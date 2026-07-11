"""Report: the engine's complete output — findings plus the §4.2 coverage frame.

Coverage is what turns "we found N issues" into "we inspected everything and
found N issues": every in-scope dataset/table/column is either counted here or
listed in `skipped` with a reason. The report echoes the engagement params so
the A-level AI layer (and any auditor) can see exactly which rules produced
these findings without a side channel.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.modules.inspection.domain.finding import Finding
from src.modules.inspection.domain.params import InspectionParams
from src.modules.inspection.domain.snapshot import ProjectSnapshot, SkippedResource


@dataclass(frozen=True)
class Coverage:
    datasets: int
    tables: int
    columns: int
    skipped: tuple[SkippedResource, ...] = ()

    @staticmethod
    def from_snapshot(snapshot: ProjectSnapshot) -> Coverage:
        tables = [table for dataset in snapshot.datasets for table in dataset.tables]
        return Coverage(
            datasets=len(snapshot.datasets),
            tables=len(tables),
            columns=sum(len(table.schema_fields) for table in tables),
            skipped=snapshot.skipped,
        )


@dataclass(frozen=True)
class Report:
    project_id: str
    captured_at: datetime
    params: InspectionParams
    coverage: Coverage
    findings: tuple[Finding, ...]

    def severity_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for finding in self.findings:
            counts[finding.severity.value] = counts.get(finding.severity.value, 0) + 1
        return counts
