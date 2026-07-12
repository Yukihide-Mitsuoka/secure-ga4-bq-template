from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src.modules.reporting.domain.model import (
    CHECK_IDS,
    SEVERITIES,
    CoverageFrame,
    FindingFrame,
    InspectionArtifact,
)

_MAX_FILE_BYTES = 1_048_576
_MAX_TEXT = 8_192
_FINDING_KEYS = {
    "check_id",
    "severity",
    "resource",
    "observed",
    "expected",
    "rule_ref",
    "remediation_hint",
}


class JsonArtifactReader:
    def __init__(self, max_file_bytes: int = _MAX_FILE_BYTES) -> None:
        self._max_file_bytes = max_file_bytes

    def read(self, path: Path) -> InspectionArtifact:
        if path.stat().st_size > self._max_file_bytes:
            raise ValueError("inspection artifact exceeds the size limit")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError("inspection artifact is not valid JSON") from error
        root = _mapping(raw, "root")
        if set(root) - {"schema_version", "meta", "coverage", "findings"}:
            raise ValueError("inspection artifact has unknown top-level fields")
        if root.get("schema_version", 1) != 1:
            raise ValueError("unsupported inspection artifact schema version")

        meta = _mapping(root.get("meta"), "meta")
        project_id = _text(meta.get("project_id"), "meta.project_id")
        captured_at = _text(meta.get("captured_at"), "meta.captured_at")
        try:
            datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError("meta.captured_at must be an ISO-8601 timestamp") from error

        coverage_raw = _mapping(root.get("coverage"), "coverage")
        skipped = coverage_raw.get("skipped")
        if not isinstance(skipped, list):
            raise ValueError("coverage.skipped must be an array")
        if skipped:
            raise ValueError("inspection coverage is incomplete")
        coverage = CoverageFrame(
            datasets=_count(coverage_raw.get("datasets"), "coverage.datasets"),
            tables=_count(coverage_raw.get("tables"), "coverage.tables"),
            columns=_count(coverage_raw.get("columns"), "coverage.columns"),
        )

        raw_findings = root.get("findings")
        if not isinstance(raw_findings, list):
            raise ValueError("findings must be an array")
        findings = tuple(_finding(item, index) for index, item in enumerate(raw_findings))
        return InspectionArtifact(project_id, captured_at, coverage, findings)


def _finding(value: Any, index: int) -> FindingFrame:
    item = _mapping(value, f"findings[{index}]")
    if set(item) != _FINDING_KEYS:
        raise ValueError(f"findings[{index}] has an invalid schema")
    check_id = _text(item["check_id"], f"findings[{index}].check_id")
    severity = _text(item["severity"], f"findings[{index}].severity")
    if check_id not in CHECK_IDS:
        raise ValueError(f"findings[{index}] has an unsupported check_id")
    if severity not in SEVERITIES:
        raise ValueError(f"findings[{index}] has an unsupported severity")
    _text(item["observed"], f"findings[{index}].observed")
    return FindingFrame(
        ref=f"F{index + 1:03d}",
        check_id=check_id,
        severity=severity,
        resource=_text(item["resource"], f"findings[{index}].resource"),
        resource_alias=f"RESOURCE_{index + 1:03d}",
        expected=_text(item["expected"], f"findings[{index}].expected"),
        rule_ref=_text(item["rule_ref"], f"findings[{index}].rule_ref"),
        remediation_hint=_text(item["remediation_hint"], f"findings[{index}].remediation_hint"),
    )


def _mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError(f"{field} must be an object")
    return value


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or len(value) > _MAX_TEXT:
        raise ValueError(f"{field} must be non-empty text within {_MAX_TEXT} characters")
    return value


def _count(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value
