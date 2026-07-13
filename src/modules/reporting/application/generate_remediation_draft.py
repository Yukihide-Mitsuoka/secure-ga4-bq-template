from __future__ import annotations

from pathlib import Path

from src.modules.reporting.application.ports import ArtifactReader, RemediationWriter


class GenerateRemediationDraft:
    def __init__(self, *, reader: ArtifactReader, writer: RemediationWriter) -> None:
        self._reader = reader
        self._writer = writer

    def handle(self, input_path: Path, out_dir: Path) -> Path:
        artifact = self._reader.read(input_path)
        return self._writer.write(artifact, out_dir)
