from __future__ import annotations

import json

import pytest

from src.modules.reporting.application.generate_ai_report import GenerateAiReport
from src.modules.reporting.application.ports import GeneratedOutputError
from src.modules.reporting.domain.model import ProviderText
from src.modules.reporting.infrastructure.json_artifact_reader import JsonArtifactReader
from src.modules.reporting.infrastructure.markdown_report_writer import MarkdownReportWriter
from tests.modules.reporting.unit.builders import write_artifact


class FakeGenerator:
    def __init__(self, response: dict) -> None:
        self.payload = ""
        self.response = response

    def generate(self, payload: str) -> ProviderText:
        self.payload = payload
        return ProviderText(json.dumps(self.response), "fake", "fake-model", "req-1")


def _response(
    ref: str = "F001", explanation: str = "See ![remote](https://example.invalid)."
) -> dict:
    return {
        "executive_summary": "One high-severity access issue requires review.",
        "findings": [{"ref": ref, "explanation": explanation, "next_action": "Narrow the role."}],
    }


def test_generation_pseudonymizes_provider_input_and_renders_local_identifiers(tmp_path) -> None:
    input_path = write_artifact(tmp_path / "findings.json")
    generator = FakeGenerator(_response())
    use_case = GenerateAiReport(
        reader=JsonArtifactReader(), generator=generator, writer=MarkdownReportWriter()
    )

    output = use_case.handle(input_path, tmp_path)

    assert "secret-project" not in generator.payload
    assert "private@example.com" not in generator.payload
    assert "RESOURCE_001" in generator.payload
    report = output.read_text(encoding="utf-8")
    assert "Dataset-scoped access" not in generator.payload
    assert "Replace the broad role" not in generator.payload
    assert "projects/secret-project/datasets/customer_mart" in report
    assert "F001: CHK-03" in report
    assert "![remote](" not in report
    assert "\\!\\[remote\\]\\(https://example\\.invalid\\)" in report


@pytest.mark.parametrize(
    "response",
    [
        _response(ref="F999"),
        _response(explanation="```terraform\nresource x {}\n```"),
    ],
)
def test_generation_rejects_content_outside_deterministic_frame(tmp_path, response) -> None:
    use_case = GenerateAiReport(
        reader=JsonArtifactReader(),
        generator=FakeGenerator(response),
        writer=MarkdownReportWriter(),
    )

    with pytest.raises(GeneratedOutputError):
        use_case.handle(write_artifact(tmp_path / "findings.json"), tmp_path)
    assert not (tmp_path / "ai-report.md").exists()


def test_existing_report_is_not_overwritten(tmp_path) -> None:
    existing = tmp_path / "ai-report.md"
    existing.write_text("keep me", encoding="utf-8")
    use_case = GenerateAiReport(
        reader=JsonArtifactReader(),
        generator=FakeGenerator(_response()),
        writer=MarkdownReportWriter(),
    )

    with pytest.raises(FileExistsError):
        use_case.handle(write_artifact(tmp_path / "findings.json"), tmp_path)
    assert existing.read_text(encoding="utf-8") == "keep me"
