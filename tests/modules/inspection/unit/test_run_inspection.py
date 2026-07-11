"""Unit tests for the RunInspection use case (the module's public entry point)."""

from src.modules.inspection.application.collect_snapshot import CollectSnapshot
from src.modules.inspection.application.run_inspection import RunInspection
from src.modules.inspection.domain.checks import ALL_CHECKS
from src.modules.inspection.domain.snapshot import SchemaField
from tests.modules.inspection.builders import FIXED_NOW, a_catalog, a_dataset, a_table, params
from tests.modules.inspection.fakes import (
    FakeBigQueryPort,
    FakeCatalogRepository,
    FakeIamPort,
    FakeLoggingPort,
    FakeTaxonomyPort,
    FixedClock,
)


def _runner(bigquery: FakeBigQueryPort, checks: tuple = ALL_CHECKS) -> RunInspection:  # type: ignore[type-arg]
    collector = CollectSnapshot(
        bigquery=bigquery,
        iam=FakeIamPort(),
        taxonomies=FakeTaxonomyPort(),
        logging_config=FakeLoggingPort(),
        clock=FixedClock(),
    )
    return RunInspection(collector, FakeCatalogRepository(a_catalog()), checks=checks)


def _dirty_bigquery() -> FakeBigQueryPort:
    # One mart table with an untagged cataloged-high column -> CHK-04 must fire.
    table = a_table("fct_events", schema_fields=(SchemaField("user_id", "STRING"),))
    return FakeBigQueryPort(
        datasets={"marts": a_dataset("marts")}, tables={"marts": {"fct_events": table}}
    )


def test_report_carries_findings_coverage_and_params_echo() -> None:
    scoped = params()
    report = _runner(_dirty_bigquery()).handle(scoped)
    assert report.project_id == "verify-project"
    assert report.captured_at == FIXED_NOW
    assert report.params is scoped
    assert report.coverage.datasets == 1
    assert report.coverage.tables == 1
    assert report.coverage.columns == 1
    assert "CHK-04" in {f.check_id for f in report.findings}


def test_findings_leave_sorted_regardless_of_check_order() -> None:
    forward = _runner(_dirty_bigquery()).handle(params())
    reversed_run = _runner(_dirty_bigquery(), checks=tuple(reversed(ALL_CHECKS))).handle(params())
    assert forward.findings == reversed_run.findings


def test_clean_empty_project_reports_zero_coverage_and_only_pipeline_advice() -> None:
    report = _runner(FakeBigQueryPort(datasets={})).handle(params())
    assert (report.coverage.datasets, report.coverage.tables, report.coverage.columns) == (0, 0, 0)
    assert {f.check_id for f in report.findings} <= {"CHK-07"}
