"""Shared pagination draining for discovery-client list calls.

Adapters must always return complete results — a silently truncated page would
fake the §4.2 coverage denominator. `request_for_token` builds the request for
a given pageToken (None = first page); iteration ends when no nextPageToken
comes back.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any


def paginate(request_for_token: Callable[[str | None], Any]) -> Iterator[dict[str, Any]]:
    token: str | None = None
    while True:
        page = request_for_token(token).execute()
        yield page
        token = page.get("nextPageToken")
        if not token:
            return
