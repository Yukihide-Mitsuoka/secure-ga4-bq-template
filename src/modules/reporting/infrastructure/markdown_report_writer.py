from __future__ import annotations

import html
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from src.modules.reporting.domain.model import (
    GeneratedNarrative,
    InspectionArtifact,
    ReportLanguage,
)

_MARKDOWN_SPECIALS = frozenset("\\`*_{}[]()#+-.!|>")


@dataclass(frozen=True)
class _ReportLabels:
    title: str
    notice: str
    project: str
    captured_at: str
    coverage_label: str
    coverage_format: str
    generator: str
    executive_summary: str
    severity: str
    resource: str
    rule: str
    explanation: str
    remediation_hint: str
    next_action: str
    generation_metadata: str
    request_id: str
    unavailable: str


_REPORT_LABELS = {
    ReportLanguage.ENGLISH: _ReportLabels(
        title="AI-generated inspection report",
        notice="Draft: human review is required. Deterministic findings remain authoritative.",
        project="Project",
        captured_at="Captured at",
        coverage_label="Coverage",
        coverage_format="{datasets} datasets, {tables} tables, {columns} columns",
        generator="Generator",
        executive_summary="Executive summary",
        severity="Severity",
        resource="Resource",
        rule="Rule",
        explanation="Explanation",
        remediation_hint="Deterministic remediation hint",
        next_action="Next action",
        generation_metadata="Generation metadata",
        request_id="Request ID",
        unavailable="unavailable",
    ),
    ReportLanguage.JAPANESE: _ReportLabels(
        title="AI生成点検レポート",
        notice="草案: 人によるレビューが必要です。決定論的なfindingが正準です。",
        project="プロジェクト",
        captured_at="取得日時",
        coverage_label="対象範囲",
        coverage_format="{datasets} データセット、{tables} テーブル、{columns} カラム",
        generator="生成元",
        executive_summary="エグゼクティブサマリー",
        severity="重大度",
        resource="リソース",
        rule="ルール",
        explanation="説明",
        remediation_hint="決定論的な是正ヒント",
        next_action="次のアクション",
        generation_metadata="生成メタデータ",
        request_id="リクエストID",
        unavailable="取得不可",
    ),
}


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
    labels = _REPORT_LABELS[narrative.language]
    coverage = labels.coverage_format.format(
        datasets=artifact.coverage.datasets,
        tables=artifact.coverage.tables,
        columns=artifact.coverage.columns,
    )
    lines = [
        f"# {labels.title}",
        "",
        f"> {labels.notice}",
        "",
        f"- {labels.project}: {_code(artifact.project_id)}",
        f"- {labels.captured_at}: {_code(artifact.captured_at)}",
        f"- {labels.coverage_label}: {coverage}",
        f"- {labels.generator}: {_code(narrative.provider)} / {_code(narrative.model)}",
        "",
        f"## {labels.executive_summary}",
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
                f"- {labels.severity}: **{finding.severity}**",
                f"- {labels.resource}: {_code(finding.resource)}",
                f"- {labels.rule}: {_code(finding.rule_ref)}",
                "",
                f"### {labels.explanation}",
                "",
                _prose(generated.explanation),
                "",
                f"### {labels.remediation_hint}",
                "",
                _prose(finding.remediation_hint),
                "",
                f"### {labels.next_action}",
                "",
                _prose(generated.next_action),
            ]
        )
    lines.extend(
        [
            "",
            f"## {labels.generation_metadata}",
            "",
            f"- {labels.request_id}: {_code(narrative.request_id or labels.unavailable)}",
            "",
        ]
    )
    return "\n".join(lines)


def _prose(value: str) -> str:
    escaped = html.escape(value, quote=True)
    return "".join(f"\\{char}" if char in _MARKDOWN_SPECIALS else char for char in escaped)


def _code(value: str) -> str:
    return f"`{html.escape(value, quote=True).replace('`', '&#96;')}`"
