"""Deterministic engagement qualification rules from ADR-0007."""

from __future__ import annotations

from dataclasses import dataclass

from src.modules.service_packaging.domain.menu import MenuProfile


@dataclass(frozen=True)
class ScopeCounts:
    projects: int
    datasets: int
    table_resources: int
    leaf_columns: int

    def __post_init__(self) -> None:
        for name, value in vars(self).items():
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"counts.{name} must be a positive integer")


@dataclass(frozen=True)
class EngagementScope:
    version: int
    counts: ScopeCounts
    customer_wif_setup: bool
    query_jobs_required: bool
    row_value_inspection_required: bool

    def __post_init__(self) -> None:
        if self.version != 1:
            raise ValueError(f"unsupported engagement scope version {self.version!r}")
        for name in (
            "customer_wif_setup",
            "query_jobs_required",
            "row_value_inspection_required",
        ):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"special_conditions.{name} must be a YAML boolean")


@dataclass(frozen=True)
class QualificationReason:
    condition_id: str
    label: str
    actual: int | bool
    limit: int | None


@dataclass(frozen=True)
class QualificationResult:
    profile_id: str
    profile_version: int
    scope: EngagementScope
    reasons: tuple[QualificationReason, ...]

    @property
    def standard_package_eligible(self) -> bool:
        return not self.reasons


def evaluate_scope(profile: MenuProfile, scope: EngagementScope) -> QualificationResult:
    counts = scope.counts
    limits = profile.limits
    observations: dict[str, tuple[bool, int | bool, int | None]] = {
        "multiple_projects": (counts.projects > limits.projects, counts.projects, limits.projects),
        "dataset_limit_exceeded": (
            counts.datasets > limits.datasets,
            counts.datasets,
            limits.datasets,
        ),
        "table_resource_limit_exceeded": (
            counts.table_resources > limits.table_resources,
            counts.table_resources,
            limits.table_resources,
        ),
        "leaf_column_limit_exceeded": (
            counts.leaf_columns > limits.leaf_columns,
            counts.leaf_columns,
            limits.leaf_columns,
        ),
        "customer_wif_setup": (scope.customer_wif_setup, scope.customer_wif_setup, None),
        "query_jobs_required": (scope.query_jobs_required, scope.query_jobs_required, None),
        "row_value_inspection_required": (
            scope.row_value_inspection_required,
            scope.row_value_inspection_required,
            None,
        ),
    }
    reasons = tuple(
        QualificationReason(
            item.item_id, item.label, observations[item.item_id][1], observations[item.item_id][2]
        )
        for item in profile.separate_estimate_conditions
        if observations[item.item_id][0]
    )
    return QualificationResult(profile.profile_id, profile.version, scope, reasons)
