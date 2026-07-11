"""Unit tests for the YAML engagement-params repository (design §2.2 un-nesting)."""

from pathlib import Path

import pytest

from src.modules.inspection.domain.params import DatasetScope, InspectionParams
from src.modules.inspection.infrastructure.yaml_params_repository import YamlParamsRepository

FULL_YAML = """\
version: 1
project_id: cust-project
expected_location: asia-northeast1
datasets:
  mart_patterns: ["mart_*"]
  raw_patterns: ["analytics_*"]
  exclude: ["scratch"]
audit:
  high_sensitivity_datasets: ["marts"]
  retention_max_days: 180
thresholds:
  large_table_bytes: 1073741824
  long_lived_days: 30
  require_cmek: true
catalog_path: catalog/custom.yml
"""

MINIMAL_YAML = "project_id: p\nexpected_location: asia-northeast1\n"


def _load(tmp_path: Path, content: str) -> InspectionParams:
    path = tmp_path / "params.yml"
    path.write_text(content, encoding="utf-8")
    return YamlParamsRepository().load(str(path))


def test_full_engagement_file_maps_every_field(tmp_path: Path) -> None:
    params = _load(tmp_path, FULL_YAML)
    assert params.project_id == "cust-project"
    assert params.mart_patterns == ("mart_*",)
    assert params.exclude == ("scratch",)
    assert params.audit.high_sensitivity_datasets == ("marts",)
    assert params.audit.retention_max_days == 180
    assert params.thresholds.large_table_bytes == 1024**3
    assert params.thresholds.require_cmek is True
    assert params.catalog_path == "catalog/custom.yml"


def test_nested_dataset_scoping_still_classifies(tmp_path: Path) -> None:
    params = _load(tmp_path, FULL_YAML)
    assert params.classify("scratch") is DatasetScope.EXCLUDED
    assert params.classify("analytics_1") is DatasetScope.RAW
    assert params.classify("mart_sales") is DatasetScope.MART


def test_minimal_file_falls_back_to_template_defaults(tmp_path: Path) -> None:
    params = _load(tmp_path, MINIMAL_YAML)
    defaults = InspectionParams(project_id="_", expected_location="_")
    assert params.mart_patterns == defaults.mart_patterns
    assert params.audit.retention_max_days == defaults.audit.retention_max_days
    assert params.thresholds.large_table_bytes == defaults.thresholds.large_table_bytes
    assert params.catalog_path == defaults.catalog_path


def test_missing_project_id_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="'project_id' is required"):
        _load(tmp_path, "expected_location: asia-northeast1\n")


def test_missing_expected_location_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="'expected_location' is required"):
        _load(tmp_path, "project_id: p\n")


def test_non_mapping_yaml_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="must be a YAML mapping"):
        _load(tmp_path, "- a\n- b\n")


def test_non_list_patterns_are_rejected(tmp_path: Path) -> None:
    bad = MINIMAL_YAML + "datasets:\n  mart_patterns: not-a-list\n"
    with pytest.raises(ValueError, match="datasets.mart_patterns must be a YAML list"):
        _load(tmp_path, bad)


def test_non_mapping_section_is_rejected(tmp_path: Path) -> None:
    bad = MINIMAL_YAML + "audit: [not, a, mapping]\n"
    with pytest.raises(ValueError, match="'audit' must be a YAML mapping"):
        _load(tmp_path, bad)


def test_unsupported_version_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unsupported params version"):
        _load(tmp_path, "version: 9\n" + MINIMAL_YAML)


def test_invalid_threshold_propagates_domain_validation(tmp_path: Path) -> None:
    bad = MINIMAL_YAML + "thresholds:\n  long_lived_days: 0\n"
    with pytest.raises(ValueError, match="long_lived_days must be positive"):
        _load(tmp_path, bad)
