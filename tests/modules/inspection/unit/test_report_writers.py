"""Unit tests for the JSON/CSV/Markdown report writers (byte-determinism, §6)."""

import csv
import json
from pathlib import Path

from src.modules.inspection.domain.finding import Finding, Severity
from src.modules.inspection.domain.report import Coverage, Report
from src.modules.inspection.domain.snapshot import SkippedResource
from src.modules.inspection.infrastructure.csv_report_writer import CsvReportWriter
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


def _finding_with_csv_metacharacters() -> Finding:
    return Finding(
        check_id="CHK-12",
        severity=Severity.LOW,
        resource="projects/p/datasets/marts/tables/report,ja/columns/売上",
        observed='description is "missing"\nfor the leaf column',
        expected="non-empty description",
        rule_ref="FR-9.1",
        remediation_hint="add a BigQuery description",
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


def test_csv_report_is_deterministic_and_preserves_escaped_values(tmp_path: Path) -> None:
    report = _report((_finding(), _finding_with_csv_metacharacters()))
    first = CsvReportWriter().write(report, tmp_path / "a").read_bytes()
    second = CsvReportWriter().write(report, tmp_path / "b").read_bytes()

    assert first == second
    assert b"\r\n" not in first
    with (tmp_path / "a" / "findings.csv").open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        assert reader.fieldnames == [
            "check_id",
            "severity",
            "resource",
            "observed",
            "expected",
            "rule_ref",
            "remediation_hint",
        ]
        rows = list(reader)
    assert [row["check_id"] for row in rows] == ["CHK-04", "CHK-12"]
    assert rows[1]["resource"].endswith("report,ja/columns/売上")
    assert rows[1]["observed"] == 'description is "missing"\nfor the leaf column'


def test_csv_clean_report_contains_only_the_header(tmp_path: Path) -> None:
    data = CsvReportWriter().write(_report(), tmp_path).read_text(encoding="utf-8")
    assert data == ("check_id,severity,resource,observed,expected,rule_ref,remediation_hint\n")


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


def test_markdown_clean_report_does_not_overstate_skipped_coverage(tmp_path: Path) -> None:
    text = MarkdownReportWriter().write(_report(), tmp_path).read_text(encoding="utf-8")
    assert "No findings detected in the evaluated scope." in text
    assert "all eleven checkpoints passed" not in text
