"""Loads catalog/ga4-sensitivity.yml into the SensitivityCatalog domain model.

Boundary validation happens here (COD-011): the file shape is checked with
path-carrying error messages; level-value validity is the domain model's own
invariant and propagates from SensitivityCatalog.__post_init__.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from src.modules.inspection.domain.catalog import SensitivityCatalog

_SUPPORTED_VERSION = 1


class YamlCatalogRepository:
    """CatalogRepository port implementation; the path is fixed at construction
    because callers get it from the engagement params (`catalog_path`)."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def load(self) -> SensitivityCatalog:
        raw = yaml.safe_load(self._path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"{self._path}: catalog must be a YAML mapping")
        version = raw.get("version", _SUPPORTED_VERSION)
        if version != _SUPPORTED_VERSION:
            raise ValueError(f"{self._path}: unsupported catalog version {version!r}")
        if "levels" not in raw:
            raise ValueError(f"{self._path}: catalog must declare 'levels'")
        return SensitivityCatalog(
            levels=_str_tuple(raw["levels"], where=f"{self._path}: levels"),
            columns=_str_map(raw.get("columns"), where=f"{self._path}: columns"),
            promoted_event_params=_str_map(
                raw.get("promoted_event_params"), where=f"{self._path}: promoted_event_params"
            ),
            overrides=_str_map(raw.get("overrides"), where=f"{self._path}: overrides"),
        )


def _str_tuple(value: object, *, where: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{where} must be a YAML list")
    return tuple(str(item) for item in value)


def _str_map(value: object, *, where: str) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{where} must be a YAML mapping")
    return {str(key): str(val) for key, val in value.items()}
