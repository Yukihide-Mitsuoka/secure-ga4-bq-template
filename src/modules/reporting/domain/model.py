from __future__ import annotations

from dataclasses import dataclass

CHECK_IDS = frozenset(f"CHK-{number:02d}" for number in range(1, 13))
SEVERITIES = frozenset({"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"})
PROMPT_VERSION = "v1"


@dataclass(frozen=True)
class CoverageFrame:
    datasets: int
    tables: int
    columns: int


@dataclass(frozen=True)
class FindingFrame:
    ref: str
    check_id: str
    severity: str
    resource: str
    resource_alias: str
    expected: str
    rule_ref: str
    remediation_hint: str


@dataclass(frozen=True)
class InspectionArtifact:
    project_id: str
    captured_at: str
    coverage: CoverageFrame
    findings: tuple[FindingFrame, ...]


@dataclass(frozen=True)
class GeneratedFinding:
    ref: str
    explanation: str
    next_action: str


@dataclass(frozen=True)
class ProviderText:
    text: str
    provider: str
    model: str
    request_id: str | None = None


@dataclass(frozen=True)
class GeneratedNarrative:
    executive_summary: str
    findings: tuple[GeneratedFinding, ...]
    provider: str
    model: str
    request_id: str | None = None
