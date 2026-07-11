"""IAM checkpoints CHK-01..03 (FR-4 #1-#3).

Severity for basic roles follows the owner ruling in LOG-0014: owner/editor are
HIGH, viewer is detected one notch lighter at MEDIUM (FR-2 bans all three).
"""

from __future__ import annotations

from src.modules.inspection.domain.catalog import SensitivityCatalog
from src.modules.inspection.domain.finding import Finding, Severity
from src.modules.inspection.domain.params import DatasetScope, InspectionParams
from src.modules.inspection.domain.snapshot import ProjectSnapshot

_BASIC_ROLE_SEVERITY = {
    "roles/owner": Severity.HIGH,
    "roles/editor": Severity.HIGH,
    "roles/viewer": Severity.MEDIUM,
}

_PUBLIC_MEMBERS = frozenset(
    {"allUsers", "allAuthenticatedUsers", "specialGroup:allAuthenticatedUsers"}
)

# Broad BigQuery data access that belongs at dataset/table grain, not project grain.
_PROJECT_WIDE_BQ_ROLES = frozenset(
    {
        "roles/bigquery.dataViewer",
        "roles/bigquery.dataEditor",
        "roles/bigquery.dataOwner",
        "roles/bigquery.admin",
    }
)


def check_chk01_basic_roles(
    snapshot: ProjectSnapshot,
    params: InspectionParams,
    catalog: SensitivityCatalog,
) -> list[Finding]:
    """CHK-01: basic roles granted on the project or on a dataset."""
    findings: list[Finding] = []
    for binding in snapshot.iam.bindings:
        severity = _BASIC_ROLE_SEVERITY.get(binding.role)
        if severity is None:
            continue
        for member in binding.members:
            findings.append(
                Finding(
                    check_id="CHK-01",
                    severity=severity,
                    resource=f"projects/{snapshot.project_id}",
                    observed=f"{binding.role} bound to {member} at project level",
                    expected="no basic roles anywhere (FR-2); use dataset/table-grain roles",
                    rule_ref="FR-4 #1",
                    remediation_hint=(
                        f"remove {binding.role} from {member}; "
                        "replace with the narrowest predefined role"
                    ),
                )
            )
    for dataset in snapshot.datasets:
        if params.classify(dataset.dataset_id) is DatasetScope.EXCLUDED:
            continue
        for entry in dataset.access:
            severity = _BASIC_ROLE_SEVERITY.get(entry.role)
            if severity is None:
                continue
            findings.append(
                Finding(
                    check_id="CHK-01",
                    severity=severity,
                    resource=snapshot.dataset_path(dataset),
                    observed=f"{entry.role} granted to {entry.member} on the dataset",
                    expected="no basic roles anywhere (FR-2)",
                    rule_ref="FR-4 #1",
                    remediation_hint=(
                        f"remove {entry.role} from {entry.member} on {dataset.dataset_id}"
                    ),
                )
            )
    return findings


def check_chk02_public_members(
    snapshot: ProjectSnapshot,
    params: InspectionParams,
    catalog: SensitivityCatalog,
) -> list[Finding]:
    """CHK-02: any grant to allUsers / allAuthenticatedUsers."""
    findings: list[Finding] = []
    for binding in snapshot.iam.bindings:
        for member in binding.members:
            if member in _PUBLIC_MEMBERS:
                findings.append(
                    _public_finding(
                        resource=f"projects/{snapshot.project_id}",
                        role=binding.role,
                        member=member,
                        where="project IAM",
                    )
                )
    for dataset in snapshot.datasets:
        if params.classify(dataset.dataset_id) is DatasetScope.EXCLUDED:
            continue
        for entry in dataset.access:
            if entry.member in _PUBLIC_MEMBERS:
                findings.append(
                    _public_finding(
                        resource=snapshot.dataset_path(dataset),
                        role=entry.role,
                        member=entry.member,
                        where="dataset access",
                    )
                )
    return findings


def check_chk03_project_wide_data_roles(
    snapshot: ProjectSnapshot,
    params: InspectionParams,
    catalog: SensitivityCatalog,
) -> list[Finding]:
    """CHK-03: BigQuery data roles bound at project scope instead of dataset/table."""
    findings: list[Finding] = []
    for binding in snapshot.iam.bindings:
        if binding.role not in _PROJECT_WIDE_BQ_ROLES:
            continue
        for member in binding.members:
            findings.append(
                Finding(
                    check_id="CHK-03",
                    severity=Severity.MEDIUM,
                    resource=f"projects/{snapshot.project_id}",
                    observed=f"{binding.role} bound to {member} project-wide",
                    expected="BigQuery data access granted per dataset/table (FR-2)",
                    rule_ref="FR-4 #3",
                    remediation_hint=(
                        f"move {member} to dataset-level access on the datasets it actually needs"
                    ),
                )
            )
    return findings


def _public_finding(*, resource: str, role: str, member: str, where: str) -> Finding:
    return Finding(
        check_id="CHK-02",
        severity=Severity.HIGH,
        resource=resource,
        observed=f"{role} granted to {member} in {where}",
        expected="no grants to allUsers/allAuthenticatedUsers",
        rule_ref="FR-4 #2",
        remediation_hint=f"remove the {member} grant immediately",
    )
