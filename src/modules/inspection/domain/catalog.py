"""Sensitivity catalog model (FR-1.1/FR-1.2) — CHK-04 data plus CHK-13 origin input.

Mirrors catalog/ga4-sensitivity.yml: shipped defaults (`columns`,
`promoted_columns`) plus per-engagement `overrides`. Resolution order is the
FR-1.2 contract: overrides win over defaults; promoted nested keys are columns
once promoted, so they participate under the same target path.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True)
class PromotionSource:
    """Declared nested source for one promoted mart-column path."""

    field_path: str | None = None
    key: str | None = None


@dataclass(frozen=True)
class PromotedColumn:
    """Sensitivity and optional declared origin of one promoted column."""

    level: str
    source: PromotionSource | None = None


@dataclass(frozen=True)
class SensitivityCatalog:
    levels: tuple[str, ...]
    columns: Mapping[str, str] = field(default_factory=dict)
    promoted_columns: Mapping[str, PromotedColumn] = field(default_factory=dict)
    overrides: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.levels:
            raise ValueError("catalog must declare at least one sensitivity level")
        known = set(self.levels)
        for source_name, mapping in (("columns", self.columns), ("overrides", self.overrides)):
            for column, level in mapping.items():
                if level not in known:
                    raise ValueError(
                        f"catalog {source_name}[{column!r}] -> {level!r} "
                        f"is not one of the declared levels {self.levels}"
                    )
        for column, promoted in self.promoted_columns.items():
            if promoted.level not in known:
                raise ValueError(
                    f"catalog promoted_columns[{column!r}] -> {promoted.level!r} "
                    f"is not one of the declared levels {self.levels}"
                )

    def effective_level(self, column: str) -> str | None:
        """FR-1.2 resolution: overrides > shipped defaults; None = not cataloged."""
        if column in self.overrides:
            return self.overrides[column]
        if column in self.columns:
            return self.columns[column]
        promoted = self.promoted_columns.get(column)
        if promoted is not None:
            return promoted.level
        return None

    def promotion_source(self, column: str) -> PromotionSource | None:
        """Return the declared origin, without inferring transformation correctness."""
        promoted = self.promoted_columns.get(column)
        return promoted.source if promoted is not None else None
