"""Use case: assemble the immutable ProjectSnapshot through the read-only ports.

Scoping happens at collection time (§4.2): excluded datasets are skipped with a
recorded reason, raw `analytics_*` datasets are collected containment-only (no
table walk — their IAM still feeds CHK-01..03), mart/unmatched datasets get the
full table+schema walk. A table whose fetch fails is recorded in `skipped`
rather than aborting or vanishing — the coverage denominator stays honest
(COD-010: recording IS the handling here).
"""

from __future__ import annotations

from dataclasses import replace

from src.modules.inspection.application.ports import (
    BigQueryMetadataPort,
    Clock,
    IamPolicyPort,
    LoggingConfigPort,
    TaxonomyPort,
)
from src.modules.inspection.domain.params import DatasetScope, InspectionParams
from src.modules.inspection.domain.snapshot import (
    DatasetMeta,
    LoggingConfig,
    ProjectSnapshot,
    SkippedResource,
    TableMeta,
)


class CollectSnapshot:
    def __init__(
        self,
        bigquery: BigQueryMetadataPort,
        iam: IamPolicyPort,
        taxonomies: TaxonomyPort,
        logging_config: LoggingConfigPort,
        clock: Clock,
    ) -> None:
        self._bigquery = bigquery
        self._iam = iam
        self._taxonomies = taxonomies
        self._logging_config = logging_config
        self._clock = clock

    def collect(self, params: InspectionParams) -> ProjectSnapshot:
        project_id = params.project_id
        datasets: list[DatasetMeta] = []
        skipped: list[SkippedResource] = []

        for dataset_id in self._bigquery.list_datasets(project_id):
            scope = params.classify(dataset_id)
            dataset_path = f"projects/{project_id}/datasets/{dataset_id}"
            if scope is DatasetScope.EXCLUDED:
                skipped.append(SkippedResource(dataset_path, "excluded by engagement params"))
                continue
            dataset = self._bigquery.get_dataset(project_id, dataset_id)
            if scope is DatasetScope.RAW:
                # Containment-only (§4.2): dataset IAM feeds CHK-01..03; the raw
                # export's tables are deliberately outside the column denominator.
                skipped.append(
                    SkippedResource(f"{dataset_path}/tables", "raw export scope: containment-only")
                )
                datasets.append(dataset)
                continue
            tables, table_skips = self._collect_tables(project_id, dataset_id, dataset_path)
            skipped.extend(table_skips)
            datasets.append(replace(dataset, tables=tables))

        return ProjectSnapshot(
            project_id=project_id,
            captured_at=self._clock.now(),
            iam=self._iam.get_project_iam_policy(project_id),
            datasets=tuple(datasets),
            taxonomies=self._taxonomies.list_taxonomies(project_id, params.expected_location),
            logging=LoggingConfig(
                sinks=self._logging_config.list_sinks(project_id),
                exclusions=self._logging_config.list_exclusions(project_id),
            ),
            skipped=tuple(skipped),
        )

    def _collect_tables(
        self, project_id: str, dataset_id: str, dataset_path: str
    ) -> tuple[tuple[TableMeta, ...], list[SkippedResource]]:
        tables: list[TableMeta] = []
        skips: list[SkippedResource] = []
        for table_id in self._bigquery.list_tables(project_id, dataset_id):
            try:
                tables.append(self._bigquery.get_table(project_id, dataset_id, table_id))
            except Exception as error:  # noqa: BLE001 — recorded, never silent (COD-010)
                skips.append(
                    SkippedResource(
                        f"{dataset_path}/tables/{table_id}", f"collection failed: {error}"
                    )
                )
        return tuple(tables), skips
