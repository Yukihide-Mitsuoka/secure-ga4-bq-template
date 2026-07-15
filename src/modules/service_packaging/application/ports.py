from __future__ import annotations

from pathlib import Path
from typing import Protocol

from src.modules.service_packaging.domain.menu import MenuProfile
from src.modules.service_packaging.domain.qualification import (
    EngagementScope,
    QualificationResult,
)


class MenuProfileReader(Protocol):
    def load(self, path: Path) -> MenuProfile: ...


class MenuWriter(Protocol):
    def write(self, profile: MenuProfile, out_dir: Path) -> Path: ...


class EngagementScopeReader(Protocol):
    def load(self, path: Path) -> EngagementScope: ...


class QualificationWriter(Protocol):
    def write(self, result: QualificationResult, out_dir: Path) -> tuple[Path, Path]: ...
