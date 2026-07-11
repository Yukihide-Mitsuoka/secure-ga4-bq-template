"""Unit tests for the sensitivity-catalog model and FR-1.2 level resolution."""

import pytest

from src.modules.inspection.domain.catalog import SensitivityCatalog
from tests.modules.inspection.builders import a_catalog


def test_shipped_column_default_resolves() -> None:
    assert a_catalog().effective_level("user_id") == "high"


def test_promoted_event_param_counts_as_column_once_promoted() -> None:
    assert a_catalog().effective_level("page_location") == "high"


def test_engagement_override_wins_over_shipped_default() -> None:
    catalog = a_catalog(overrides={"user_pseudo_id": "high"})
    assert catalog.effective_level("user_pseudo_id") == "high"


def test_override_can_also_relax_a_level() -> None:
    catalog = a_catalog(overrides={"user_id": "medium"})
    assert catalog.effective_level("user_id") == "medium"


def test_uncataloged_column_resolves_to_none() -> None:
    assert a_catalog().effective_level("event_name") is None


def test_level_value_outside_declared_levels_is_rejected() -> None:
    with pytest.raises(ValueError, match="not one of the declared levels"):
        a_catalog(columns={"user_id": "critical"})


def test_bad_override_level_is_rejected_too() -> None:
    with pytest.raises(ValueError, match="overrides"):
        a_catalog(overrides={"user_id": "top-secret"})


def test_empty_levels_are_rejected() -> None:
    with pytest.raises(ValueError, match="at least one sensitivity level"):
        SensitivityCatalog(levels=())
