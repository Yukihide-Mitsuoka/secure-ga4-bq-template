"""BigQueryMetadataPort implementation over the bigquery v2 discovery service.

Read-only by construction: the only methods ever invoked are datasets.list,
datasets.get, tables.list, tables.get — REST metadata, never jobs.* (ADR-0003,
MODULE.md invariants #1-#2). Raw API JSON is translated here into the typed
domain records; nothing outside infrastructure/gcp touches the untyped client.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from src.modules.inspection.domain.snapshot import (
    AccessEntry,
    DatasetMeta,
    SchemaField,
    TableMeta,
)

# Dataset access entries name their grantee under one of these keys; the member
# is normalized to "<kind>:<value>" so checks can match deterministically
# (specialGroup:allAuthenticatedUsers is CHK-02's public-member spelling).
# iamMember values arrive already prefixed (or bare, e.g. "allUsers").
_ACCESS_MEMBER_KEYS = ("userByEmail", "groupByEmail", "domain", "specialGroup")

# Ingestion-time partitioned tables carry timePartitioning without a field;
# they partition on the _PARTITIONTIME pseudo-column. Mapping to that name
# keeps TableMeta.is_partitioned truthful (CHK-08 must not flag them).
_INGESTION_TIME_FIELD = "_PARTITIONTIME"


class BigQueryMetadataAdapter:
    def __init__(self, bigquery_service: Any) -> None:
        self._service = bigquery_service

    def list_datasets(self, project_id: str) -> tuple[str, ...]:
        ids: list[str] = []
        for page in self._pages(
            lambda token: self._service.datasets().list(projectId=project_id, pageToken=token)
        ):
            for entry in page.get("datasets") or []:
                ids.append(str(entry["datasetReference"]["datasetId"]))
        return tuple(ids)

    def get_dataset(self, project_id: str, dataset_id: str) -> DatasetMeta:
        data = self._service.datasets().get(projectId=project_id, datasetId=dataset_id).execute()
        encryption = data.get("defaultEncryptionConfiguration") or {}
        labels = data.get("labels") or {}
        return DatasetMeta(
            dataset_id=dataset_id,
            location=str(data.get("location", "")),
            default_table_expiration_ms=_optional_int(data.get("defaultTableExpirationMs")),
            default_partition_expiration_ms=_optional_int(data.get("defaultPartitionExpirationMs")),
            cmek_key=_optional_str(encryption.get("kmsKeyName")),
            access=_access_entries(data.get("access") or []),
            labels=tuple(sorted((str(k), str(v)) for k, v in labels.items())),
            tables=(),  # the collection use case assembles the tree (ports.py)
        )

    def list_tables(self, project_id: str, dataset_id: str) -> tuple[str, ...]:
        ids: list[str] = []
        for page in self._pages(
            lambda token: self._service.tables().list(
                projectId=project_id, datasetId=dataset_id, pageToken=token
            )
        ):
            for entry in page.get("tables") or []:
                ids.append(str(entry["tableReference"]["tableId"]))
        return tuple(ids)

    def get_table(self, project_id: str, dataset_id: str, table_id: str) -> TableMeta:
        data = (
            self._service.tables()
            .get(projectId=project_id, datasetId=dataset_id, tableId=table_id)
            .execute()
        )
        where = f"{project_id}.{dataset_id}.{table_id}"
        time_partitioning = data.get("timePartitioning") or {}
        range_partitioning = data.get("rangePartitioning") or {}
        time_field = time_partitioning.get("field") if time_partitioning else None
        if time_partitioning and time_field is None:
            time_field = _INGESTION_TIME_FIELD
        return TableMeta(
            table_id=table_id,
            table_type=str(data.get("type", "TABLE")),
            num_bytes=int(str(data.get("numBytes") or 0)),
            creation_time=_required_ms_timestamp(data.get("creationTime"), where=where),
            expiration_time=_optional_ms_timestamp(data.get("expirationTime")),
            time_partitioning_field=_optional_str(time_field),
            range_partitioning_field=_optional_str(range_partitioning.get("field")),
            require_partition_filter=bool(
                data.get("requirePartitionFilter")
                or time_partitioning.get("requirePartitionFilter")
            ),
            clustering_fields=tuple(
                str(f) for f in (data.get("clustering") or {}).get("fields") or []
            ),
            schema_fields=_flatten_schema((data.get("schema") or {}).get("fields") or []),
            description=_optional_str(data.get("description")),
        )

    @staticmethod
    def _pages(request_for_token: Any) -> list[dict[str, Any]]:
        """Drain a paginated list call; adapters always return complete results."""
        pages: list[dict[str, Any]] = []
        token: str | None = None
        while True:
            page = request_for_token(token).execute()
            pages.append(page)
            token = page.get("nextPageToken")
            if not token:
                return pages


def _access_entries(entries: list[dict[str, Any]]) -> tuple[AccessEntry, ...]:
    result: list[AccessEntry] = []
    for entry in entries:
        role = entry.get("role")
        if not role:
            continue  # authorized view/dataset/routine entries carry no role grant
        if "iamMember" in entry:
            member = str(entry["iamMember"])
        else:
            for key in _ACCESS_MEMBER_KEYS:
                if key in entry:
                    member = f"{key}:{entry[key]}"
                    break
            else:
                continue
        result.append(AccessEntry(role=str(role), member=member))
    return tuple(result)


def _flatten_schema(fields: list[dict[str, Any]], prefix: str = "") -> tuple[SchemaField, ...]:
    """Leaves only, nested RECORDs flattened to dotted paths (FR-1.3 view of the
    schema); BigQuery attaches policy tags to leaf columns exclusively."""
    out: list[SchemaField] = []
    for field in fields:
        path = f"{prefix}{field['name']}"
        children = field.get("fields")
        if children:
            out.extend(_flatten_schema(children, prefix=f"{path}."))
            continue
        tag_names = (field.get("policyTags") or {}).get("names") or []
        out.append(
            SchemaField(
                path=path,
                field_type=str(field.get("type", "")),
                policy_tag_ids=tuple(str(name) for name in tag_names),
                description=_optional_str(field.get("description")),
            )
        )
    return tuple(out)


def _optional_int(value: Any) -> int | None:
    return None if value is None else int(str(value))


def _optional_str(value: Any) -> str | None:
    return None if value is None else str(value)


def _required_ms_timestamp(value: Any, *, where: str) -> datetime:
    if value is None:
        raise ValueError(f"{where}: creationTime missing in tables.get response")
    return _ms_timestamp(value)


def _optional_ms_timestamp(value: Any) -> datetime | None:
    return None if value is None else _ms_timestamp(value)


def _ms_timestamp(value: Any) -> datetime:
    return datetime.fromtimestamp(int(str(value)) / 1000, tz=UTC)
