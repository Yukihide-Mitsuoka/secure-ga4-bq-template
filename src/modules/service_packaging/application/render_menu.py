from __future__ import annotations

from pathlib import Path

from src.modules.service_packaging.application.ports import MenuProfileReader, MenuWriter


class RenderInspectionMenu:
    def __init__(self, *, reader: MenuProfileReader, writer: MenuWriter) -> None:
        self._reader = reader
        self._writer = writer

    def handle(self, profile_path: Path, out_dir: Path) -> Path:
        profile = self._reader.load(profile_path)
        return self._writer.write(profile, out_dir)
