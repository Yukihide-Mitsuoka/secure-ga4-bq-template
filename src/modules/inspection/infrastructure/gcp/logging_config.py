"""LoggingConfigPort implementation over logging v2.

Read-only: sinks.list + exclusions.list (CHK-06/07's input). These are exactly
the reads the bq-inspector-role grants (logging.sinks.get/list,
logging.exclusions.list) — nothing here needs more.
"""

from __future__ import annotations

from typing import Any

from src.modules.inspection.domain.snapshot import LogExclusion, LogSink
from src.modules.inspection.infrastructure.gcp.pagination import paginate


class LoggingConfigAdapter:
    def __init__(self, logging_service: Any) -> None:
        self._service = logging_service

    def list_sinks(self, project_id: str) -> tuple[LogSink, ...]:
        parent = f"projects/{project_id}"
        sinks: list[LogSink] = []
        for page in paginate(
            lambda token: self._service.sinks().list(parent=parent, pageToken=token)
        ):
            for entry in page.get("sinks") or []:
                sinks.append(
                    LogSink(
                        name=str(entry.get("name", "")),
                        destination=str(entry.get("destination", "")),
                        filter=str(entry.get("filter") or ""),
                        disabled=bool(entry.get("disabled", False)),
                    )
                )
        return tuple(sinks)

    def list_exclusions(self, project_id: str) -> tuple[LogExclusion, ...]:
        parent = f"projects/{project_id}"
        exclusions: list[LogExclusion] = []
        for page in paginate(
            lambda token: self._service.exclusions().list(parent=parent, pageToken=token)
        ):
            for entry in page.get("exclusions") or []:
                exclusions.append(
                    LogExclusion(
                        name=str(entry.get("name", "")),
                        filter=str(entry.get("filter") or ""),
                        disabled=bool(entry.get("disabled", False)),
                    )
                )
        return tuple(exclusions)
