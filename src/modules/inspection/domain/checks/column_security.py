"""Column-level-security checkpoints CHK-04..05 (FR-4 #4-#5).

CHK-04 is the catalog⇔tag consistency check — the exact failure mode the live
E2E run surfaced (policy tags silently not attached): a green build with
unprotected high columns. Views are skipped deliberately: BigQuery cannot tag
view columns; staging/intermediate views are protected by dataset IAM
(LOG-0010 — design, not a gap).
"""

from __future__ import annotations

from src.modules.inspection.domain.catalog import SensitivityCatalog
from src.modules.inspection.domain.finding import Finding, Severity
from src.modules.inspection.domain.params import DatasetScope, InspectionParams
from src.modules.inspection.domain.snapshot import ProjectSnapshot

_LEVEL_SEVERITY = {"high": Severity.HIGH, "medium": Severity.MEDIUM}


def check_chk04_catalog_columns_untagged(
    snapshot: ProjectSnapshot,
    params: InspectionParams,
    catalog: SensitivityCatalog,
) -> list[Finding]:
    """CHK-04: a cataloged high/medium column carries no policy tag."""
    findings: list[Finding] = []
    for dataset in snapshot.datasets:
        if params.classify(dataset.dataset_id) not in (DatasetScope.MART, DatasetScope.UNMATCHED):
            continue
        for table in dataset.tables:
            if table.table_type != "TABLE":
                continue  # views cannot carry policy tags (LOG-0010)
            for field in table.schema_fields:
                level = catalog.effective_level(field.path)
                severity = _LEVEL_SEVERITY.get(level or "")
                if severity is None or field.policy_tag_ids:
                    continue
                findings.append(
                    Finding(
                        check_id="CHK-04",
                        severity=severity,
                        resource=f"{snapshot.table_path(dataset, table)}/columns/{field.path}",
                        observed="no policy tag attached",
                        expected=f"policy tag level={level} (catalog: {field.path} -> {level})",
                        rule_ref="FR-4 #4",
                        remediation_hint=(
                            "declare policy_tags/bigqueryPolicyTags for this "
                            "column in the model config"
                        ),
                    )
                )
    return findings


def check_chk05_taxonomy_consistency(
    snapshot: ProjectSnapshot,
    params: InspectionParams,
    catalog: SensitivityCatalog,
) -> list[Finding]:
    """CHK-05: dangling tag references, taxonomy/dataset location mismatch, orphan tags."""
    known_tags = {tag.name for taxonomy in snapshot.taxonomies for tag in taxonomy.policy_tags}
    findings: list[Finding] = []
    used_tags: set[str] = set()

    for dataset in snapshot.datasets:
        if params.classify(dataset.dataset_id) is DatasetScope.EXCLUDED:
            continue
        for table in dataset.tables:
            for field in table.schema_fields:
                for tag_id in field.policy_tag_ids:
                    used_tags.add(tag_id)
                    column_path = f"{snapshot.table_path(dataset, table)}/columns/{field.path}"
                    if tag_id not in known_tags:
                        findings.append(
                            Finding(
                                check_id="CHK-05",
                                severity=Severity.HIGH,
                                resource=column_path,
                                observed=(
                                    f"references policy tag {tag_id} which no taxonomy defines"
                                ),
                                expected="every column tag resolves to an existing taxonomy tag",
                                rule_ref="FR-4 #5",
                                remediation_hint=(
                                    "re-point the column at a live tag or recreate the taxonomy"
                                ),
                            )
                        )
                        continue
                    tag_location = _location_of(tag_id)
                    if (
                        tag_location is not None
                        and tag_location.lower() != dataset.location.lower()
                    ):
                        findings.append(
                            Finding(
                                check_id="CHK-05",
                                severity=Severity.HIGH,
                                resource=column_path,
                                observed=(
                                    f"tag location {tag_location} != "
                                    f"dataset location {dataset.location}"
                                ),
                                expected=(
                                    "taxonomy location equals dataset location — "
                                    "CLS silently fails otherwise"
                                ),
                                rule_ref="FR-4 #5",
                                remediation_hint="recreate the taxonomy in the dataset's location",
                            )
                        )

    for taxonomy in snapshot.taxonomies:
        for tag in taxonomy.policy_tags:
            if tag.name not in used_tags:
                findings.append(
                    Finding(
                        check_id="CHK-05",
                        severity=Severity.INFO,
                        resource=tag.name,
                        observed=f"policy tag '{tag.display_name}' is attached to no column",
                        expected="declared tags are in use (orphans usually mean drift)",
                        rule_ref="FR-4 #5",
                        remediation_hint="attach it where the catalog demands, or remove the level",
                    )
                )
    return findings


def _location_of(tag_resource_name: str) -> str | None:
    """Extract the location segment of projects/P/locations/L/taxonomies/..."""
    parts = tag_resource_name.split("/")
    try:
        index = parts.index("locations")
    except ValueError:
        return None
    return parts[index + 1] if index + 1 < len(parts) else None
