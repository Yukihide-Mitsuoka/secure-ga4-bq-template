from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest
import yaml

from src.modules.service_packaging.application.qualify_engagement import QualifyEngagement
from src.modules.service_packaging.domain.menu import LabeledItem
from src.modules.service_packaging.domain.qualification import evaluate_scope
from src.modules.service_packaging.infrastructure.qualification_artifact_writer import (
    QualificationArtifactWriter,
)
from src.modules.service_packaging.infrastructure.yaml_profile_repository import (
    YamlMenuProfileRepository,
)
from src.modules.service_packaging.infrastructure.yaml_scope_repository import (
    YamlEngagementScopeRepository,
)
from src.modules.service_packaging.interface.qualify_cli import main

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


def test_qualification_use_case_loads_evaluates_and_writes(tmp_path: Path) -> None:
    profile_reader = Mock()
    profile_reader.load.return_value = _profile()
    scope_reader = Mock()
    scope_reader.load.return_value = _scope()
    writer = Mock()
    writer.write.return_value = (tmp_path / "qualification.json", tmp_path / "qualification.md")
    paths = QualifyEngagement(
        profile_reader=profile_reader, scope_reader=scope_reader, writer=writer
    ).handle(PROFILE_PATH, SCOPE_PATH, tmp_path)

    assert paths == (tmp_path / "qualification.json", tmp_path / "qualification.md")
    profile_reader.load.assert_called_once_with(PROFILE_PATH)
    scope_reader.load.assert_called_once_with(SCOPE_PATH)
    assert writer.write.call_args.args[0].standard_package_eligible
    assert writer.write.call_args.args[1] == tmp_path


def test_writer_outputs_deterministic_matching_json_and_markdown(tmp_path: Path) -> None:
    scope = replace(
        _scope(),
        counts=replace(_scope().counts, projects=2, datasets=11),
        query_jobs_required=True,
    )
    result = evaluate_scope(_profile(), scope)
    injected = "複数\n## [link](target)"
    result = replace(
        result, reasons=(replace(result.reasons[0], label=injected), *result.reasons[1:])
    )

    first = QualificationArtifactWriter().write(result, tmp_path / "first")
    second = QualificationArtifactWriter().write(result, tmp_path / "second")
    payload = json.loads(first[0].read_text(encoding="utf-8"))
    markdown = first[1].read_text(encoding="utf-8")

    assert tuple(path.read_bytes() for path in first) == tuple(path.read_bytes() for path in second)
    assert payload["standard_package_eligible"] is False
    assert payload["scope"]["counts"]["datasets"] == 11
    assert [reason["condition_id"] for reason in payload["reasons"]] == [
        "multiple_projects",
        "dataset_limit_exceeded",
        "query_jobs_required",
    ]
    assert payload["reasons"][0]["label"] == injected
    assert "\n## [link]" not in markdown
    assert all(reason["label"] in markdown for reason in payload["reasons"][1:])
    assert "**別途見積もり**" in markdown


@pytest.mark.parametrize("filename", ["qualification.json", "qualification.md"])
def test_writer_refuses_to_overwrite_either_artifact(tmp_path: Path, filename: str) -> None:
    target = tmp_path / filename
    target.write_text("keep", encoding="utf-8")

    with pytest.raises(FileExistsError, match=filename):
        QualificationArtifactWriter().write(evaluate_scope(_profile(), _scope()), tmp_path)

    assert target.read_text(encoding="utf-8") == "keep"
    assert len(list(tmp_path.iterdir())) == 1


def test_writer_rolls_back_pair_when_second_publish_fails(monkeypatch, tmp_path: Path) -> None:
    real_link = os.link

    def fail_markdown(source, target) -> None:
        if Path(target).name == "qualification.md":
            raise OSError("publish failed")
        real_link(source, target)

    monkeypatch.setattr(os, "link", fail_markdown)

    with pytest.raises(OSError, match="publish failed"):
        QualificationArtifactWriter().write(evaluate_scope(_profile(), _scope()), tmp_path)

    assert list(tmp_path.iterdir()) == []


def test_qualification_cli_needs_no_cloud_configuration(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)

    assert main(_cli_args(tmp_path, SCOPE_PATH)) == 0
    payload = json.loads((tmp_path / "qualification.json").read_text(encoding="utf-8"))
    markdown = (tmp_path / "qualification.md").read_text(encoding="utf-8")
    assert payload["standard_package_eligible"] is True
    assert payload["reasons"] == []
    assert "**標準パッケージ適合**" in markdown and "- なし" in markdown


def test_qualification_cli_rejects_missing_scope(tmp_path: Path) -> None:
    assert main(_cli_args(tmp_path, tmp_path / "missing.yml")) == 2


def _cli_args(out_dir: Path, scope_path: Path) -> list[str]:
    return [
        "--profile",
        str(PROFILE_PATH),
        "--scope",
        str(scope_path),
        "--out-dir",
        str(out_dir),
    ]


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
