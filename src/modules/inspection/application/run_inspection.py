"""Use case: snapshot → 11 deterministic checkpoints → Report.

The module's public entry point (MODULE.md). Determinism invariant: identical
snapshot + params + catalog ⇒ identical Report — findings always leave here in
`sorted_findings` order, so downstream writers can be byte-stable.
"""

from __future__ import annotations

from src.modules.inspection.application.collect_snapshot import CollectSnapshot
from src.modules.inspection.application.ports import CatalogRepository
from src.modules.inspection.domain.checks import ALL_CHECKS, Check
from src.modules.inspection.domain.finding import sorted_findings
from src.modules.inspection.domain.params import InspectionParams
from src.modules.inspection.domain.report import Coverage, Report


class RunInspection:
    def __init__(
        self,
        collector: CollectSnapshot,
        catalog_repository: CatalogRepository,
        checks: tuple[Check, ...] = ALL_CHECKS,
    ) -> None:
        self._collector = collector
        self._catalog_repository = catalog_repository
        self._checks = checks

    def handle(self, params: InspectionParams) -> Report:
        snapshot = self._collector.collect(params)
        catalog = self._catalog_repository.load()
        findings = sorted_findings(
            [finding for check in self._checks for finding in check(snapshot, params, catalog)]
        )
        return Report(
            project_id=snapshot.project_id,
            captured_at=snapshot.captured_at,
            params=params,
            coverage=Coverage.from_snapshot(snapshot),
            findings=tuple(findings),
        )
