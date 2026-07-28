from __future__ import annotations

import csv
from pathlib import Path

from src.modules.reporting.infrastructure.json_artifact_reader import JsonArtifactReader

_PACK = Path(__file__).resolve().parents[4] / "examples" / "reporting"
_EXPECTED = (("F001", "CHK-04"), ("F002", "CHK-12"), ("F003", "CHK-13"))


def test_sample_artifact_matches_the_reporting_input_contract() -> None:
    artifact = JsonArtifactReader().read(_PACK / "findings.json")

    assert artifact.project_id == "sample-project"
    assert artifact.coverage.datasets == 1
    assert tuple((finding.ref, finding.check_id) for finding in artifact.findings) == _EXPECTED


def test_sample_outputs_reference_the_same_findings() -> None:
    artifact = JsonArtifactReader().read(_PACK / "findings.json")
    summary = (_PACK / "summary.md").read_text(encoding="utf-8")
    ai_report = (_PACK / "ai-report.md").read_text(encoding="utf-8")
    remediation = (_PACK / "remediation-draft.md").read_text(encoding="utf-8")

    for finding, (ref, check_id) in zip(artifact.findings, _EXPECTED, strict=True):
        assert f"[{finding.severity}] `{finding.resource}`" in summary
        assert f"{ref}: {check_id}" in ai_report
        assert f"{ref}: {check_id}" in remediation
    normalized_ai_report = " ".join(line.lstrip("> ").strip() for line in ai_report.splitlines())
    assert "not an AI-generated result or Acceptance evidence" in normalized_ai_report
    assert "Do not apply directly" in remediation


def test_sample_csv_is_the_finding_only_projection() -> None:
    with (_PACK / "findings.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))

    assert [row["check_id"] for row in rows] == [item[1] for item in _EXPECTED]
    assert all(row["resource"].startswith("projects/sample-project/") for row in rows)
