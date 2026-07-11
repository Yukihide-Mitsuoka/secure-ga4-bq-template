"""Loads an engagement-parameters YAML (design §2.2) into InspectionParams.

The YAML nests scoping under `datasets:` and keeps `audit:`/`thresholds:` as
sub-maps; the domain dataclass flattens `datasets.*` to top-level fields — the
un-nesting happens here, once, at the boundary (COD-011). Absent keys fall
back to the dataclass defaults so the template's recommended values need no
repetition in engagement files (FR-7: override the file, never the code).
"""

from __future__ import annotations

from pathlib import Path

import yaml

from src.modules.inspection.domain.params import AuditParams, InspectionParams, Thresholds

_SUPPORTED_VERSION = 1

# Single source of the dataclass defaults for absent-key fallbacks.
_DEFAULTS = InspectionParams(project_id="_defaults_", expected_location="_defaults_")


class YamlParamsRepository:
    """ParamsRepository port implementation."""

    def load(self, path: str) -> InspectionParams:
        file_path = Path(path)
        raw = yaml.safe_load(file_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"{file_path}: params must be a YAML mapping")
        version = raw.get("version", _SUPPORTED_VERSION)
        if version != _SUPPORTED_VERSION:
            raise ValueError(f"{file_path}: unsupported params version {version!r}")
        for required in ("project_id", "expected_location"):
            if not raw.get(required):
                raise ValueError(f"{file_path}: '{required}' is required")

        datasets = _sub_map(raw, "datasets", file_path)
        audit = _sub_map(raw, "audit", file_path)
        thresholds = _sub_map(raw, "thresholds", file_path)

        return InspectionParams(
            project_id=str(raw["project_id"]),
            expected_location=str(raw["expected_location"]),
            mart_patterns=_patterns(datasets, "mart_patterns", file_path),
            raw_patterns=_patterns(datasets, "raw_patterns", file_path),
            exclude=_patterns(datasets, "exclude", file_path),
            audit=AuditParams(
                high_sensitivity_datasets=_str_tuple(
                    audit.get("high_sensitivity_datasets", []),
                    where=f"{file_path}: audit.high_sensitivity_datasets",
                ),
                retention_max_days=_int(
                    audit,
                    "retention_max_days",
                    _DEFAULTS.audit.retention_max_days,
                    where=f"{file_path}: audit.retention_max_days",
                ),
            ),
            thresholds=Thresholds(
                large_table_bytes=_int(
                    thresholds,
                    "large_table_bytes",
                    _DEFAULTS.thresholds.large_table_bytes,
                    where=f"{file_path}: thresholds.large_table_bytes",
                ),
                long_lived_days=_int(
                    thresholds,
                    "long_lived_days",
                    _DEFAULTS.thresholds.long_lived_days,
                    where=f"{file_path}: thresholds.long_lived_days",
                ),
                require_cmek=_bool(
                    thresholds,
                    "require_cmek",
                    _DEFAULTS.thresholds.require_cmek,
                    where=f"{file_path}: thresholds.require_cmek",
                ),
            ),
            catalog_path=str(raw.get("catalog_path", _DEFAULTS.catalog_path)),
        )


def _sub_map(raw: dict[object, object], key: str, file_path: Path) -> dict[object, object]:
    value = raw.get(key)
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{file_path}: '{key}' must be a YAML mapping")
    return value


def _patterns(datasets: dict[object, object], key: str, file_path: Path) -> tuple[str, ...]:
    if key not in datasets:
        # Field names in InspectionParams match the YAML keys exactly.
        default: tuple[str, ...] = getattr(_DEFAULTS, key)
        return default
    return _str_tuple(datasets[key], where=f"{file_path}: datasets.{key}")


def _str_tuple(value: object, *, where: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{where} must be a YAML list")
    return tuple(str(item) for item in value)


def _int(mapping: dict[object, object], key: str, default: int, *, where: str) -> int:
    value = mapping.get(key)
    if value is None:
        return default
    # bool is an int subclass — reject it explicitly so `true` can't slip in.
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{where} must be a YAML integer")
    return value


def _bool(mapping: dict[object, object], key: str, default: bool, *, where: str) -> bool:
    value = mapping.get(key)
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ValueError(f"{where} must be a YAML boolean")
    return value
