from __future__ import annotations

from pathlib import Path
from typing import Protocol

from src.modules.reporting.domain.model import (
    GeneratedNarrative,
    InspectionArtifact,
    ProviderText,
)


class ProviderError(RuntimeError):
    pass


class GeneratedOutputError(RuntimeError):
    pass


class ArtifactReader(Protocol):
    def read(self, path: Path) -> InspectionArtifact: ...


class TextGenerator(Protocol):
    def generate(self, payload: str) -> ProviderText: ...


class ReportWriter(Protocol):
    def write(
        self, artifact: InspectionArtifact, narrative: GeneratedNarrative, out_dir: Path
    ) -> Path: ...
