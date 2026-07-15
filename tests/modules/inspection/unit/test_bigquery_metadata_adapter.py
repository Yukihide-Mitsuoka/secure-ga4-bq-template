"""Unit tests for the BigQuery metadata adapter's JSON→domain translation.

The discovery service is replaced by in-memory fakes mimicking the fluent
`.datasets().list(...).execute()` shape — no network, no GCP (TST-020: mock at
the port boundary; the translation logic IS the adapter's behavior under test).
"""

from datetime import UTC, datetime
from typing import Any

import pytest

from src.modules.inspection.infrastructure.gcp.bigquery_metadata import BigQueryMetadataAdapter

# --- discovery-client fakes -------------------------------------------------


class FakeRequest:
    def __init__(self, response: dict[str, Any]) -> None:
        self._response = response

    def execute(self) -> dict[str, Any]:
        return self._response


class FakeDatasetsResource:
    def __init__(self, pages: list[dict[str, Any]], by_id: dict[str, dict[str, Any]]) -> None:
        self._pages = pages
        self._by_id = by_id

    def list(self, projectId: str, pageToken: str | None = None) -> FakeRequest:  # noqa: N803
        return FakeRequest(self._pages[0 if pageToken is None else int(pageToken)])

    def get(self, projectId: str, datasetId: str) -> FakeRequest:  # noqa: N803
        return FakeRequest(self._by_id[datasetId])


class FakeTablesResource:
    def __init__(self, pages: list[dict[str, Any]], by_id: dict[str, dict[str, Any]]) -> None:
        self._pages = pages
        self._by_id = by_id

    def list(
        self,
        projectId: str,  # noqa: N803
        datasetId: str,  # noqa: N803
        pageToken: str | None = None,  # noqa: N803
    ) -> FakeRequest:
        return FakeRequest(self._pages[0 if pageToken is None else int(pageToken)])

    def get(self, projectId: str, datasetId: str, tableId: str) -> FakeRequest:  # noqa: N803
        return FakeRequest(self._by_id[tableId])


class FakeBigQueryService:
    def __init__(
        self,
        dataset_pages: list[dict[str, Any]] | None = None,
        datasets_by_id: dict[str, dict[str, Any]] | None = None,
        table_pages: list[dict[str, Any]] | None = None,
        tables_by_id: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self._datasets = FakeDatasetsResource(dataset_pages or [{}], datasets_by_id or {})
        self._tables = FakeTablesResource(table_pages or [{}], tables_by_id or {})

    def datasets(self) -> FakeDatasetsResource:
        return self._datasets

    def tables(self) -> FakeTablesResource:
        return self._tables


def _dataset_ref(dataset_id: str) -> dict[str, Any]:
    return {"datasetReference": {"datasetId": dataset_id}}


def _table_ref(table_id: str) -> dict[str, Any]:
    return {"tableReference": {"tableId": table_id}}


# --- datasets ---------------------------------------------------------------


def test_list_datasets_drains_all_pages() -> None:
    service = FakeBigQueryService(
        dataset_pages=[
            {"datasets": [_dataset_ref("marts")], "nextPageToken": "1"},
            {"datasets": [_dataset_ref("staging")]},
        ]
    )
    adapter = BigQueryMetadataAdapter(service)
    assert adapter.list_datasets("p") == ("marts", "staging")


def test_list_datasets_handles_empty_project() -> None:
    assert BigQueryMetadataAdapter(FakeBigQueryService()).list_datasets("p") == ()


def test_get_dataset_maps_every_field() -> None:
    service = FakeBigQueryService(
        datasets_by_id={
            "marts": {
                "location": "asia-northeast1",
                "defaultTableExpirationMs": "3600000",
                "defaultPartitionExpirationMs": "7200000",
                "defaultEncryptionConfiguration": {"kmsKeyName": "projects/p/keys/k"},
                "labels": {"layer": "marts", "env": "dev"},
                "access": [
                    {"role": "READER", "specialGroup": "allAuthenticatedUsers"},
                    {"role": "WRITER", "userByEmail": "svc@p.iam.gserviceaccount.com"},
                    {"role": "roles/bigquery.dataViewer", "iamMember": "allUsers"},
                    {"view": {"tableId": "authorized_view"}},  # role-less: not a grant
                ],
            }
        }
    )
    dataset = BigQueryMetadataAdapter(service).get_dataset("p", "marts")
    assert dataset.location == "asia-northeast1"
    assert dataset.default_table_expiration_ms == 3600000
    assert dataset.default_partition_expiration_ms == 7200000
    assert dataset.cmek_key == "projects/p/keys/k"
    assert dataset.labels == (("env", "dev"), ("layer", "marts"))  # sorted, deterministic
    assert [(a.role, a.member) for a in dataset.access] == [
        ("READER", "specialGroup:allAuthenticatedUsers"),
        ("WRITER", "userByEmail:svc@p.iam.gserviceaccount.com"),
        ("roles/bigquery.dataViewer", "allUsers"),
    ]
    assert dataset.tables == ()  # tree assembly is the use case's job


def test_get_dataset_minimal_response_defaults_optionals() -> None:
    service = FakeBigQueryService(datasets_by_id={"d": {"location": "asia-northeast1"}})
    dataset = BigQueryMetadataAdapter(service).get_dataset("p", "d")
    assert dataset.default_table_expiration_ms is None
    assert dataset.cmek_key is None
    assert dataset.access == ()
    assert dataset.labels == ()


# --- tables -----------------------------------------------------------------


def test_list_tables_drains_all_pages_and_handles_empty() -> None:
    service = FakeBigQueryService(
        table_pages=[
            {"tables": [_table_ref("fct_events")], "nextPageToken": "1"},
            {"tables": [_table_ref("dim_users")]},
        ]
    )
    assert BigQueryMetadataAdapter(service).list_tables("p", "d") == ("fct_events", "dim_users")
    assert BigQueryMetadataAdapter(FakeBigQueryService()).list_tables("p", "d") == ()


def test_get_table_maps_governance_fields() -> None:
    tag = "projects/p/locations/asia-northeast1/taxonomies/1/policyTags/9"
    service = FakeBigQueryService(
        tables_by_id={
            "fct_events": {
                "type": "TABLE",
                "description": " Fact events ",
                "numBytes": "1024",
                "creationTime": "1752192000000",
                "expirationTime": "1783728000000",
                "timePartitioning": {"field": "event_date", "requirePartitionFilter": True},
                "clustering": {"fields": ["event_name"]},
                "schema": {
                    "fields": [
                        {"name": "event_date", "type": "DATE", "description": " Event date "},
                        {
                            "name": "user_id",
                            "type": "STRING",
                            "policyTags": {"names": [tag]},
                        },
                        {
                            "name": "geo",
                            "type": "RECORD",
                            "description": "Location record",
                            "fields": [{"name": "city", "type": "STRING", "description": "   "}],
                        },
                    ]
                },
            }
        }
    )
    table = BigQueryMetadataAdapter(service).get_table("p", "d", "fct_events")
    assert table.table_type == "TABLE"
    assert table.description == " Fact events "
    assert table.num_bytes == 1024
    assert table.creation_time == datetime.fromtimestamp(1752192000, tz=UTC)
    assert table.expiration_time == datetime.fromtimestamp(1783728000, tz=UTC)
    assert table.time_partitioning_field == "event_date"
    assert table.require_partition_filter is True  # legacy nested flag honored
    assert table.clustering_fields == ("event_name",)
    assert [
        (f.path, f.field_type, f.policy_tag_ids, f.description) for f in table.schema_fields
    ] == [
        ("event_date", "DATE", (), " Event date "),
        ("user_id", "STRING", (tag,), None),
        ("geo.city", "STRING", (), "   "),  # parent omitted; leaf text preserved exactly
    ]


def test_get_table_ingestion_time_partitioning_counts_as_partitioned() -> None:
    service = FakeBigQueryService(
        tables_by_id={"t": {"creationTime": "1752192000000", "timePartitioning": {"type": "DAY"}}}
    )
    table = BigQueryMetadataAdapter(service).get_table("p", "d", "t")
    assert table.time_partitioning_field == "_PARTITIONTIME"
    assert table.is_partitioned


def test_get_table_top_level_partition_filter_flag_is_honored() -> None:
    service = FakeBigQueryService(
        tables_by_id={
            "t": {
                "creationTime": "1752192000000",
                "rangePartitioning": {"field": "customer_id"},
                "requirePartitionFilter": True,
            }
        }
    )
    table = BigQueryMetadataAdapter(service).get_table("p", "d", "t")
    assert table.range_partitioning_field == "customer_id"
    assert table.require_partition_filter is True


def test_get_table_missing_creation_time_fails_with_context() -> None:
    service = FakeBigQueryService(tables_by_id={"t": {"type": "TABLE"}})
    with pytest.raises(ValueError, match="p.d.t: creationTime missing"):
        BigQueryMetadataAdapter(service).get_table("p", "d", "t")
