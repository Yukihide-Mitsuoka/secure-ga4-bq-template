"""Collection and configuration ports (design §3).

The application layer owns these interfaces; `infrastructure/` implements them
(dependency inversion, ARC-002). Every collection port is **read-only by
contract** — an implementation that mutates anything violates MODULE.md
invariant #1 (FR-6, GR-030). Unit tests fake these with builders; no GCP, no
network, deterministic (TST-020: mock only at port boundaries).

The GCP ports return the *flat* domain records; assembling the nested
`ProjectSnapshot` tree (datasets containing tables, etc.) is the collection
use case's job (design §8 PR 7), so adapters stay one-API-call-per-method.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from src.modules.inspection.domain.catalog import SensitivityCatalog
from src.modules.inspection.domain.params import InspectionParams
from src.modules.inspection.domain.snapshot import (
    DatasetMeta,
    LogExclusion,
    LogSink,
    ProjectIam,
    TableMeta,
    Taxonomy,
)


class BigQueryMetadataPort(Protocol):
    """BigQuery REST metadata reads (datasets.*/tables.* — never jobs.*, ADR-0003)."""

    def list_datasets(self, project_id: str) -> tuple[str, ...]:
        """All dataset ids in the project (paginated fully by the adapter)."""
        ...

    def get_dataset(self, project_id: str, dataset_id: str) -> DatasetMeta:
        """One dataset's metadata; `tables` is left empty — the use case fills it."""
        ...

    def list_tables(self, project_id: str, dataset_id: str) -> tuple[str, ...]:
        """All table ids in the dataset (paginated fully by the adapter)."""
        ...

    def get_table(self, project_id: str, dataset_id: str, table_id: str) -> TableMeta:
        """One table's metadata incl. schema with per-field policy tags."""
        ...


class IamPolicyPort(Protocol):
    def get_project_iam_policy(self, project_id: str) -> ProjectIam:
        """Project IAM policy v3: bindings + auditConfigs (checkpoints 1-3, 6)."""
        ...


class TaxonomyPort(Protocol):
    def list_taxonomies(self, project_id: str, location: str) -> tuple[Taxonomy, ...]:
        """Taxonomies with their policy tags in one location (checkpoint 5)."""
        ...


class LoggingConfigPort(Protocol):
    def list_sinks(self, project_id: str) -> tuple[LogSink, ...]: ...

    def list_exclusions(self, project_id: str) -> tuple[LogExclusion, ...]: ...


class CatalogRepository(Protocol):
    def load(self) -> SensitivityCatalog:
        """The sensitivity catalog (FR-1.1/1.2); source location is the
        implementation's concern — the engagement params carry the path."""
        ...


class ParamsRepository(Protocol):
    def load(self, path: str) -> InspectionParams:
        """Engagement parameters (FR-7) from the given file path."""
        ...


class Clock(Protocol):
    def now(self) -> datetime:
        """Injected time source (MODULE.md invariant #3 — never wall time in domain)."""
        ...
