from __future__ import annotations

import json

from src.modules.reporting.domain.model import ProviderText
from src.modules.reporting.interface.cli import main
from tests.modules.reporting.unit.builders import write_artifact


class FakeGenerator:
    def generate(self, payload: str) -> ProviderText:
        response = {
            "executive_summary": "Review one access finding.",
            "findings": [
                {"ref": "F001", "explanation": "Access is broad.", "next_action": "Narrow it."}
            ],
        }
        return ProviderText(json.dumps(response), "fake", "model")


def test_cli_generates_report_with_standard_environment(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "global")
    input_path = write_artifact(tmp_path / "findings.json")

    exit_code = main(
        ["--input", str(input_path)],
        generator_factory=lambda project, location, model: FakeGenerator(),
    )

    assert exit_code == 0
    assert (tmp_path / "ai-report.md").is_file()


def test_cli_rejects_missing_vertex_configuration(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_LOCATION", raising=False)

    assert main(["--input", str(tmp_path / "missing.json")]) == 2
