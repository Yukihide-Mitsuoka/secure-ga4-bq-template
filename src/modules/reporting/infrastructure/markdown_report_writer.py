from __future__ import annotations

import html
import os
import tempfile
from pathlib import Path

from src.modules.reporting.domain.model import GeneratedNarrative, InspectionArtifact


class MarkdownReportWriter:
    def write(
        self, artifact: InspectionArtifact, narrative: GeneratedNarrative, out_dir: Path
    ) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        target = out_dir / "ai-report.md"
        if target.exists():
            raise FileExistsError(f"report already exists: {target}")
        content = _render(artifact, narrative)
        descriptor, temporary_name = tempfile.mkstemp(prefix=".ai-report-", dir=out_dir)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.link(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
        return target


def _render(artifact: InspectionArtifact, narrative: GeneratedNarrative) -> str:
    finding_by_ref = {finding.ref: finding for finding in artifact.findings}
    lines = [
        "# AI-generated inspection report",
        "",
        "> Draft: human review is required. Deterministic findings remain authoritative.",
        "",
        f"- Project: {_code(artifact.project_id)}",
        f"- Captured at: {_code(artifact.captured_at)}",
        f"- Coverage: {artifact.coverage.datasets} datasets, {artifact.coverage.tables} tables, "
        f"{artifact.coverage.columns} columns",
        f"- Generator: {_code(narrative.provider)} / {_code(narrative.model)}",
        "",
        "## Executive summary",
        "",
        _prose(narrative.executive_summary),
    ]
    for generated in narrative.findings:
        finding = finding_by_ref[generated.ref]
        lines.extend(
            [
                "",
                f"## {finding.ref}: {finding.check_id}",
                "",
                f"- Severity: **{finding.severity}**",
                f"- Resource: {_code(finding.resource)}",
                f"- Rule: {_code(finding.rule_ref)}",
                "",
                "### Explanation",
                "",
                _prose(generated.explanation),
                "",
                "### Next action",
                "",
                _prose(generated.next_action),
            ]
        )
    lines.extend(
        [
            "",
            "## Generation metadata",
            "",
            f"- Request ID: {_code(narrative.request_id or 'unavailable')}",
            "",
        ]
    )
    return "\n".join(lines)


def _prose(value: str) -> str:
    return html.escape(value, quote=True)


def _code(value: str) -> str:
    return f"`{html.escape(value, quote=True).replace('`', '&#96;')}`"
