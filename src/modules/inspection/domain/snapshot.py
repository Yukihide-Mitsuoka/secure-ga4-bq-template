"""ProjectSnapshot: everything the 11 checkpoints read, collected once, immutable.

Checks are pure functions over this model (MODULE.md invariant #4), so the shape
here is already normalized: adapters translate raw API responses (e.g. BigQuery
dataset `access` entries, nested schema fields) into these flat, typed records.
Values reflect REST metadata only — never query results (ADR-0003).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

# --- Project IAM (cloudresourcemanager.projects.getIamPolicy, policy v3) ---


@dataclass(frozen=True)
class IamBinding:
    role: str
    members: tuple[str, ...] = ()


@dataclass(frozen=True)
class AuditLogConfig:
    log_type: str  # "DATA_READ" | "DATA_WRITE" | "ADMIN_READ"
    exempted_members: tuple[str, ...] = ()


@dataclass(frozen=True)
class AuditConfig:
    service: str  # "allServices" or e.g. "bigquery.googleapis.com"
    log_configs: tuple[AuditLogConfig, ...] = ()


@dataclass(frozen=True)
class ProjectIam:
    bindings: tuple[IamBinding, ...] = ()
    audit_configs: tuple[AuditConfig, ...] = ()


# --- BigQuery metadata (datasets.get / tables.get) ---


@dataclass(frozen=True)
class AccessEntry:
    """One dataset-level grant, normalized by the adapter to `prefix:value` member
    form (`specialGroup:projectReaders`, `userByEmail:x@y`, `allAuthenticatedUsers`...)."""

    role: str
    member: str


@dataclass(frozen=True)
class SchemaField:
    """A leaf column; nested fields arrive flattened to dotted paths (FR-1.3)."""

    path: str
    field_type: str
    policy_tag_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class TableMeta:
    table_id: str
    table_type: str  # "TABLE" | "VIEW" | "EXTERNAL" | ...
    num_bytes: int
    creation_time: datetime
    expiration_time: datetime | None = None
    time_partitioning_field: str | None = None
    range_partitioning_field: str | None = None
    require_partition_filter: bool = False
    clustering_fields: tuple[str, ...] = ()
    schema_fields: tuple[SchemaField, ...] = ()

    @property
    def is_partitioned(self) -> bool:
        return self.time_partitioning_field is not None or (
            self.range_partitioning_field is not None
        )


@dataclass(frozen=True)
class DatasetMeta:
    dataset_id: str
    location: str
    default_table_expiration_ms: int | None = None
    default_partition_expiration_ms: int | None = None
    cmek_key: str | None = None
    access: tuple[AccessEntry, ...] = ()
    labels: tuple[tuple[str, str], ...] = ()
    tables: tuple[TableMeta, ...] = ()


# --- Data Catalog taxonomies (taxonomies.list + policyTags.list) ---


@dataclass(frozen=True)
class PolicyTag:
    name: str  # full resource name: projects/.../taxonomies/.../policyTags/...
    display_name: str


@dataclass(frozen=True)
class Taxonomy:
    name: str  # full resource name
    display_name: str
    location: str
    policy_tags: tuple[PolicyTag, ...] = ()


# --- Logging routing config (sinks.list / exclusions.list) ---


@dataclass(frozen=True)
class LogSink:
    name: str
    destination: str  # e.g. bigquery.googleapis.com/projects/p/datasets/d
    filter: str = ""
    disabled: bool = False


@dataclass(frozen=True)
class LogExclusion:
    name: str
    filter: str = ""
    disabled: bool = False


@dataclass(frozen=True)
class LoggingConfig:
    sinks: tuple[LogSink, ...] = ()
    exclusions: tuple[LogExclusion, ...] = ()


# --- The snapshot ---


@dataclass(frozen=True)
class SkippedResource:
    """Coverage bookkeeping (§4.2): anything not evaluated is listed with a reason —
    silent gaps would fake the 100%-coverage denominator."""

    resource: str
    reason: str


@dataclass(frozen=True)
class ProjectSnapshot:
    project_id: str
    captured_at: datetime  # injected Clock at collection time, never read in checks
    iam: ProjectIam = ProjectIam()
    datasets: tuple[DatasetMeta, ...] = ()
    taxonomies: tuple[Taxonomy, ...] = ()
    logging: LoggingConfig = LoggingConfig()
    skipped: tuple[SkippedResource, ...] = ()

    def __post_init__(self) -> None:
        if not self.project_id:
            raise ValueError("project_id must be non-empty")

    def dataset_path(self, dataset: DatasetMeta) -> str:
        return f"projects/{self.project_id}/datasets/{dataset.dataset_id}"

    def table_path(self, dataset: DatasetMeta, table: TableMeta) -> str:
        return f"{self.dataset_path(dataset)}/tables/{table.table_id}"
