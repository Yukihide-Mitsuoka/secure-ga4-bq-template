"""Real time source implementing the Clock port (application/ports.py)."""

from __future__ import annotations

from datetime import UTC, datetime


class SystemClock:
    """The only place in the module that reads wall time (MODULE.md #3)."""

    def now(self) -> datetime:
        return datetime.now(tz=UTC)
