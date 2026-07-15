"""Findings: the inspection engine's output vocabulary.

Everything downstream — the JSON report, the Markdown summary, and later the
A-level AI report generator — consumes only this shape. Determinism invariant
(MODULE.md #3): findings are always emitted in `sorted_findings` order so an
identical environment produces a byte-identical report.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

# CHK-01..CHK-11 map to FR-4; additive CHK-12 maps to FR-9.
_CHECK_ID_PATTERN = re.compile(r"^CHK-(0[1-9]|1[0-2])$")


class Severity(Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass(frozen=True)
class Finding:
    """One detected deviation, anchored to a checkpoint and a concrete resource.

    `observed` states the fact, `expected` states the rule — keeping them apart
    is what lets the AI layer write prose without inventing judgements.
    """

    check_id: str
    severity: Severity
    resource: str
    observed: str
    expected: str
    rule_ref: str
    remediation_hint: str

    def __post_init__(self) -> None:
        # Domain invariant, not input validation: a Finding with a bad check id
        # or no resource is a programming error in a check function (COD-011).
        if not _CHECK_ID_PATTERN.match(self.check_id):
            raise ValueError(f"check_id must be CHK-01..CHK-12, got {self.check_id!r}")
        if not self.resource:
            raise ValueError("resource must be a non-empty canonical path")

    def sort_key(self) -> tuple[str, str]:
        return (self.check_id, self.resource)


def sorted_findings(findings: list[Finding]) -> list[Finding]:
    """Deterministic report order (MODULE.md invariant #3)."""
    return sorted(findings, key=Finding.sort_key)
