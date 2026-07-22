"""findings.csv writer — the flat machine-readable finding list (FR-5).

JSON remains the authoritative full report. CSV projects only the existing finding
vocabulary for spreadsheet and audit-tool consumption, preserving report order and
using explicit line endings so identical reports produce identical bytes.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

from src.modules.inspection.domain.report import Report

_FIELD_NAMES = (
    "check_id",
    "severity",
    "resource",
    "observed",
    "expected",
    "rule_ref",
    "remediation_hint",
)


class CsvReportWriter:
    def write(self, report: Report, out_dir: Path) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "findings.csv"
        buffer = io.StringIO(newline="")
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(_FIELD_NAMES)
        for finding in report.findings:
            writer.writerow(
                (
                    finding.check_id,
                    finding.severity.value,
                    finding.resource,
                    finding.observed,
                    finding.expected,
                    finding.rule_ref,
                    finding.remediation_hint,
                )
            )
        path.write_bytes(buffer.getvalue().encode("utf-8"))
        return path
