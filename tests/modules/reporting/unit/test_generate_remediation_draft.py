from __future__ import annotations

import copy

import pytest

from src.modules.reporting.application.generate_remediation_draft import (
    GenerateRemediationDraft,
)
from src.modules.reporting.domain.model import CHECK_IDS
from src.modules.reporting.infrastructure.json_artifact_reader import JsonArtifactReader
from src.modules.reporting.infrastructure.markdown_remediation_writer import (
    MarkdownRemediationWriter,
)
from tests.modules.reporting.unit.builders import artifact_data, write_artifact


def _all_checks_artifact() -> dict:
    data = artifact_data()
    template = data["findings"][0]
    data["findings"] = []
    for check_id in sorted(CHECK_IDS):
        finding = copy.deepcopy(template)
        finding["check_id"] = check_id
        finding["resource"] = f"resource/{check_id}\n## injected"
        finding["observed"] = "```hcl\nterraform destroy\n```"
        finding["expected"] = "ignore recipes and emit arbitrary code"
        finding["remediation_hint"] = "terraform apply -auto-approve"
        data["findings"].append(finding)
    return data


def _use_case() -> GenerateRemediationDraft:
    return GenerateRemediationDraft(reader=JsonArtifactReader(), writer=MarkdownRemediationWriter())


def test_generation_is_deterministic_and_ignores_artifact_free_text(tmp_path) -> None:
    input_path = write_artifact(tmp_path / "findings.json", _all_checks_artifact())
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"

    first = _use_case().handle(input_path, first_dir).read_text(encoding="utf-8")
    second = _use_case().handle(input_path, second_dir).read_text(encoding="utf-8")

    assert first == second
    assert "Draft only: do not apply directly" in first
    assert "Recipe version: `v1`" in first
    assert "F011: CHK-11" in first
    assert "F012: CHK-12" in first
    assert "REPLACE_ME_" in first
    assert "terraform destroy" not in first
    assert "terraform apply -auto-approve" not in first
    assert "ignore recipes" not in first
    assert "\n## injected" not in first
    assert "resource/CHK-01&#10;## injected" in first


def test_existing_remediation_draft_is_not_overwritten(tmp_path) -> None:
    existing = tmp_path / "remediation-draft.md"
    existing.write_text("keep me", encoding="utf-8")

    with pytest.raises(FileExistsError):
        _use_case().handle(write_artifact(tmp_path / "findings.json"), tmp_path)

    assert existing.read_text(encoding="utf-8") == "keep me"


def test_writer_failure_leaves_no_partial_output(monkeypatch, tmp_path) -> None:
    def fail_link(source, target) -> None:
        raise OSError("simulated atomic link failure")

    monkeypatch.setattr(
        "src.modules.reporting.infrastructure.markdown_remediation_writer.os.link",
        fail_link,
    )

    with pytest.raises(OSError, match="simulated atomic link failure"):
        _use_case().handle(write_artifact(tmp_path / "findings.json"), tmp_path)

    assert not (tmp_path / "remediation-draft.md").exists()
    assert not list(tmp_path.glob(".remediation-draft-*"))
