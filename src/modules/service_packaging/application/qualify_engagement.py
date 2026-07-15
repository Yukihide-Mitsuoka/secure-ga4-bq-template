from __future__ import annotations

from pathlib import Path

from src.modules.service_packaging.application.ports import (
    EngagementScopeReader,
    MenuProfileReader,
    QualificationWriter,
)
from src.modules.service_packaging.domain.qualification import evaluate_scope


class QualifyEngagement:
    def __init__(
        self,
        *,
        profile_reader: MenuProfileReader,
        scope_reader: EngagementScopeReader,
        writer: QualificationWriter,
    ) -> None:
        self._profile_reader = profile_reader
        self._scope_reader = scope_reader
        self._writer = writer

    def handle(self, profile_path: Path, scope_path: Path, out_dir: Path) -> tuple[Path, Path]:
        profile = self._profile_reader.load(profile_path)
        scope = self._scope_reader.load(scope_path)
        return self._writer.write(evaluate_scope(profile, scope), out_dir)
