"""Unit tests for the Report/Coverage domain model."""

from src.modules.inspection.domain.finding import Finding, Severity
from src.modules.inspection.domain.report import Coverage, Report
from src.modules.inspection.domain.snapshot import SchemaField, SkippedResource
from tests.modules.inspection.builders import FIXED_NOW, a_dataset, a_snapshot, a_table, params


def _finding(check_id: str, severity: Severity) -> Finding:
    return Finding(
        check_id=check_id,
        severity=severity,
        resource="projects/p",
        observed="o",
        expected="e",
        rule_ref="FR-4 #1",
        remediation_hint="h",
    )


def test_coverage_counts_datasets_tables_and_columns() -> None:
    table = a_table(schema_fields=(SchemaField("a", "STRING"), SchemaField("b", "STRING")))
    snapshot = a_snapshot(
        datasets=(a_dataset("marts", tables=(table,)), a_dataset("staging")),
        skipped=(SkippedResource("projects/p/datasets/x", "excluded"),),
    )
    coverage = Coverage.from_snapshot(snapshot)
    assert (coverage.datasets, coverage.tables, coverage.columns) == (2, 1, 2)
    assert coverage.skipped[0].reason == "excluded"


def test_severity_counts_aggregate_by_value() -> None:
    report = Report(
        project_id="p",
        captured_at=FIXED_NOW,
        params=params(),
        coverage=Coverage(0, 0, 0),
        findings=(
            _finding("CHK-01", Severity.HIGH),
            _finding("CHK-02", Severity.HIGH),
            _finding("CHK-09", Severity.LOW),
        ),
    )
    assert report.severity_counts() == {"HIGH": 2, "LOW": 1}
