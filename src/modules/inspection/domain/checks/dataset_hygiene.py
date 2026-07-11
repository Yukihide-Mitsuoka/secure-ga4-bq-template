"""Dataset-hygiene checkpoint CHK-11 (FR-4 #11).

CMEK severity is parameter-driven (design §2.2): absence is INFO by default and
HIGH only when the engagement declares `require_cmek: true` — determinism means
the rule never guesses the engagement's compliance posture.
"""

from __future__ import annotations

from src.modules.inspection.domain.catalog import SensitivityCatalog
from src.modules.inspection.domain.finding import Finding, Severity
from src.modules.inspection.domain.params import DatasetScope, InspectionParams
from src.modules.inspection.domain.snapshot import ProjectSnapshot

_IN_SCOPE = (DatasetScope.MART, DatasetScope.UNMATCHED)


def check_chk11_dataset_hygiene(
    snapshot: ProjectSnapshot,
    params: InspectionParams,
    catalog: SensitivityCatalog,
) -> list[Finding]:
    """CHK-11: location deviation / missing default expiration / CMEK posture."""
    findings: list[Finding] = []
    for dataset in snapshot.datasets:
        if params.classify(dataset.dataset_id) not in _IN_SCOPE:
            continue
        resource = snapshot.dataset_path(dataset)
        if dataset.location != params.expected_location:
            findings.append(
                Finding(
                    check_id="CHK-11",
                    severity=Severity.MEDIUM,
                    resource=resource,
                    observed=f"location {dataset.location} != expected {params.expected_location}",
                    expected=(
                        "all governed datasets share the engagement location (CLS location match)"
                    ),
                    rule_ref="FR-4 #11",
                    remediation_hint="recreate the dataset in the expected location",
                )
            )
        if dataset.default_table_expiration_ms is None:
            findings.append(
                Finding(
                    check_id="CHK-11",
                    severity=Severity.LOW,
                    resource=resource,
                    observed="no default table expiration on the dataset",
                    expected="a default expiration bounds accidental long-term storage",
                    rule_ref="FR-4 #11",
                    remediation_hint=(
                        "set default_table_expiration_ms (bigquery-dataset module input)"
                    ),
                )
            )
        if dataset.cmek_key is None:
            severity = Severity.HIGH if params.thresholds.require_cmek else Severity.INFO
            findings.append(
                Finding(
                    check_id="CHK-11",
                    severity=severity,
                    resource=resource,
                    observed="dataset is not CMEK-encrypted (Google-managed keys)",
                    expected=(
                        "CMEK required by this engagement"
                        if params.thresholds.require_cmek
                        else "CMEK optional for this engagement (informational)"
                    ),
                    rule_ref="FR-4 #11",
                    remediation_hint="set default_encryption_configuration with a KMS key",
                )
            )
    return findings
