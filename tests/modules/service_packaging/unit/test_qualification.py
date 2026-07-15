from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import yaml

from src.modules.service_packaging.domain.menu import LabeledItem
from src.modules.service_packaging.domain.qualification import evaluate_scope
from src.modules.service_packaging.infrastructure.yaml_profile_repository import (
    YamlMenuProfileRepository,
)
from src.modules.service_packaging.infrastructure.yaml_scope_repository import (
    YamlEngagementScopeRepository,
)

PROFILE_PATH = Path("service-packages/inspection-standard.yml")
SCOPE_PATH = Path("engagement-scope.example.yml")


def _profile():
    return YamlMenuProfileRepository().load(PROFILE_PATH)


def _scope():
    return YamlEngagementScopeRepository().load(SCOPE_PATH)


def test_example_scope_at_exact_limits_is_eligible() -> None:
    result = evaluate_scope(_profile(), _scope())

    assert result.standard_package_eligible
    assert result.reasons == ()
    assert result.profile_id == "inspection-standard-v1"
    assert vars(result.scope.counts) == {
        "projects": 1,
        "datasets": 10,
        "table_resources": 200,
        "leaf_columns": 2_000,
    }


@pytest.mark.parametrize(
    ("field", "condition_id"),
    [
        ("projects", "multiple_projects"),
        ("datasets", "dataset_limit_exceeded"),
        ("table_resources", "table_resource_limit_exceeded"),
        ("leaf_columns", "leaf_column_limit_exceeded"),
    ],
)
def test_each_exceeded_capacity_returns_its_profile_reason(field, condition_id) -> None:
    scope = _scope()
    actual = getattr(scope.counts, field) + 1
    scope = replace(scope, counts=replace(scope.counts, **{field: actual}))

    result = evaluate_scope(_profile(), scope)

    assert not result.standard_package_eligible
    assert [(reason.condition_id, reason.actual) for reason in result.reasons] == [
        (condition_id, actual)
    ]


@pytest.mark.parametrize(
    "field",
    ["customer_wif_setup", "query_jobs_required", "row_value_inspection_required"],
)
def test_each_special_condition_returns_its_profile_reason(field) -> None:
    result = evaluate_scope(_profile(), replace(_scope(), **{field: True}))

    assert [(reason.condition_id, reason.actual, reason.limit) for reason in result.reasons] == [
        (field, True, None)
    ]


def test_all_triggered_conditions_return_in_profile_order() -> None:
    scope = _scope()
    counts = replace(scope.counts, projects=2, datasets=11, table_resources=201, leaf_columns=2_001)
    scope = replace(
        scope,
        counts=counts,
        customer_wif_setup=True,
        query_jobs_required=True,
        row_value_inspection_required=True,
    )

    result = evaluate_scope(_profile(), scope)

    assert tuple((reason.condition_id, reason.label) for reason in result.reasons) == tuple(
        (item.item_id, item.label) for item in _profile().separate_estimate_conditions
    )


def test_profile_limit_change_changes_evaluation_without_rule_change() -> None:
    profile = _profile()
    scope = replace(_scope(), counts=replace(_scope().counts, datasets=11))

    assert not evaluate_scope(profile, scope).standard_package_eligible
    changed = replace(profile, limits=replace(profile.limits, datasets=11))
    assert evaluate_scope(changed, scope).standard_package_eligible


def test_profile_evaluator_condition_contract_fails_closed() -> None:
    profile = _profile()

    with pytest.raises(ValueError, match="missing=.*row_value_inspection_required"):
        replace(
            profile,
            separate_estimate_conditions=profile.separate_estimate_conditions[:-1],
        )

    with pytest.raises(ValueError, match="unsupported=.*future_condition"):
        replace(
            profile,
            separate_estimate_conditions=profile.separate_estimate_conditions
            + (LabeledItem("future_condition", "Future"),),
        )


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (("version",), 2, "unsupported engagement scope version"),
        (("counts", "projects"), 0, "counts.projects must be a positive integer"),
        (("counts", "datasets"), -1, "counts.datasets must be a positive integer"),
        (("counts", "table_resources"), True, "counts.table_resources.*YAML integer"),
        (("special_conditions", "customer_wif_setup"), 1, "must be a YAML boolean"),
    ],
)
def test_invalid_scope_values_fail_closed(
    tmp_path: Path, path: tuple[str, ...], value: object, message: str
) -> None:
    raw = _scope_raw()
    _set(raw, path, value)

    with pytest.raises(ValueError, match=message):
        YamlEngagementScopeRepository().load(_write(tmp_path, raw))


def test_missing_and_unknown_scope_fields_have_path_qualified_errors(tmp_path: Path) -> None:
    raw = _scope_raw()
    del raw["counts"]["leaf_columns"]
    path = _write(tmp_path, raw)

    with pytest.raises(ValueError, match=rf"{path}.*leaf_columns"):
        YamlEngagementScopeRepository().load(path)

    raw = _scope_raw()
    raw["special_conditions"]["unknown"] = False
    with pytest.raises(ValueError, match="unsupported=.*unknown"):
        YamlEngagementScopeRepository().load(_write(tmp_path, raw))


def _scope_raw() -> dict[str, Any]:
    value = yaml.safe_load(SCOPE_PATH.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _write(tmp_path: Path, raw: dict[str, Any]) -> Path:
    path = tmp_path / "scope.yml"
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    return path


def _set(raw: dict[str, Any], path: tuple[str, ...], value: object) -> None:
    target = raw
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
