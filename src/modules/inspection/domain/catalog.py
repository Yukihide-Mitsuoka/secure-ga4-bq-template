"""Sensitivity catalog model (FR-1.1/FR-1.2) — the data behind checkpoint CHK-04.

Mirrors catalog/ga4-sensitivity.yml: shipped defaults (`columns`,
`promoted_event_params`) plus per-engagement `overrides`. Resolution order is the
FR-1.2 contract: overrides win over defaults; promoted event_params keys are
columns once promoted, so they participate under the same name.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SensitivityCatalog:
    levels: tuple[str, ...]
    columns: Mapping[str, str] = field(default_factory=dict)
    promoted_event_params: Mapping[str, str] = field(default_factory=dict)
    overrides: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.levels:
            raise ValueError("catalog must declare at least one sensitivity level")
        known = set(self.levels)
        for source_name, mapping in (
            ("columns", self.columns),
            ("promoted_event_params", self.promoted_event_params),
            ("overrides", self.overrides),
        ):
            for column, level in mapping.items():
                if level not in known:
                    raise ValueError(
                        f"catalog {source_name}[{column!r}] -> {level!r} "
                        f"is not one of the declared levels {self.levels}"
                    )

    def effective_level(self, column: str) -> str | None:
        """FR-1.2 resolution: overrides > shipped defaults; None = not cataloged."""
        if column in self.overrides:
            return self.overrides[column]
        if column in self.columns:
            return self.columns[column]
        if column in self.promoted_event_params:
            return self.promoted_event_params[column]
        return None
