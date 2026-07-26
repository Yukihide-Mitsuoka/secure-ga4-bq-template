"""Additive mart-metadata governance checkpoints CHK-12 and CHK-13."""

from __future__ import annotations

from src.modules.inspection.domain.catalog import SensitivityCatalog
from src.modules.inspection.domain.finding import Finding, Severity
from src.modules.inspection.domain.params import DatasetScope, InspectionParams
from src.modules.inspection.domain.snapshot import ProjectSnapshot

_IN_SCOPE = (DatasetScope.MART, DatasetScope.UNMATCHED)
_RESOURCE_TYPES = ("TABLE", "VIEW")


def check_chk12_missing_descriptions(
    snapshot: ProjectSnapshot,
    params: InspectionParams,
    catalog: SensitivityCatalog,
) -> list[Finding]:
    """CHK-12: tables, views, and leaf columns need non-empty descriptions."""
    findings: list[Finding] = []
    for dataset in snapshot.datasets:
        if params.classify(dataset.dataset_id) not in _IN_SCOPE:
            continue
        for table in dataset.tables:
            if table.table_type not in _RESOURCE_TYPES:
                continue
            table_path = snapshot.table_path(dataset, table)
            if _is_missing(table.description):
                findings.append(
                    Finding(
                        check_id="CHK-12",
                        severity=Severity.LOW,
                        resource=table_path,
                        observed="description is missing or whitespace-only",
                        expected="table or view has a non-empty BigQuery description",
                        rule_ref="FR-9.1",
                        remediation_hint=(
                            "add a description in the owning model or infrastructure definition"
                        ),
                    )
                )
            for field in table.schema_fields:
                if not _is_missing(field.description):
                    continue
                findings.append(
                    Finding(
                        check_id="CHK-12",
                        severity=Severity.LOW,
                        resource=f"{table_path}/columns/{field.path}",
                        observed="description is missing or whitespace-only",
                        expected="leaf column has a non-empty BigQuery description",
                        rule_ref="FR-9.1",
                        remediation_hint=(
                            "add a description in the owning model or infrastructure definition"
                        ),
                    )
                )
    return findings


def check_chk13_incomplete_promotion_sources(
    snapshot: ProjectSnapshot,
    params: InspectionParams,
    catalog: SensitivityCatalog,
) -> list[Finding]:
    """CHK-13: observed promoted leaf columns need complete source declarations."""
    findings: list[Finding] = []
    for dataset in snapshot.datasets:
        if params.classify(dataset.dataset_id) not in _IN_SCOPE:
            continue
        for table in dataset.tables:
            if table.table_type not in _RESOURCE_TYPES:
                continue
            table_path = snapshot.table_path(dataset, table)
            for field in table.schema_fields:
                if field.path not in catalog.promoted_columns:
                    continue
                missing = _missing_source_components(catalog, field.path)
                if not missing:
                    continue
                findings.append(
                    Finding(
                        check_id="CHK-13",
                        severity=Severity.LOW,
                        resource=f"{table_path}/columns/{field.path}",
                        observed=(
                            "promotion source declaration is missing " + " and ".join(missing)
                        ),
                        expected=(
                            "promoted column declares non-empty source.field_path and source.key"
                        ),
                        rule_ref="FR-10.1",
                        remediation_hint=(
                            "complete the structured promotion source declaration and review "
                            "the transformation separately"
                        ),
                    )
                )
    return findings


def _is_missing(description: str | None) -> bool:
    return description is None or not description.strip()


def _missing_source_components(
    catalog: SensitivityCatalog,
    column: str,
) -> tuple[str, ...]:
    source = catalog.promotion_source(column)
    if source is None:
        return ("source.field_path", "source.key")
    missing: list[str] = []
    if source.field_path is None or not source.field_path.strip():
        missing.append("source.field_path")
    if source.key is None or not source.key.strip():
        missing.append("source.key")
    return tuple(missing)
