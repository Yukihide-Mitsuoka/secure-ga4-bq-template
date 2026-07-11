"""Engagement parameters (FR-7) — the single per-engagement input of the engine.

Mirrors design §2.2 (inspection-params.yml). The template ships these defaults;
engagements override the file, never the code. Dataset scoping implements the
§4.2 coverage denominator: mart-pattern datasets get full column inspection,
raw-pattern datasets (`analytics_*`) get containment-only IAM checks, excluded
datasets are reported as skipped — nothing silently disappears.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fnmatch import fnmatchcase


class DatasetScope(Enum):
    MART = "mart"  # full inspection incl. column-level checks
    RAW = "raw"  # containment-only: IAM checks, no column checks
    EXCLUDED = "excluded"  # out of scope, listed in the report with a reason
    UNMATCHED = "unmatched"  # matched no pattern; treated as MART (safe default)


@dataclass(frozen=True)
class AuditParams:
    high_sensitivity_datasets: tuple[str, ...] = ()
    retention_max_days: int = 365

    def __post_init__(self) -> None:
        if self.retention_max_days <= 0:
            raise ValueError("retention_max_days must be positive")


@dataclass(frozen=True)
class Thresholds:
    large_table_bytes: int = 10 * 1024**3  # 10 GiB — CHK-08
    long_lived_days: int = 90  # CHK-10
    require_cmek: bool = False  # CHK-11: False -> CMEK absence is INFO

    def __post_init__(self) -> None:
        if self.large_table_bytes <= 0:
            raise ValueError("large_table_bytes must be positive")
        if self.long_lived_days <= 0:
            raise ValueError("long_lived_days must be positive")


@dataclass(frozen=True)
class InspectionParams:
    project_id: str
    expected_location: str
    mart_patterns: tuple[str, ...] = ("mart*", "stg*", "staging", "intermediate", "marts")
    raw_patterns: tuple[str, ...] = ("analytics_*",)
    exclude: tuple[str, ...] = ()
    audit: AuditParams = AuditParams()
    thresholds: Thresholds = Thresholds()
    catalog_path: str = "catalog/ga4-sensitivity.yml"

    def __post_init__(self) -> None:
        if not self.project_id:
            raise ValueError("project_id must be non-empty")
        if not self.expected_location:
            raise ValueError("expected_location must be non-empty")

    def classify(self, dataset_id: str) -> DatasetScope:
        """Precedence: exclude > raw > mart. Unmatched datasets are NOT dropped —
        the caller treats them as MART so an unlisted dataset can only ever widen
        coverage, never silently escape it (§4.2)."""
        if _matches_any(dataset_id, self.exclude):
            return DatasetScope.EXCLUDED
        if _matches_any(dataset_id, self.raw_patterns):
            return DatasetScope.RAW
        if _matches_any(dataset_id, self.mart_patterns):
            return DatasetScope.MART
        return DatasetScope.UNMATCHED


def _matches_any(dataset_id: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatchcase(dataset_id, pattern) for pattern in patterns)
