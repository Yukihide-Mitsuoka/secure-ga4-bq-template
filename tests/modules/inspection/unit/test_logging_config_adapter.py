"""Unit tests for the Logging config adapter (sinks + exclusions)."""

from typing import Any

from src.modules.inspection.infrastructure.gcp.logging_config import LoggingConfigAdapter


class FakeRequest:
    def __init__(self, response: dict[str, Any]) -> None:
        self._response = response

    def execute(self) -> dict[str, Any]:
        return self._response


class FakeListResource:
    def __init__(self, pages: list[dict[str, Any]]) -> None:
        self._pages = pages
        self.last_parent: str | None = None

    def list(self, parent: str, pageToken: str | None = None) -> FakeRequest:  # noqa: N803
        self.last_parent = parent
        return FakeRequest(self._pages[0 if pageToken is None else int(pageToken)])


class FakeLoggingService:
    def __init__(
        self,
        sink_pages: list[dict[str, Any]] | None = None,
        exclusion_pages: list[dict[str, Any]] | None = None,
    ) -> None:
        self.sinks_resource = FakeListResource(sink_pages or [{}])
        self.exclusions_resource = FakeListResource(exclusion_pages or [{}])

    def sinks(self) -> FakeListResource:
        return self.sinks_resource

    def exclusions(self) -> FakeListResource:
        return self.exclusions_resource


def test_sinks_are_translated_and_paginated() -> None:
    service = FakeLoggingService(
        sink_pages=[
            {
                "sinks": [
                    {
                        "name": "audit",
                        "destination": "bigquery.googleapis.com/projects/p/datasets/audit_logs",
                        "filter": 'log_id("cloudaudit.googleapis.com/activity")',
                    }
                ],
                "nextPageToken": "1",
            },
            {
                "sinks": [
                    {"name": "noise", "destination": "storage.googleapis.com/b", "disabled": True}
                ]
            },
        ]
    )
    sinks = LoggingConfigAdapter(service).list_sinks("p")
    assert [(s.name, s.disabled) for s in sinks] == [("audit", False), ("noise", True)]
    assert sinks[0].destination.startswith("bigquery.googleapis.com/")
    assert "cloudaudit" in sinks[0].filter
    assert service.sinks_resource.last_parent == "projects/p"


def test_missing_filter_becomes_empty_string_not_none() -> None:
    service = FakeLoggingService(sink_pages=[{"sinks": [{"name": "s", "destination": "d"}]}])
    assert LoggingConfigAdapter(service).list_sinks("p")[0].filter == ""


def test_exclusions_are_translated() -> None:
    service = FakeLoggingService(
        exclusion_pages=[
            {"exclusions": [{"name": "drop-noise", "filter": "severity<ERROR", "disabled": False}]}
        ]
    )
    exclusions = LoggingConfigAdapter(service).list_exclusions("p")
    assert [(e.name, e.filter, e.disabled) for e in exclusions] == [
        ("drop-noise", "severity<ERROR", False)
    ]


def test_project_without_config_yields_empty_tuples() -> None:
    adapter = LoggingConfigAdapter(FakeLoggingService())
    assert adapter.list_sinks("p") == ()
    assert adapter.list_exclusions("p") == ()
