from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any

import pytest
import yaml

from src.modules.inspection.domain.checks import ALL_CHECKS
from src.modules.service_packaging.infrastructure.yaml_profile_repository import (
    YamlMenuProfileRepository,
)

DEFAULT_PROFILE = Path("service-packages/inspection-standard.yml")


def test_default_profile_matches_the_owner_approved_contract() -> None:
    profile = YamlMenuProfileRepository().load(DEFAULT_PROFILE)

    assert (profile.fee.currency, profile.fee.minimum, profile.fee.maximum) == (
        "JPY",
        300_000,
        500_000,
    )
    assert vars(profile.limits) == {
        "projects": 1,
        "datasets": 10,
        "table_resources": 200,
        "leaf_columns": 2_000,
    }
    assert profile.checks == tuple(f"CHK-{number:02d}" for number in range(1, 13))
    assert len(profile.checks) == len(ALL_CHECKS)
    assert tuple(item.item_id for item in profile.deliverables) == (
        "deterministic_report",
        "advisory_ai_report",
        "non_applying_remediation_draft",
    )
    assert profile.review_sessions == 1
    conditions = profile.separate_estimate_conditions
    assert len(conditions) == 7
    assert conditions[0].item_id == "multiple_projects"
    assert conditions[-1].item_id == "row_value_inspection_required"


def test_valid_value_changes_need_only_a_profile_edit(tmp_path: Path) -> None:
    raw = _default_raw()
    raw["fee"]["maximum"] = 600_000
    raw["limits"]["datasets"] = 12
    raw["checks"] = ["CHK-01", "CHK-12"]
    raw["deliverables"][0]["label"] = "Custom report"
    raw["review_sessions"] = 2
    raw["separate_estimate_conditions"][0]["label"] = "Custom condition"
    path = _write(tmp_path, raw)

    profile = YamlMenuProfileRepository().load(path)

    assert profile.fee.maximum == 600_000
    assert profile.limits.datasets == 12
    assert profile.checks == ("CHK-01", "CHK-12")
    assert profile.deliverables[0].label == "Custom report"
    assert profile.review_sessions == 2
    assert profile.separate_estimate_conditions[0].label == "Custom condition"


def test_loaded_profile_is_immutable() -> None:
    profile = YamlMenuProfileRepository().load(DEFAULT_PROFILE)

    with pytest.raises(FrozenInstanceError):
        profile.display_name = "changed"


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (("version",), 2, "unsupported profile version"),
        (("fee", "minimum"), 0, "fee minimum and maximum must be positive"),
        (("fee", "maximum"), 200_000, "fee.minimum must not exceed"),
        (("limits", "projects"), 0, "limits.projects must be positive"),
        (("limits", "datasets"), True, "limits.datasets.*YAML integer"),
        (("checks",), ["CHK-01", "CHK-01"], "checks must not contain duplicates"),
        (("checks",), ["CUSTOM-01"], "checks must contain CHK-NN"),
        (("deliverables",), "invalid", "'deliverables' must be a YAML list"),
        (("deliverables",), [], "deliverables must be non-empty"),
        (("review_sessions",), 0, "review_sessions must be positive"),
        (
            ("separate_estimate_conditions",),
            [{"id": "same", "label": "A"}, {"id": "same", "label": "B"}],
            "separate_estimate_conditions ids must not contain duplicates",
        ),
    ],
)
def test_invalid_profile_values_fail_closed(
    tmp_path: Path, path: tuple[str, ...], value: object, message: str
) -> None:
    raw = _default_raw()
    _set(raw, path, value)

    with pytest.raises(ValueError, match=message):
        YamlMenuProfileRepository().load(_write(tmp_path, raw))


def test_missing_required_field_has_a_path_qualified_error(tmp_path: Path) -> None:
    raw = _default_raw()
    del raw["profile_id"]
    path = _write(tmp_path, raw)

    with pytest.raises(ValueError, match=rf"{path}.*profile_id"):
        YamlMenuProfileRepository().load(path)


def _default_raw() -> dict[str, Any]:
    value = yaml.safe_load(DEFAULT_PROFILE.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _write(tmp_path: Path, raw: dict[str, Any]) -> Path:
    path = tmp_path / "profile.yml"
    path.write_text(yaml.safe_dump(raw, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def _set(raw: dict[str, Any], path: tuple[str, ...], value: object) -> None:
    target = raw
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
