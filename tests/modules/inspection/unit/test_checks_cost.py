"""Unit tests for cost checkpoints CHK-08..10."""

from datetime import timedelta

from src.modules.inspection.domain.checks.cost import (
    check_chk08_large_tables_unpartitioned,
    check_chk09_partition_filter_not_required,
    check_chk10_long_lived_without_expiration,
)
from src.modules.inspection.domain.finding import Severity
from tests.modules.inspection.builders import (
    FIXED_NOW,
    a_catalog,
    a_dataset,
    a_snapshot,
    a_table,
    params,
)

BIG = 11 * 1024**3  # over the 10 GiB default threshold


def test_chk08_large_unpartitioned_table_is_medium_plus_clustering_info() -> None:
    table = a_table(num_bytes=BIG, time_partitioning_field=None, clustering_fields=())
    snapshot = a_snapshot(datasets=(a_dataset(tables=(table,)),))
    findings = check_chk08_large_tables_unpartitioned(snapshot, params(), a_catalog())
    assert sorted(f.severity.value for f in findings) == ["INFO", "MEDIUM"]


def test_chk08_small_unpartitioned_table_passes() -> None:
    table = a_table(num_bytes=1024, time_partitioning_field=None, clustering_fields=())
    snapshot = a_snapshot(datasets=(a_dataset(tables=(table,)),))
    assert check_chk08_large_tables_unpartitioned(snapshot, params(), a_catalog()) == []


def test_chk08_large_partitioned_clustered_table_passes() -> None:
    table = a_table(num_bytes=BIG)  # builder default: partitioned + clustered
    snapshot = a_snapshot(datasets=(a_dataset(tables=(table,)),))
    assert check_chk08_large_tables_unpartitioned(snapshot, params(), a_catalog()) == []


def test_chk09_partitioned_without_filter_requirement_is_low() -> None:
    table = a_table(require_partition_filter=False)
    snapshot = a_snapshot(datasets=(a_dataset(tables=(table,)),))
    findings = check_chk09_partition_filter_not_required(snapshot, params(), a_catalog())
    assert [f.severity for f in findings] == [Severity.LOW]


def test_chk09_unpartitioned_table_is_chk08s_business_not_chk09s() -> None:
    table = a_table(time_partitioning_field=None, require_partition_filter=False)
    snapshot = a_snapshot(datasets=(a_dataset(tables=(table,)),))
    assert check_chk09_partition_filter_not_required(snapshot, params(), a_catalog()) == []


def test_chk10_old_table_with_no_expiration_anywhere_is_low() -> None:
    table = a_table(creation_time=FIXED_NOW - timedelta(days=120))
    snapshot = a_snapshot(datasets=(a_dataset(tables=(table,)),))
    findings = check_chk10_long_lived_without_expiration(snapshot, params(), a_catalog())
    assert [f.severity for f in findings] == [Severity.LOW]
    assert "120 days old" in findings[0].observed


def test_chk10_table_level_expiration_satisfies_the_check() -> None:
    table = a_table(
        creation_time=FIXED_NOW - timedelta(days=120),
        expiration_time=FIXED_NOW + timedelta(days=30),
    )
    snapshot = a_snapshot(datasets=(a_dataset(tables=(table,)),))
    assert check_chk10_long_lived_without_expiration(snapshot, params(), a_catalog()) == []


def test_chk10_dataset_default_expiration_satisfies_the_check() -> None:
    table = a_table(creation_time=FIXED_NOW - timedelta(days=120))
    dataset = a_dataset(default_table_expiration_ms=1000, tables=(table,))
    snapshot = a_snapshot(datasets=(dataset,))
    assert check_chk10_long_lived_without_expiration(snapshot, params(), a_catalog()) == []


def test_chk10_young_table_is_not_flagged() -> None:
    table = a_table(creation_time=FIXED_NOW - timedelta(days=5))
    snapshot = a_snapshot(datasets=(a_dataset(tables=(table,)),))
    assert check_chk10_long_lived_without_expiration(snapshot, params(), a_catalog()) == []
