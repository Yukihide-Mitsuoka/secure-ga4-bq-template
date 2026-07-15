from __future__ import annotations

import pytest

from src.modules.reporting.infrastructure.json_artifact_reader import JsonArtifactReader
from tests.modules.reporting.unit.builders import artifact_data, write_artifact


def test_valid_artifact_is_parsed_with_deterministic_aliases(tmp_path) -> None:
    artifact = JsonArtifactReader().read(write_artifact(tmp_path / "findings.json"))

    assert artifact.project_id == "secret-project"
    assert artifact.findings[0].ref == "F001"
    assert artifact.findings[0].resource_alias == "RESOURCE_001"


def test_chk12_artifact_is_supported(tmp_path) -> None:
    data = artifact_data()
    data["findings"][0]["check_id"] = "CHK-12"
    data["findings"][0]["severity"] = "LOW"
    data["findings"][0]["rule_ref"] = "FR-9"

    artifact = JsonArtifactReader().read(write_artifact(tmp_path / "findings.json", data))

    assert artifact.findings[0].check_id == "CHK-12"


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda data: data["coverage"]["skipped"].append({"resource": "x"}), "incomplete"),
        (lambda data: data["findings"][0].update(check_id="CHK-99"), "check_id"),
        (lambda data: data.update(schema_version=2), "schema version"),
    ],
)
def test_unsafe_or_unsupported_artifact_is_rejected(tmp_path, mutate, message) -> None:
    data = artifact_data()
    mutate(data)

    with pytest.raises(ValueError, match=message):
        JsonArtifactReader().read(write_artifact(tmp_path / "findings.json", data))


def test_oversized_artifact_is_rejected_before_parsing(tmp_path) -> None:
    path = tmp_path / "findings.json"
    path.write_text("12345", encoding="utf-8")

    with pytest.raises(ValueError, match="size limit"):
        JsonArtifactReader(max_file_bytes=4).read(path)
