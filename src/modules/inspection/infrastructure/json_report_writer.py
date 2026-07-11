"""findings.json writer — the machine-readable report (FR-5, design §5).

This file is the frame the A-level AI report generator consumes: the engine
decides, AI only writes prose inside it. Byte-determinism matters (§6
idempotence): keys sorted, findings pre-sorted by the use case, stable
serialization for every field.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.modules.inspection.domain.report import Report


class JsonReportWriter:
    def write(self, report: Report, out_dir: Path) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "findings.json"
        path.write_text(
            json.dumps(_as_dict(report), sort_keys=True, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return path


def _as_dict(report: Report) -> dict[str, Any]:
    params = report.params
    return {
        "meta": {
            "project_id": report.project_id,
            "captured_at": report.captured_at.isoformat(),
            "params": {
                "expected_location": params.expected_location,
                "mart_patterns": list(params.mart_patterns),
                "raw_patterns": list(params.raw_patterns),
                "exclude": list(params.exclude),
                "audit": {
                    "high_sensitivity_datasets": list(params.audit.high_sensitivity_datasets),
                    "retention_max_days": params.audit.retention_max_days,
                },
                "thresholds": {
                    "large_table_bytes": params.thresholds.large_table_bytes,
                    "long_lived_days": params.thresholds.long_lived_days,
                    "require_cmek": params.thresholds.require_cmek,
                },
                "catalog_path": params.catalog_path,
            },
        },
        "coverage": {
            "datasets": report.coverage.datasets,
            "tables": report.coverage.tables,
            "columns": report.coverage.columns,
            "skipped": [
                {"resource": s.resource, "reason": s.reason} for s in report.coverage.skipped
            ],
        },
        "findings": [
            {
                "check_id": f.check_id,
                "severity": f.severity.value,
                "resource": f.resource,
                "observed": f.observed,
                "expected": f.expected,
                "rule_ref": f.rule_ref,
                "remediation_hint": f.remediation_hint,
            }
            for f in report.findings
        ],
    }
