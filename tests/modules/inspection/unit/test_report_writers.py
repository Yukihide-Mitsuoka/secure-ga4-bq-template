"""Unit tests for the JSON/Markdown report writers (byte-determinism, §6)."""

import json
from pathlib import Path

from src.modules.inspection.domain.finding import Finding, Severity
from src.modules.inspection.domain.report import Coverage, Report
from src.modules.inspection.domain.snapshot import SkippedResource
from src.modules.inspection.infrastructure.json_report_writer import JsonReportWriter
from src.modules.inspection.infrastructure.markdown_report_writer import MarkdownReportWriter
from tests.modules.inspection.builders import FIXED_NOW, params


def _report(findings: tuple[Finding, ...] = ()) -> Report:
    return Report(
        project_id="verify-project",
        captured_at=FIXED_NOW,
        params=params(),
        coverage=Coverage(
            datasets=2,
            tables=3,
            columns=9,
            skipped=(SkippedResource("projects/p/datasets/x", "excluded by engagement params"),),
        ),
        findings=findings,
    )


def _finding() -> Finding:
    return Finding(
        check_id="CHK-04",
        severity=Severity.HIGH,
        resource="projects/p/datasets/marts/tables/fct_events/columns/user_id",
        observed="no policy tag attached",
        expected="policy tag level=high",
        rule_ref="FR-4 #4",
        remediation_hint="declare policy_tags in the model config",
    )


def test_json_report_is_byte_identical_across_writes(tmp_path: Path) -> None:
    report = _report((_finding(),))
    first = JsonReportWriter().write(report, tmp_path / "a").read_bytes()
    second = JsonReportWriter().write(report, tmp_path / "b").read_bytes()
    assert first == second


def test_json_report_carries_meta_coverage_and_findings(tmp_path: Path) -> None:
    path = JsonReportWriter().write(_report((_finding(),)), tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["meta"]["project_id"] == "verify-project"
    assert data["meta"]["captured_at"] == FIXED_NOW.isoformat()
    assert data["meta"]["params"]["expected_location"] == "asia-northeast1"
    assert data["coverage"] == {
        "datasets": 2,
        "tables": 3,
        "columns": 9,
        "skipped": [
            {"resource": "projects/p/datasets/x", "reason": "excluded by engagement params"}
        ],
    }
    assert data["findings"][0]["check_id"] == "CHK-04"
    assert data["findings"][0]["severity"] == "HIGH"


def test_markdown_summary_is_deterministic_and_complete(tmp_path: Path) -> None:
    report = _report((_finding(),))
    first = MarkdownReportWriter().write(report, tmp_path / "a").read_text(encoding="utf-8")
    second = MarkdownReportWriter().write(report, tmp_path / "b").read_text(encoding="utf-8")
    assert first == second
    assert "# Inspection summary — verify-project" in first
    assert "| 2 | 3 | 9 | 1 |" in first  # coverage row
    assert "HIGH: 1" in first
    assert "### CHK-04 (FR-4 #4) — 1" in first
    assert "excluded by engagement params" in first  # skipped listed with reason


def test_markdown_clean_report_says_all_checkpoints_passed(tmp_path: Path) -> None:
    text = MarkdownReportWriter().write(_report(), tmp_path).read_text(encoding="utf-8")
    assert "No findings — all eleven checkpoints passed." in text
