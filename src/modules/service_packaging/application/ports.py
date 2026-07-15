from __future__ import annotations

from pathlib import Path
from typing import Protocol

from src.modules.service_packaging.domain.menu import MenuProfile


class MenuProfileReader(Protocol):
    def load(self, path: Path) -> MenuProfile: ...


class MenuWriter(Protocol):
    def write(self, profile: MenuProfile, out_dir: Path) -> Path: ...
