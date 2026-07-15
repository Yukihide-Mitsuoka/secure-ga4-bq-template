"""Immutable service-menu profile vocabulary (ADR-0007)."""

from __future__ import annotations

import re
from dataclasses import dataclass

_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*$")
_CHECK_PATTERN = re.compile(r"^CHK-[0-9]{2}$")
EVALUATOR_CONDITION_IDS = (
    "multiple_projects",
    "dataset_limit_exceeded",
    "table_resource_limit_exceeded",
    "leaf_column_limit_exceeded",
    "customer_wif_setup",
    "query_jobs_required",
    "row_value_inspection_required",
)


@dataclass(frozen=True)
class FeeRange:
    currency: str
    minimum: int
    maximum: int

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Z]{3}", self.currency):
            raise ValueError("fee.currency must be a three-letter uppercase code")
        if self.minimum <= 0 or self.maximum <= 0:
            raise ValueError("fee minimum and maximum must be positive")
        if self.minimum > self.maximum:
            raise ValueError("fee.minimum must not exceed fee.maximum")


@dataclass(frozen=True)
class CapacityLimits:
    projects: int
    datasets: int
    table_resources: int
    leaf_columns: int

    def __post_init__(self) -> None:
        for name, value in vars(self).items():
            if value <= 0:
                raise ValueError(f"limits.{name} must be positive")


@dataclass(frozen=True)
class LabeledItem:
    item_id: str
    label: str

    def __post_init__(self) -> None:
        if not _ID_PATTERN.fullmatch(self.item_id):
            raise ValueError(f"invalid item id: {self.item_id!r}")
        if not self.label.strip():
            raise ValueError(f"label for {self.item_id!r} must be non-empty")


@dataclass(frozen=True)
class MenuProfile:
    version: int
    profile_id: str
    display_name: str
    fee: FeeRange
    limits: CapacityLimits
    checks: tuple[str, ...]
    deliverables: tuple[LabeledItem, ...]
    review_sessions: int
    separate_estimate_conditions: tuple[LabeledItem, ...]

    def __post_init__(self) -> None:
        if self.version != 1:
            raise ValueError(f"unsupported profile version {self.version!r}")
        if not _ID_PATTERN.fullmatch(self.profile_id):
            raise ValueError(f"invalid profile_id: {self.profile_id!r}")
        if not self.display_name.strip():
            raise ValueError("display_name must be non-empty")
        if not self.checks or any(not _CHECK_PATTERN.fullmatch(item) for item in self.checks):
            raise ValueError("checks must contain CHK-NN identifiers")
        _require_unique(self.checks, "checks")
        _require_items(self.deliverables, "deliverables")
        _require_items(self.separate_estimate_conditions, "separate_estimate_conditions")
        _require_evaluator_conditions(self.separate_estimate_conditions)
        if self.review_sessions <= 0:
            raise ValueError("review_sessions must be positive")


def _require_items(items: tuple[LabeledItem, ...], field: str) -> None:
    if not items:
        raise ValueError(f"{field} must be non-empty")
    _require_unique(tuple(item.item_id for item in items), f"{field} ids")


def _require_unique(values: tuple[str, ...], field: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{field} must not contain duplicates")


def _require_evaluator_conditions(items: tuple[LabeledItem, ...]) -> None:
    actual = tuple(item.item_id for item in items)
    missing = tuple(item for item in EVALUATOR_CONDITION_IDS if item not in actual)
    unsupported = tuple(item for item in actual if item not in EVALUATOR_CONDITION_IDS)
    if missing or unsupported:
        raise ValueError(
            "separate_estimate_conditions must contain schema-v1 evaluator ids; "
            f"missing={missing!r}, unsupported={unsupported!r}"
        )
