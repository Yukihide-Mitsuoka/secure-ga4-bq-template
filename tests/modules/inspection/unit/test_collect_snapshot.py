"""Unit tests for the CollectSnapshot use case (scoping + honest coverage)."""

from src.modules.inspection.application.collect_snapshot import CollectSnapshot
from tests.modules.inspection.builders import FIXED_NOW, a_dataset, a_table, params
from tests.modules.inspection.fakes import (
    FakeBigQueryPort,
    FakeIamPort,
    FakeLoggingPort,
    FakeTaxonomyPort,
    FixedClock,
)


def _collector(bigquery: FakeBigQueryPort) -> CollectSnapshot:
    return CollectSnapshot(
        bigquery=bigquery,
        iam=FakeIamPort(),
        taxonomies=FakeTaxonomyPort(),
        logging_config=FakeLoggingPort(),
        clock=FixedClock(),
    )


def test_mart_dataset_gets_the_full_table_walk() -> None:
    bigquery = FakeBigQueryPort(
        datasets={"marts": a_dataset("marts")},
        tables={"marts": {"fct_events": a_table("fct_events")}},
    )
    snapshot = _collector(bigquery).collect(params())
    assert [d.dataset_id for d in snapshot.datasets] == ["marts"]
    assert [t.table_id for t in snapshot.datasets[0].tables] == ["fct_events"]
    assert snapshot.skipped == ()


def test_excluded_dataset_is_skipped_with_a_reason() -> None:
    bigquery = FakeBigQueryPort(datasets={"scratch": a_dataset("scratch")})
    snapshot = _collector(bigquery).collect(params(exclude=("scratch",)))
    assert snapshot.datasets == ()
    assert [(s.resource, s.reason) for s in snapshot.skipped] == [
        ("projects/verify-project/datasets/scratch", "excluded by engagement params")
    ]


def test_raw_export_is_containment_only_no_table_walk() -> None:
    bigquery = FakeBigQueryPort(
        datasets={"analytics_123": a_dataset("analytics_123")},
        tables={"analytics_123": {"events_x": a_table("events_x")}},
    )
    snapshot = _collector(bigquery).collect(params())
    dataset = snapshot.datasets[0]
    assert dataset.dataset_id == "analytics_123"
    assert dataset.tables == ()  # IAM still inspectable; columns out of denominator
    assert "containment-only" in snapshot.skipped[0].reason


def test_unmatched_dataset_is_walked_like_a_mart() -> None:
    bigquery = FakeBigQueryPort(
        datasets={"random": a_dataset("random")},
        tables={"random": {"t": a_table("t")}},
    )
    snapshot = _collector(bigquery).collect(params())
    assert [t.table_id for t in snapshot.datasets[0].tables] == ["t"]


def test_failing_table_is_recorded_as_skipped_not_fatal() -> None:
    bigquery = FakeBigQueryPort(
        datasets={"marts": a_dataset("marts")},
        tables={"marts": {"good": a_table("good"), "bad": a_table("bad")}},
        failing_tables=frozenset({"bad"}),
    )
    snapshot = _collector(bigquery).collect(params())
    assert [t.table_id for t in snapshot.datasets[0].tables] == ["good"]
    skip = snapshot.skipped[0]
    assert skip.resource == "projects/verify-project/datasets/marts/tables/bad"
    assert "collection failed" in skip.reason and "boom" in skip.reason


def test_clock_and_taxonomy_location_are_wired() -> None:
    taxonomy_port = FakeTaxonomyPort()
    collector = CollectSnapshot(
        bigquery=FakeBigQueryPort(datasets={}),
        iam=FakeIamPort(),
        taxonomies=taxonomy_port,
        logging_config=FakeLoggingPort(),
        clock=FixedClock(),
    )
    snapshot = collector.collect(params(expected_location="us-central1"))
    assert snapshot.captured_at == FIXED_NOW
    assert taxonomy_port.requested_location == "us-central1"
