"""summary.md writer — the deterministic human-readable rendering (FR-5).

Pure template over the already-sorted Report; no LLM involved (the repo-wide
principle: deterministic guards decide, AI writes prose elsewhere, later).
"""

from __future__ import annotations

from pathlib import Path

from src.modules.inspection.domain.finding import Severity
from src.modules.inspection.domain.report import Report


class MarkdownReportWriter:
    def write(self, report: Report, out_dir: Path) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "summary.md"
        path.write_text("\n".join(_render(report)) + "\n", encoding="utf-8")
        return path


def _render(report: Report) -> list[str]:
    lines = [
        f"# Inspection summary — {report.project_id}",
        "",
        f"Captured at: {report.captured_at.isoformat()}",
        "",
        "## Coverage (§4.2 denominator)",
        "",
        "| Datasets | Tables | Columns | Skipped |",
        "|---------:|-------:|--------:|--------:|",
        (
            f"| {report.coverage.datasets} | {report.coverage.tables} "
            f"| {report.coverage.columns} | {len(report.coverage.skipped)} |"
        ),
    ]
    if report.coverage.skipped:
        lines += ["", "### Skipped (with reasons — nothing silently disappears)", ""]
        lines += [f"- `{s.resource}` — {s.reason}" for s in report.coverage.skipped]

    lines += ["", "## Findings by severity", ""]
    counts = report.severity_counts()
    for severity in Severity:
        lines.append(f"- {severity.value}: {counts.get(severity.value, 0)}")

    lines += ["", "## Findings by checkpoint", ""]
    if not report.findings:
        lines.append("No findings detected in the evaluated scope.")
    for check_id in sorted({f.check_id for f in report.findings}):
        check_findings = [f for f in report.findings if f.check_id == check_id]
        lines += [f"### {check_id} ({check_findings[0].rule_ref}) — {len(check_findings)}", ""]
        for f in check_findings:
            lines.append(
                f"- [{f.severity.value}] `{f.resource}` — {f.observed} "
                f"(expected: {f.expected}; fix: {f.remediation_hint})"
            )
        lines.append("")
    return lines
