"""Unit tests for the ProjectSnapshot domain model (pure, no I/O)."""

import pytest

from src.modules.inspection.domain.snapshot import ProjectSnapshot
from tests.modules.inspection.builders import FIXED_NOW, a_dataset, a_snapshot, a_table


def test_empty_project_id_is_rejected() -> None:
    with pytest.raises(ValueError):
        ProjectSnapshot(project_id="", captured_at=FIXED_NOW)


def test_snapshot_is_immutable() -> None:
    snapshot = a_snapshot()
    with pytest.raises(AttributeError):
        snapshot.project_id = "other"  # type: ignore[misc]


def test_time_partitioned_table_reports_is_partitioned() -> None:
    assert a_table(time_partitioning_field="event_date").is_partitioned


def test_range_partitioned_table_reports_is_partitioned() -> None:
    table = a_table(time_partitioning_field=None, range_partitioning_field="customer_id")
    assert table.is_partitioned


def test_unpartitioned_table_reports_not_partitioned() -> None:
    assert not a_table(time_partitioning_field=None).is_partitioned


def test_resource_paths_are_canonical() -> None:
    table = a_table("fct_events")
    dataset = a_dataset("marts", tables=(table,))
    snapshot = a_snapshot(project_id="p1", datasets=(dataset,))
    assert snapshot.dataset_path(dataset) == "projects/p1/datasets/marts"
    assert snapshot.table_path(dataset, table) == "projects/p1/datasets/marts/tables/fct_events"
