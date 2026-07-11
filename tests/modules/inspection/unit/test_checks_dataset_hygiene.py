"""Unit tests for the dataset-hygiene checkpoint CHK-11."""

from src.modules.inspection.domain.checks.dataset_hygiene import check_chk11_dataset_hygiene
from src.modules.inspection.domain.finding import Severity
from src.modules.inspection.domain.params import Thresholds
from tests.modules.inspection.builders import a_catalog, a_dataset, a_snapshot, params


def _findings_for(dataset, scoped=None):  # type: ignore[no-untyped-def]
    return check_chk11_dataset_hygiene(
        a_snapshot(datasets=(dataset,)), scoped or params(), a_catalog()
    )


def test_chk11_location_deviation_is_medium() -> None:
    findings = _findings_for(a_dataset(location="us-central1", default_table_expiration_ms=1))
    location_findings = [f for f in findings if "location" in f.observed]
    assert [f.severity for f in location_findings] == [Severity.MEDIUM]


def test_chk11_missing_default_expiration_is_low() -> None:
    findings = _findings_for(a_dataset(default_table_expiration_ms=None))
    expiry_findings = [f for f in findings if "expiration" in f.observed]
    assert [f.severity for f in expiry_findings] == [Severity.LOW]


def test_chk11_cmek_absence_is_info_by_default() -> None:
    findings = _findings_for(a_dataset(default_table_expiration_ms=1, cmek_key=None))
    cmek_findings = [f for f in findings if "CMEK" in f.observed]
    assert [f.severity for f in cmek_findings] == [Severity.INFO]


def test_chk11_cmek_absence_is_high_when_engagement_requires_it() -> None:
    scoped = params(thresholds=Thresholds(require_cmek=True))
    findings = _findings_for(a_dataset(default_table_expiration_ms=1), scoped)
    cmek_findings = [f for f in findings if "CMEK" in f.observed]
    assert [f.severity for f in cmek_findings] == [Severity.HIGH]


def test_chk11_cmek_present_is_not_a_finding() -> None:
    dataset = a_dataset(
        default_table_expiration_ms=1, cmek_key="projects/p/locations/l/keyRings/k/cryptoKeys/c"
    )
    assert [f for f in _findings_for(dataset) if "CMEK" in f.observed] == []


def test_chk11_compliant_dataset_yields_nothing() -> None:
    dataset = a_dataset(
        default_table_expiration_ms=1,
        cmek_key="projects/p/locations/l/keyRings/k/cryptoKeys/c",
    )
    assert _findings_for(dataset) == []


def test_chk11_raw_export_dataset_is_out_of_scope() -> None:
    dataset = a_dataset("analytics_123", location="us-central1")
    assert _findings_for(dataset) == []
