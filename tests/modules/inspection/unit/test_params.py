"""Unit tests for engagement parameters (FR-7) and the §4.2 dataset scoping."""

import pytest

from src.modules.inspection.domain.params import AuditParams, DatasetScope, Thresholds
from tests.modules.inspection.builders import params


def test_mart_pattern_classifies_as_mart() -> None:
    assert params().classify("marts") is DatasetScope.MART
    assert params().classify("staging") is DatasetScope.MART


def test_raw_ga4_export_classifies_as_raw() -> None:
    assert params().classify("analytics_123456789") is DatasetScope.RAW


def test_exclude_wins_over_raw_and_mart_patterns() -> None:
    scoped = params(exclude=("analytics_*", "marts"))
    assert scoped.classify("analytics_123") is DatasetScope.EXCLUDED
    assert scoped.classify("marts") is DatasetScope.EXCLUDED


def test_raw_wins_over_mart_when_both_match() -> None:
    scoped = params(mart_patterns=("analytics_*",))
    assert scoped.classify("analytics_1") is DatasetScope.RAW


def test_unmatched_dataset_is_flagged_not_dropped() -> None:
    assert params().classify("random_dataset") is DatasetScope.UNMATCHED


def test_empty_project_id_is_rejected() -> None:
    with pytest.raises(ValueError):
        params(project_id="")


def test_empty_expected_location_is_rejected() -> None:
    with pytest.raises(ValueError):
        params(expected_location="")


def test_non_positive_thresholds_are_rejected() -> None:
    with pytest.raises(ValueError):
        Thresholds(large_table_bytes=0)
    with pytest.raises(ValueError):
        Thresholds(long_lived_days=-1)
    with pytest.raises(ValueError):
        AuditParams(retention_max_days=0)


def test_threshold_defaults_match_design_2_2() -> None:
    thresholds = Thresholds()
    assert thresholds.large_table_bytes == 10 * 1024**3
    assert thresholds.long_lived_days == 90
    assert thresholds.require_cmek is False
