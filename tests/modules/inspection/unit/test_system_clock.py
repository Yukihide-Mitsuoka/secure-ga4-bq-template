"""Unit test for the SystemClock adapter (the module's only wall-time reader)."""

from datetime import UTC

from src.modules.inspection.infrastructure.system_clock import SystemClock


def test_now_returns_timezone_aware_utc() -> None:
    now = SystemClock().now()
    assert now.tzinfo is UTC
