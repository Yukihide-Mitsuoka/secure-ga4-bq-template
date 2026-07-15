"""Fail-closed schema-v1 YAML adapter for service-menu product data."""

from __future__ import annotations

from pathlib import Path

import yaml

from src.modules.service_packaging.domain.menu import (
    CapacityLimits,
    FeeRange,
    LabeledItem,
    MenuProfile,
)


class YamlMenuProfileRepository:
    def load(self, path: Path) -> MenuProfile:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"{path}: profile must be a YAML mapping")
        fee = _mapping(raw, "fee", path)
        limits = _mapping(raw, "limits", path)
        try:
            return MenuProfile(
                version=_integer(raw, "version", path),
                profile_id=_string(raw, "profile_id", path),
                display_name=_string(raw, "display_name", path),
                fee=FeeRange(
                    currency=_string(fee, "currency", path, "fee"),
                    minimum=_integer(fee, "minimum", path, "fee"),
                    maximum=_integer(fee, "maximum", path, "fee"),
                ),
                limits=CapacityLimits(
                    projects=_integer(limits, "projects", path, "limits"),
                    datasets=_integer(limits, "datasets", path, "limits"),
                    table_resources=_integer(limits, "table_resources", path, "limits"),
                    leaf_columns=_integer(limits, "leaf_columns", path, "limits"),
                ),
                checks=_strings(raw, "checks", path),
                deliverables=_items(raw, "deliverables", path),
                review_sessions=_integer(raw, "review_sessions", path),
                separate_estimate_conditions=_items(raw, "separate_estimate_conditions", path),
            )
        except ValueError as error:
            if str(error).startswith(f"{path}:"):
                raise
            raise ValueError(f"{path}: {error}") from error


def _mapping(raw: dict[object, object], key: str, path: Path) -> dict[object, object]:
    value = raw.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: '{key}' must be a YAML mapping")
    return value


def _string(raw: dict[object, object], key: str, path: Path, parent: str | None = None) -> str:
    value = raw.get(key)
    where = f"{parent}.{key}" if parent else key
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path}: '{where}' must be a non-empty YAML string")
    return value


def _integer(raw: dict[object, object], key: str, path: Path, parent: str | None = None) -> int:
    value = raw.get(key)
    where = f"{parent}.{key}" if parent else key
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{path}: '{where}' must be a YAML integer")
    return value


def _strings(raw: dict[object, object], key: str, path: Path) -> tuple[str, ...]:
    value = raw.get(key)
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"{path}: '{key}' must be a YAML string list")
    return tuple(value)


def _items(raw: dict[object, object], key: str, path: Path) -> tuple[LabeledItem, ...]:
    value = raw.get(key)
    if not isinstance(value, list):
        raise ValueError(f"{path}: '{key}' must be a YAML list")
    items: list[LabeledItem] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"{path}: '{key}[{index}]' must be a YAML mapping")
        items.append(
            LabeledItem(
                item_id=_string(item, "id", path, f"{key}[{index}]"),
                label=_string(item, "label", path, f"{key}[{index}]"),
            )
        )
    return tuple(items)
