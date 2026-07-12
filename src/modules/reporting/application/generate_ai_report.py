from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.modules.reporting.application.ports import (
    ArtifactReader,
    GeneratedOutputError,
    ReportWriter,
    TextGenerator,
)
from src.modules.reporting.domain.model import (
    PROMPT_VERSION,
    GeneratedFinding,
    GeneratedNarrative,
    InspectionArtifact,
    ProviderText,
)

_MAX_GENERATED_TEXT = 8_000


class GenerateAiReport:
    def __init__(
        self, *, reader: ArtifactReader, generator: TextGenerator, writer: ReportWriter
    ) -> None:
        self._reader = reader
        self._generator = generator
        self._writer = writer

    def handle(self, input_path: Path, out_dir: Path) -> Path:
        artifact = self._reader.read(input_path)
        response = self._generator.generate(_provider_payload(artifact))
        narrative = _parse_response(response, artifact)
        return self._writer.write(artifact, narrative, out_dir)


def _provider_payload(artifact: InspectionArtifact) -> str:
    payload = {
        "prompt_version": PROMPT_VERSION,
        "project": "PROJECT",
        "coverage": {
            "datasets": artifact.coverage.datasets,
            "tables": artifact.coverage.tables,
            "columns": artifact.coverage.columns,
        },
        "findings": [
            {
                "ref": finding.ref,
                "check_id": finding.check_id,
                "severity": finding.severity,
                "resource": finding.resource_alias,
                "expected": finding.expected,
                "rule_ref": finding.rule_ref,
                "remediation_hint": finding.remediation_hint,
            }
            for finding in artifact.findings
        ],
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _parse_response(response: ProviderText, artifact: InspectionArtifact) -> GeneratedNarrative:
    try:
        raw = json.loads(response.text)
    except (json.JSONDecodeError, TypeError) as error:
        raise GeneratedOutputError("provider returned invalid JSON") from error
    if not isinstance(raw, dict) or set(raw) != {"executive_summary", "findings"}:
        raise GeneratedOutputError("provider response has an invalid top-level schema")

    summary = _generated_text(raw["executive_summary"], "executive_summary")
    items = raw["findings"]
    if not isinstance(items, list):
        raise GeneratedOutputError("provider findings must be an array")

    generated: list[GeneratedFinding] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict) or set(item) != {"ref", "explanation", "next_action"}:
            raise GeneratedOutputError(f"provider finding {index} has an invalid schema")
        generated.append(
            GeneratedFinding(
                ref=_generated_text(item["ref"], f"findings[{index}].ref"),
                explanation=_generated_text(item["explanation"], f"findings[{index}].explanation"),
                next_action=_generated_text(item["next_action"], f"findings[{index}].next_action"),
            )
        )

    expected_refs = [finding.ref for finding in artifact.findings]
    actual_refs = [finding.ref for finding in generated]
    if sorted(actual_refs) != sorted(expected_refs) or len(actual_refs) != len(set(actual_refs)):
        raise GeneratedOutputError("provider response does not match the deterministic finding set")
    by_ref = {finding.ref: finding for finding in generated}
    return GeneratedNarrative(
        executive_summary=summary,
        findings=tuple(by_ref[ref] for ref in expected_refs),
        provider=response.provider,
        model=response.model,
        request_id=response.request_id,
    )


def _generated_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GeneratedOutputError(f"provider field {field} must be non-empty text")
    text = value.strip()
    if len(text) > _MAX_GENERATED_TEXT or "```" in text:
        raise GeneratedOutputError(f"provider field {field} contains disallowed content")
    return text
