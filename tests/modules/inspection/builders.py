"""Builders for inspection-domain test data (TST-010: independent fixtures).

Each builder returns a fully valid object with innocuous defaults; tests override
only the fields they assert on, so every test stays readable on its own. Extend
with new keyword arguments as later check PRs need them — never with **kwargs
(keeps mypy/ruff honest about what tests actually set).
"""

from __future__ import annotations

from datetime import UTC, datetime

from src.modules.inspection.domain.catalog import SensitivityCatalog
from src.modules.inspection.domain.params import AuditParams, InspectionParams, Thresholds
from src.modules.inspection.domain.snapshot import (
    AccessEntry,
    DatasetMeta,
    LoggingConfig,
    ProjectIam,
    ProjectSnapshot,
    SchemaField,
    SkippedResource,
    TableMeta,
    Taxonomy,
)

FIXED_NOW = datetime(2026, 7, 11, 12, 0, 0, tzinfo=UTC)


def a_table(
    table_id: str = "fct_events",
    *,
    table_type: str = "TABLE",
    num_bytes: int = 1024,
    creation_time: datetime = FIXED_NOW,
    expiration_time: datetime | None = None,
    time_partitioning_field: str | None = "event_date",
    range_partitioning_field: str | None = None,
    require_partition_filter: bool = True,
    clustering_fields: tuple[str, ...] = ("event_name",),
    schema_fields: tuple[SchemaField, ...] = (),
) -> TableMeta:
    return TableMeta(
        table_id=table_id,
        table_type=table_type,
        num_bytes=num_bytes,
        creation_time=creation_time,
        expiration_time=expiration_time,
        time_partitioning_field=time_partitioning_field,
        range_partitioning_field=range_partitioning_field,
        require_partition_filter=require_partition_filter,
        clustering_fields=clustering_fields,
        schema_fields=schema_fields,
    )


def a_dataset(
    dataset_id: str = "marts",
    *,
    location: str = "asia-northeast1",
    default_table_expiration_ms: int | None = None,
    cmek_key: str | None = None,
    access: tuple[AccessEntry, ...] = (),
    tables: tuple[TableMeta, ...] = (),
) -> DatasetMeta:
    return DatasetMeta(
        dataset_id=dataset_id,
        location=location,
        default_table_expiration_ms=default_table_expiration_ms,
        cmek_key=cmek_key,
        access=access,
        tables=tables,
    )


def a_snapshot(
    *,
    project_id: str = "verify-project",
    iam: ProjectIam | None = None,
    datasets: tuple[DatasetMeta, ...] = (),
    taxonomies: tuple[Taxonomy, ...] = (),
    logging: LoggingConfig | None = None,
    skipped: tuple[SkippedResource, ...] = (),
) -> ProjectSnapshot:
    return ProjectSnapshot(
        project_id=project_id,
        captured_at=FIXED_NOW,
        iam=iam if iam is not None else ProjectIam(),
        datasets=datasets,
        taxonomies=taxonomies,
        logging=logging if logging is not None else LoggingConfig(),
        skipped=skipped,
    )


def a_catalog(
    *,
    levels: tuple[str, ...] = ("high", "medium", "low"),
    columns: dict[str, str] | None = None,
    promoted_event_params: dict[str, str] | None = None,
    overrides: dict[str, str] | None = None,
) -> SensitivityCatalog:
    return SensitivityCatalog(
        levels=levels,
        columns={"user_id": "high", "user_pseudo_id": "medium"} if columns is None else columns,
        promoted_event_params=(
            {"page_location": "high"} if promoted_event_params is None else promoted_event_params
        ),
        overrides={} if overrides is None else overrides,
    )


def params(
    *,
    project_id: str = "verify-project",
    expected_location: str = "asia-northeast1",
    mart_patterns: tuple[str, ...] | None = None,
    raw_patterns: tuple[str, ...] | None = None,
    exclude: tuple[str, ...] = (),
    audit: AuditParams | None = None,
    thresholds: Thresholds | None = None,
) -> InspectionParams:
    defaults = InspectionParams(project_id="d", expected_location="d")
    return InspectionParams(
        project_id=project_id,
        expected_location=expected_location,
        mart_patterns=defaults.mart_patterns if mart_patterns is None else mart_patterns,
        raw_patterns=defaults.raw_patterns if raw_patterns is None else raw_patterns,
        exclude=exclude,
        audit=audit if audit is not None else AuditParams(),
        thresholds=thresholds if thresholds is not None else Thresholds(),
    )
