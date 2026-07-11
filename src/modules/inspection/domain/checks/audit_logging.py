"""Audit-logging checkpoints CHK-06..07 (FR-4 #6-#7, FR-3 four-layer design).

Sink-filter recognition uses a deliberately small v1 grammar (design §9 open
point 1): a filter "ingests BigQuery data access" when it mentions the
`data_access` log or `BigQueryAuditMetadata`; it is an "audit sink" when it
mentions `cloudaudit.googleapis.com` or `bigquery`. Extend by evidence from
real engagements — never by speculation (COD-051).
"""

from __future__ import annotations

from src.modules.inspection.domain.catalog import SensitivityCatalog
from src.modules.inspection.domain.finding import Finding, Severity
from src.modules.inspection.domain.params import InspectionParams
from src.modules.inspection.domain.snapshot import LogSink, ProjectSnapshot

_DATA_ACCESS_LOG_TYPES = frozenset({"DATA_READ", "DATA_WRITE"})
_BQ_DESTINATION_PREFIX = "bigquery.googleapis.com/projects/"
_GCS_DESTINATION_PREFIX = "storage.googleapis.com/"

_MS_PER_DAY = 24 * 60 * 60 * 1000


def check_chk06_data_access_overenabled(
    snapshot: ProjectSnapshot,
    params: InspectionParams,
    catalog: SensitivityCatalog,
) -> list[Finding]:
    """CHK-06: Data Access audit logs enabled wider than the high-sensitivity scope."""
    findings: list[Finding] = []
    project = f"projects/{snapshot.project_id}"
    declared = params.audit.high_sensitivity_datasets

    for config in snapshot.iam.audit_configs:
        data_types = sorted(
            lc.log_type for lc in config.log_configs if lc.log_type in _DATA_ACCESS_LOG_TYPES
        )
        if not data_types:
            continue
        if config.service == "allServices":
            findings.append(
                _chk06(
                    resource=project,
                    observed=f"auditConfigs enable {'/'.join(data_types)} for allServices",
                    hint="restrict Data Access logging to the services that need it (FR-3 layer 2)",
                )
            )
        elif config.service == "bigquery.googleapis.com" and not declared:
            findings.append(
                _chk06(
                    resource=project,
                    observed=(
                        f"auditConfigs enable {'/'.join(data_types)} for BigQuery, but the "
                        "engagement declares no high-sensitivity datasets"
                    ),
                    hint=(
                        "declare audit.high_sensitivity_datasets or "
                        "disable BigQuery Data Access logs"
                    ),
                )
            )

    for sink in snapshot.logging.sinks:
        if sink.disabled or not _ingests_bq_data_access(sink):
            continue
        if not declared or not any(name in sink.filter for name in declared):
            findings.append(
                _chk06(
                    resource=f"{project}/sinks/{sink.name}",
                    observed=(
                        "sink ingests BigQuery data-access entries without "
                        "a high-sensitivity dataset restriction"
                    ),
                    hint=(
                        "narrow the sink filter to the declared "
                        "high-sensitivity datasets (FR-3 layer 2)"
                    ),
                )
            )
    return findings


def check_chk07_audit_pipeline(
    snapshot: ProjectSnapshot,
    params: InspectionParams,
    catalog: SensitivityCatalog,
) -> list[Finding]:
    """CHK-07: audit sink absent / retention excessive / no exclusion filters."""
    findings: list[Finding] = []
    project = f"projects/{snapshot.project_id}"
    audit_sinks = [s for s in snapshot.logging.sinks if not s.disabled and _is_audit_sink(s)]

    if not audit_sinks:
        findings.append(
            Finding(
                check_id="CHK-07",
                severity=Severity.MEDIUM,
                resource=project,
                observed="no enabled sink routes BigQuery audit logs anywhere",
                expected="audit logs routed to BQ/GCS with bounded retention (FR-3 layer 4)",
                rule_ref="FR-4 #7",
                remediation_hint="add a log-router-sink (library module) targeting BQ or GCS",
            )
        )

    for sink in audit_sinks:
        findings.extend(_retention_findings(snapshot, params, sink))

    if not any(not e.disabled for e in snapshot.logging.exclusions):
        findings.append(
            Finding(
                check_id="CHK-07",
                severity=Severity.LOW,
                resource=project,
                observed="no enabled Cloud Logging exclusion filters",
                expected="noise excluded before ingestion (FR-3 layer 3)",
                rule_ref="FR-4 #7",
                remediation_hint="add exclusion filters for high-volume noise logs",
            )
        )
    return findings


def _retention_findings(
    snapshot: ProjectSnapshot, params: InspectionParams, sink: LogSink
) -> list[Finding]:
    resource = f"projects/{snapshot.project_id}/sinks/{sink.name}"
    if sink.destination.startswith(_BQ_DESTINATION_PREFIX):
        dataset_id = sink.destination.rsplit("/", 1)[-1]
        dataset = next((d for d in snapshot.datasets if d.dataset_id == dataset_id), None)
        if dataset is None:
            return [
                Finding(
                    check_id="CHK-07",
                    severity=Severity.INFO,
                    resource=resource,
                    observed=f"destination dataset {dataset_id} is outside this project snapshot",
                    expected="retention verifiable on the destination",
                    rule_ref="FR-4 #7",
                    remediation_hint="inspect the destination project separately",
                )
            ]
        max_ms = params.audit.retention_max_days * _MS_PER_DAY
        expiration = dataset.default_table_expiration_ms
        if expiration is None or expiration > max_ms:
            observed = (
                "destination dataset has no default table expiration"
                if expiration is None
                else f"destination retention {expiration // _MS_PER_DAY} days exceeds the ceiling"
            )
            return [
                Finding(
                    check_id="CHK-07",
                    severity=Severity.MEDIUM,
                    resource=resource,
                    observed=observed,
                    expected=f"retention <= {params.audit.retention_max_days} days (FR-3 layer 4)",
                    rule_ref="FR-4 #7",
                    remediation_hint="set default_table_expiration_ms on the destination dataset",
                )
            ]
        return []
    if sink.destination.startswith(_GCS_DESTINATION_PREFIX):
        return [
            Finding(
                check_id="CHK-07",
                severity=Severity.INFO,
                resource=resource,
                observed=(
                    "GCS destination: bucket lifecycle is not readable with the inspector role"
                ),
                expected="retention bounded via bucket lifecycle (verify out of band)",
                rule_ref="FR-4 #7",
                remediation_hint="confirm the bucket lifecycle rule manually or extend the role",
            )
        ]
    return []


def _ingests_bq_data_access(sink: LogSink) -> bool:
    return "data_access" in sink.filter or "BigQueryAuditMetadata" in sink.filter


def _is_audit_sink(sink: LogSink) -> bool:
    lowered = sink.filter.lower()
    return "cloudaudit.googleapis.com" in lowered or "bigquery" in lowered


def _chk06(*, resource: str, observed: str, hint: str) -> Finding:
    return Finding(
        check_id="CHK-06",
        severity=Severity.MEDIUM,
        resource=resource,
        observed=observed,
        expected="Data Access logging limited to high-sensitivity data (FR-3 layer 2)",
        rule_ref="FR-4 #6",
        remediation_hint=hint,
    )
