"""Cost checkpoints CHK-08..10 (FR-4 #8-#10).

Table age (CHK-10) is measured against `snapshot.captured_at` — the injected
collection clock — never against wall time inside a check (MODULE.md #3).
"""

from __future__ import annotations

from collections.abc import Iterator

from src.modules.inspection.domain.catalog import SensitivityCatalog
from src.modules.inspection.domain.finding import Finding, Severity
from src.modules.inspection.domain.params import DatasetScope, InspectionParams
from src.modules.inspection.domain.snapshot import DatasetMeta, ProjectSnapshot, TableMeta

_IN_SCOPE = (DatasetScope.MART, DatasetScope.UNMATCHED)


def check_chk08_large_tables_unpartitioned(
    snapshot: ProjectSnapshot,
    params: InspectionParams,
    catalog: SensitivityCatalog,
) -> list[Finding]:
    """CHK-08: tables over the size threshold without partitioning (clustering: INFO)."""
    findings: list[Finding] = []
    threshold = params.thresholds.large_table_bytes
    for dataset, table in _tables(snapshot, params):
        if table.num_bytes < threshold:
            continue
        path = snapshot.table_path(dataset, table)
        if not table.is_partitioned:
            findings.append(
                Finding(
                    check_id="CHK-08",
                    severity=Severity.MEDIUM,
                    resource=path,
                    observed=f"{table.num_bytes} bytes with no partitioning",
                    expected=f"tables >= {threshold} bytes are partitioned",
                    rule_ref="FR-4 #8",
                    remediation_hint=(
                        "declare partition_by / bigquery.partitionBy in the model config"
                    ),
                )
            )
        if not table.clustering_fields:
            findings.append(
                Finding(
                    check_id="CHK-08",
                    severity=Severity.INFO,
                    resource=path,
                    observed=f"{table.num_bytes} bytes with no clustering",
                    expected="large tables cluster on their dominant filter columns",
                    rule_ref="FR-4 #8",
                    remediation_hint="declare cluster_by / bigquery.clusterBy in the model config",
                )
            )
    return findings


def check_chk09_partition_filter_not_required(
    snapshot: ProjectSnapshot,
    params: InspectionParams,
    catalog: SensitivityCatalog,
) -> list[Finding]:
    """CHK-09: partitioned tables that do not force a partition filter."""
    findings: list[Finding] = []
    for dataset, table in _tables(snapshot, params):
        if table.is_partitioned and not table.require_partition_filter:
            findings.append(
                Finding(
                    check_id="CHK-09",
                    severity=Severity.LOW,
                    resource=snapshot.table_path(dataset, table),
                    observed="require_partition_filter is false/unset on a partitioned table",
                    expected="partitioned tables force partition elimination",
                    rule_ref="FR-4 #9",
                    remediation_hint="set require_partition_filter=true in the model config",
                )
            )
    return findings


def check_chk10_long_lived_without_expiration(
    snapshot: ProjectSnapshot,
    params: InspectionParams,
    catalog: SensitivityCatalog,
) -> list[Finding]:
    """CHK-10: old tables with neither their own nor a dataset default expiration."""
    findings: list[Finding] = []
    max_age_days = params.thresholds.long_lived_days
    for dataset, table in _tables(snapshot, params):
        age_days = (snapshot.captured_at - table.creation_time).days
        if (
            age_days > max_age_days
            and table.expiration_time is None
            and dataset.default_table_expiration_ms is None
        ):
            findings.append(
                Finding(
                    check_id="CHK-10",
                    severity=Severity.LOW,
                    resource=snapshot.table_path(dataset, table),
                    observed=f"{age_days} days old with no expiration at any level",
                    expected=(
                        f"tables older than {max_age_days} days carry an expiration "
                        "or live in a dataset with a default"
                    ),
                    rule_ref="FR-4 #10",
                    remediation_hint="set an expiration, or document why this table is permanent",
                )
            )
    return findings


def _tables(
    snapshot: ProjectSnapshot, params: InspectionParams
) -> Iterator[tuple[DatasetMeta, TableMeta]]:
    for dataset in snapshot.datasets:
        if params.classify(dataset.dataset_id) not in _IN_SCOPE:
            continue
        for table in dataset.tables:
            if table.table_type == "TABLE":
                yield dataset, table
