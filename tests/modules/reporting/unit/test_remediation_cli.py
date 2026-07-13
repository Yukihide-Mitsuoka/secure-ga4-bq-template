from __future__ import annotations

from src.modules.reporting.interface.remediation_cli import main
from tests.modules.reporting.unit.builders import write_artifact


def test_cli_generates_draft_without_vertex_configuration(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_LOCATION", raising=False)
    input_path = write_artifact(tmp_path / "findings.json")

    assert main(["--input", str(input_path)]) == 0
    assert (tmp_path / "remediation-draft.md").is_file()


def test_cli_rejects_missing_input(tmp_path) -> None:
    assert main(["--input", str(tmp_path / "missing.json")]) == 2
