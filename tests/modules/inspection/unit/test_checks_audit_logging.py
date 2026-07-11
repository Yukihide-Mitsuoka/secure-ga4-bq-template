"""Unit tests for audit-logging checkpoints CHK-06..07."""

from src.modules.inspection.domain.checks.audit_logging import (
    check_chk06_data_access_overenabled,
    check_chk07_audit_pipeline,
)
from src.modules.inspection.domain.finding import Severity
from src.modules.inspection.domain.params import AuditParams
from src.modules.inspection.domain.snapshot import (
    AuditConfig,
    AuditLogConfig,
    LogExclusion,
    LoggingConfig,
    LogSink,
    ProjectIam,
)
from tests.modules.inspection.builders import a_catalog, a_dataset, a_snapshot, params

AUDIT_FILTER = 'log_id("cloudaudit.googleapis.com/activity")'
DATA_ACCESS_FILTER = 'log_id("cloudaudit.googleapis.com/data_access")'


def _iam_with_audit(service: str, log_type: str = "DATA_READ") -> ProjectIam:
    return ProjectIam(audit_configs=(AuditConfig(service, (AuditLogConfig(log_type),)),))


def test_chk06_all_services_data_read_is_flagged() -> None:
    snapshot = a_snapshot(iam=_iam_with_audit("allServices"))
    findings = check_chk06_data_access_overenabled(snapshot, params(), a_catalog())
    assert [f.severity for f in findings] == [Severity.MEDIUM]
    assert "allServices" in findings[0].observed


def test_chk06_bigquery_data_access_without_declared_scope_is_flagged() -> None:
    snapshot = a_snapshot(iam=_iam_with_audit("bigquery.googleapis.com"))
    findings = check_chk06_data_access_overenabled(snapshot, params(), a_catalog())
    assert len(findings) == 1


def test_chk06_bigquery_data_access_with_declared_scope_passes() -> None:
    snapshot = a_snapshot(iam=_iam_with_audit("bigquery.googleapis.com"))
    scoped = params(audit=AuditParams(high_sensitivity_datasets=("marts",)))
    assert check_chk06_data_access_overenabled(snapshot, scoped, a_catalog()) == []


def test_chk06_admin_read_only_is_not_data_access() -> None:
    snapshot = a_snapshot(iam=_iam_with_audit("allServices", log_type="ADMIN_READ"))
    assert check_chk06_data_access_overenabled(snapshot, params(), a_catalog()) == []


def test_chk06_unrestricted_data_access_sink_is_flagged() -> None:
    sink = LogSink("audit", "storage.googleapis.com/b", filter=DATA_ACCESS_FILTER)
    snapshot = a_snapshot(logging=LoggingConfig(sinks=(sink,)))
    findings = check_chk06_data_access_overenabled(snapshot, params(), a_catalog())
    assert [f.resource for f in findings] == ["projects/verify-project/sinks/audit"]


def test_chk06_sink_restricted_to_declared_datasets_passes() -> None:
    sink = LogSink("audit", "storage.googleapis.com/b", filter=DATA_ACCESS_FILTER + ' "marts"')
    snapshot = a_snapshot(logging=LoggingConfig(sinks=(sink,)))
    scoped = params(audit=AuditParams(high_sensitivity_datasets=("marts",)))
    assert check_chk06_data_access_overenabled(snapshot, scoped, a_catalog()) == []


def test_chk07_missing_audit_sink_and_exclusions_are_both_flagged() -> None:
    findings = check_chk07_audit_pipeline(a_snapshot(), params(), a_catalog())
    severities = sorted(f.severity.value for f in findings)
    assert severities == ["LOW", "MEDIUM"]  # no exclusions + no sink


def test_chk07_bq_destination_without_expiration_is_flagged() -> None:
    sink = LogSink(
        "audit",
        "bigquery.googleapis.com/projects/verify-project/datasets/audit_logs",
        filter=AUDIT_FILTER,
    )
    dataset = a_dataset("audit_logs", default_table_expiration_ms=None)
    snapshot = a_snapshot(
        datasets=(dataset,),
        logging=LoggingConfig(sinks=(sink,), exclusions=(LogExclusion("noise"),)),
    )
    findings = check_chk07_audit_pipeline(snapshot, params(), a_catalog())
    assert [f.severity for f in findings] == [Severity.MEDIUM]
    assert "no default table expiration" in findings[0].observed


def test_chk07_bq_destination_within_retention_ceiling_passes() -> None:
    thirty_days_ms = 30 * 24 * 60 * 60 * 1000
    sink = LogSink(
        "audit",
        "bigquery.googleapis.com/projects/verify-project/datasets/audit_logs",
        filter=AUDIT_FILTER,
    )
    dataset = a_dataset("audit_logs", default_table_expiration_ms=thirty_days_ms)
    snapshot = a_snapshot(
        datasets=(dataset,),
        logging=LoggingConfig(sinks=(sink,), exclusions=(LogExclusion("noise"),)),
    )
    assert check_chk07_audit_pipeline(snapshot, params(), a_catalog()) == []


def test_chk07_destination_outside_snapshot_is_info_not_silent() -> None:
    sink = LogSink(
        "audit", "bigquery.googleapis.com/projects/other/datasets/elsewhere", filter=AUDIT_FILTER
    )
    snapshot = a_snapshot(logging=LoggingConfig(sinks=(sink,), exclusions=(LogExclusion("noise"),)))
    findings = check_chk07_audit_pipeline(snapshot, params(), a_catalog())
    assert [f.severity for f in findings] == [Severity.INFO]


def test_chk07_gcs_destination_retention_is_reported_unverifiable() -> None:
    sink = LogSink("audit", "storage.googleapis.com/audit-bucket", filter=AUDIT_FILTER)
    snapshot = a_snapshot(logging=LoggingConfig(sinks=(sink,), exclusions=(LogExclusion("noise"),)))
    findings = check_chk07_audit_pipeline(snapshot, params(), a_catalog())
    assert [f.severity for f in findings] == [Severity.INFO]
    assert "inspector role" in findings[0].observed
