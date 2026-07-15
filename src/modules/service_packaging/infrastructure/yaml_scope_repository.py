"""Fail-closed schema-v1 YAML adapter for engagement scope inputs."""

from __future__ import annotations

from pathlib import Path

import yaml

from src.modules.service_packaging.domain.qualification import EngagementScope, ScopeCounts

_ROOT_FIELDS = {"version", "counts", "special_conditions"}
_COUNT_FIELDS = {"projects", "datasets", "table_resources", "leaf_columns"}
_CONDITION_FIELDS = {
    "customer_wif_setup",
    "query_jobs_required",
    "row_value_inspection_required",
}


class YamlEngagementScopeRepository:
    def load(self, path: Path) -> EngagementScope:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"{path}: engagement scope must be a YAML mapping")
        _require_fields(raw, _ROOT_FIELDS, path, "scope")
        counts = _mapping(raw, "counts", path)
        conditions = _mapping(raw, "special_conditions", path)
        _require_fields(counts, _COUNT_FIELDS, path, "counts")
        _require_fields(conditions, _CONDITION_FIELDS, path, "special_conditions")
        try:
            return EngagementScope(
                version=_integer(raw, "version", path),
                counts=ScopeCounts(
                    projects=_integer(counts, "projects", path, "counts"),
                    datasets=_integer(counts, "datasets", path, "counts"),
                    table_resources=_integer(counts, "table_resources", path, "counts"),
                    leaf_columns=_integer(counts, "leaf_columns", path, "counts"),
                ),
                customer_wif_setup=_boolean(conditions, "customer_wif_setup", path),
                query_jobs_required=_boolean(conditions, "query_jobs_required", path),
                row_value_inspection_required=_boolean(
                    conditions, "row_value_inspection_required", path
                ),
            )
        except ValueError as error:
            if str(error).startswith(f"{path}:"):
                raise
            raise ValueError(f"{path}: {error}") from error


def _require_fields(raw: dict[object, object], expected: set[str], path: Path, parent: str) -> None:
    actual = set(raw)
    missing = sorted(expected - actual)
    unsupported = sorted(str(item) for item in actual - expected)
    if missing or unsupported:
        raise ValueError(
            f"{path}: '{parent}' fields invalid; missing={missing!r}, unsupported={unsupported!r}"
        )


def _mapping(raw: dict[object, object], key: str, path: Path) -> dict[object, object]:
    value = raw.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: '{key}' must be a YAML mapping")
    return value


def _integer(raw: dict[object, object], key: str, path: Path, parent: str | None = None) -> int:
    value = raw.get(key)
    where = f"{parent}.{key}" if parent else key
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{path}: '{where}' must be a YAML integer")
    return value


def _boolean(raw: dict[object, object], key: str, path: Path) -> bool:
    value = raw.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{path}: 'special_conditions.{key}' must be a YAML boolean")
    return value
