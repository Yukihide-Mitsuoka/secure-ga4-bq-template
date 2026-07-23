"""Loads catalog/ga4-sensitivity.yml into the SensitivityCatalog domain model.

Boundary validation happens here (COD-011): the file shape is checked with
path-carrying error messages; level-value validity is the domain model's own
invariant and propagates from SensitivityCatalog.__post_init__.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from src.modules.inspection.domain.catalog import (
    PromotedColumn,
    PromotionSource,
    SensitivityCatalog,
)

_SUPPORTED_VERSIONS = (1, 2)


class YamlCatalogRepository:
    """CatalogRepository port implementation; the path is fixed at construction
    because callers get it from the engagement params (`catalog_path`)."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def load(self) -> SensitivityCatalog:
        raw = yaml.safe_load(self._path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"{self._path}: catalog must be a YAML mapping")
        raw_version = raw.get("version", 1)
        if type(raw_version) is not int or raw_version not in _SUPPORTED_VERSIONS:
            raise ValueError(f"{self._path}: unsupported catalog version {raw_version!r}")
        version = raw_version
        if "levels" not in raw:
            raise ValueError(f"{self._path}: catalog must declare 'levels'")
        promoted_columns = self._load_promoted_columns(raw, version)
        return SensitivityCatalog(
            levels=_str_tuple(raw["levels"], where=f"{self._path}: levels"),
            columns=_str_map(raw.get("columns"), where=f"{self._path}: columns"),
            promoted_columns=promoted_columns,
            overrides=_str_map(raw.get("overrides"), where=f"{self._path}: overrides"),
        )

    def _load_promoted_columns(
        self,
        raw: dict[object, object],
        version: int,
    ) -> dict[str, PromotedColumn]:
        if version == 1:
            if "promoted_columns" in raw:
                raise ValueError(f"{self._path}: promoted_columns requires catalog version 2")
            legacy = _str_map(
                raw.get("promoted_event_params"),
                where=f"{self._path}: promoted_event_params",
            )
            return {
                target: PromotedColumn(
                    level=level,
                    source=PromotionSource(field_path="event_params", key=target),
                )
                for target, level in legacy.items()
            }

        if "promoted_event_params" in raw:
            raise ValueError(f"{self._path}: promoted_event_params belongs to catalog version 1")
        return _promoted_column_map(
            raw.get("promoted_columns"),
            where=f"{self._path}: promoted_columns",
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


def _promoted_column_map(
    value: object,
    *,
    where: str,
) -> dict[str, PromotedColumn]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{where} must be a YAML mapping")

    promoted: dict[str, PromotedColumn] = {}
    for raw_target, raw_spec in value.items():
        target = str(raw_target)
        item_where = f"{where}[{target!r}]"
        if not isinstance(raw_spec, dict):
            raise ValueError(f"{item_where} must be a YAML mapping")
        level = _required_string(raw_spec.get("level"), where=f"{item_where}.level")
        source = _promotion_source(raw_spec.get("source"), where=f"{item_where}.source")
        promoted[target] = PromotedColumn(level=level, source=source)
    return promoted


def _promotion_source(value: object, *, where: str) -> PromotionSource | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError(f"{where} must be a YAML mapping")
    return PromotionSource(
        field_path=_optional_string(value.get("field_path"), where=f"{where}.field_path"),
        key=_optional_string(value.get("key"), where=f"{where}.key"),
    )


def _required_string(value: object, *, where: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{where} must be a string")
    return value


def _optional_string(value: object, *, where: str) -> str | None:
    if value is None:
        return None
    return _required_string(value, where=where)
