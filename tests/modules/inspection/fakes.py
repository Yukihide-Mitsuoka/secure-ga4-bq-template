"""Port-level fakes for use-case tests (TST-020: fake at the port boundary).

These implement the application/ports.py Protocols in memory. Prefer these
over service-level fakes when testing use cases — the adapters' JSON
translation is covered by their own unit tests.
"""

from __future__ import annotations

from datetime import datetime

from src.modules.inspection.domain.catalog import SensitivityCatalog
from src.modules.inspection.domain.snapshot import (
    DatasetMeta,
    LogExclusion,
    LogSink,
    ProjectIam,
    TableMeta,
    Taxonomy,
)
from tests.modules.inspection.builders import FIXED_NOW


class FakeBigQueryPort:
    def __init__(
        self,
        datasets: dict[str, DatasetMeta],
        tables: dict[str, dict[str, TableMeta]] | None = None,
        failing_tables: frozenset[str] = frozenset(),
    ) -> None:
        self._datasets = datasets
        self._tables = tables or {}
        self._failing_tables = failing_tables

    def list_datasets(self, project_id: str) -> tuple[str, ...]:
        return tuple(self._datasets)

    def get_dataset(self, project_id: str, dataset_id: str) -> DatasetMeta:
        return self._datasets[dataset_id]

    def list_tables(self, project_id: str, dataset_id: str) -> tuple[str, ...]:
        return tuple(self._tables.get(dataset_id, {}))

    def get_table(self, project_id: str, dataset_id: str, table_id: str) -> TableMeta:
        if table_id in self._failing_tables:
            raise RuntimeError("boom: simulated tables.get failure")
        return self._tables[dataset_id][table_id]


class FakeIamPort:
    def __init__(self, iam: ProjectIam | None = None) -> None:
        self._iam = iam if iam is not None else ProjectIam()

    def get_project_iam_policy(self, project_id: str) -> ProjectIam:
        return self._iam


class FakeTaxonomyPort:
    def __init__(self, taxonomies: tuple[Taxonomy, ...] = ()) -> None:
        self._taxonomies = taxonomies
        self.requested_location: str | None = None

    def list_taxonomies(self, project_id: str, location: str) -> tuple[Taxonomy, ...]:
        self.requested_location = location
        return self._taxonomies


class FakeLoggingPort:
    def __init__(
        self, sinks: tuple[LogSink, ...] = (), exclusions: tuple[LogExclusion, ...] = ()
    ) -> None:
        self._sinks = sinks
        self._exclusions = exclusions

    def list_sinks(self, project_id: str) -> tuple[LogSink, ...]:
        return self._sinks

    def list_exclusions(self, project_id: str) -> tuple[LogExclusion, ...]:
        return self._exclusions


class FixedClock:
    def __init__(self, moment: datetime = FIXED_NOW) -> None:
        self._moment = moment

    def now(self) -> datetime:
        return self._moment


class FakeCatalogRepository:
    def __init__(self, catalog: SensitivityCatalog) -> None:
        self._catalog = catalog

    def load(self) -> SensitivityCatalog:
        return self._catalog
