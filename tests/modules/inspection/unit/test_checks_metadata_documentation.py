"""Unit tests for additive mart-metadata checkpoints CHK-12 and CHK-13."""

from dataclasses import replace

import pytest

from src.modules.inspection.domain.catalog import PromotedColumn, PromotionSource
from src.modules.inspection.domain.checks.metadata_documentation import (
    check_chk12_missing_descriptions,
    check_chk13_incomplete_promotion_sources,
)
from src.modules.inspection.domain.finding import Severity
from src.modules.inspection.domain.snapshot import SchemaField
from tests.modules.inspection.builders import a_catalog, a_dataset, a_snapshot, a_table, params


def _run(
    dataset_id: str = "marts",
    *,
    table_type: str = "TABLE",
    table_description: str | None = None,
    fields: tuple[SchemaField, ...] = (),
    exclude: tuple[str, ...] = (),
):
    table = replace(
        a_table("customer_orders", table_type=table_type, schema_fields=fields),
        description=table_description,
    )
    snapshot = a_snapshot(datasets=(a_dataset(dataset_id, tables=(table,)),))
    return check_chk12_missing_descriptions(
        snapshot,
        params(exclude=exclude),
        a_catalog(),
    )


def test_missing_table_and_whitespace_leaf_descriptions_emit_low_findings() -> None:
    findings = _run(
        fields=(
            SchemaField("order_id", "STRING", description="Business order identifier"),
            SchemaField("customer.email", "STRING", description=" \t "),
        )
    )

    assert [(finding.severity, finding.resource) for finding in findings] == [
        (
            Severity.LOW,
            "projects/verify-project/datasets/marts/tables/customer_orders",
        ),
        (
            Severity.LOW,
            "projects/verify-project/datasets/marts/tables/customer_orders/columns/customer.email",
        ),
    ]


def test_view_descriptions_are_evaluated() -> None:
    findings = _run(table_type="VIEW", table_description="", fields=())

    assert len(findings) == 1
    assert findings[0].resource.endswith("/tables/customer_orders")


def test_non_table_or_view_resources_are_not_evaluated() -> None:
    assert _run(table_type="EXTERNAL") == []


@pytest.mark.parametrize(
    ("dataset_id", "exclude"),
    [("analytics_123", ()), ("marts", ("marts",))],
)
def test_raw_and_excluded_datasets_are_not_evaluated(
    dataset_id: str, exclude: tuple[str, ...]
) -> None:
    assert _run(dataset_id, exclude=exclude) == []


def test_unmatched_dataset_is_evaluated_conservatively() -> None:
    findings = _run("unclassified")

    assert len(findings) == 1
    assert "/datasets/unclassified/" in findings[0].resource


def test_non_empty_descriptions_are_not_semantically_scored() -> None:
    findings = _run(
        table_description="x",
        fields=(SchemaField("order_id", "STRING", description="not useful prose"),),
    )

    assert findings == []


def _run_chk13(
    *,
    dataset_id: str = "marts",
    table_type: str = "TABLE",
    exclude: tuple[str, ...] = (),
    field_description: str | None = None,
):
    fields = (
        SchemaField("customer_email", "STRING", description=field_description),
        SchemaField("session_source", "STRING"),
    )
    table = a_table("customer_events", table_type=table_type, schema_fields=fields)
    snapshot = a_snapshot(datasets=(a_dataset(dataset_id, tables=(table,)),))
    catalog = a_catalog(
        columns={},
        promoted_columns={
            "customer_email": PromotedColumn(level="high"),
            "session_source": PromotedColumn(
                level="medium",
                source=PromotionSource(field_path="custom_attributes", key=" \t"),
            ),
            "catalog_only": PromotedColumn(level="low"),
        },
    )
    return check_chk13_incomplete_promotion_sources(
        snapshot,
        params(exclude=exclude),
        catalog,
    )


def test_incomplete_sources_for_observed_promoted_columns_emit_low_findings() -> None:
    findings = _run_chk13(field_description="source.key=customer_email")

    assert [(finding.severity, finding.resource, finding.observed) for finding in findings] == [
        (
            Severity.LOW,
            "projects/verify-project/datasets/marts/tables/customer_events/columns/customer_email",
            "promotion source declaration is missing source.field_path and source.key",
        ),
        (
            Severity.LOW,
            "projects/verify-project/datasets/marts/tables/customer_events/columns/session_source",
            "promotion source declaration is missing source.key",
        ),
    ]
    assert all(finding.rule_ref == "FR-10.1" for finding in findings)


def test_complete_source_is_silent_and_values_are_source_agnostic() -> None:
    field = SchemaField("customer_email", "STRING")
    snapshot = a_snapshot(datasets=(a_dataset("marts", tables=(a_table(schema_fields=(field,)),)),))
    catalog = a_catalog(
        columns={},
        promoted_columns={
            "customer_email": PromotedColumn(
                level="high",
                source=PromotionSource(
                    field_path="custom_attributes",
                    key="primary_email",
                ),
            )
        },
    )

    assert check_chk13_incomplete_promotion_sources(snapshot, params(), catalog) == []


@pytest.mark.parametrize(
    ("dataset_id", "table_type", "exclude"),
    [
        ("analytics_123", "TABLE", ()),
        ("marts", "TABLE", ("marts",)),
        ("marts", "EXTERNAL", ()),
    ],
)
def test_chk13_skips_raw_excluded_and_non_table_view_resources(
    dataset_id: str,
    table_type: str,
    exclude: tuple[str, ...],
) -> None:
    assert _run_chk13(dataset_id=dataset_id, table_type=table_type, exclude=exclude) == []


def test_chk13_evaluates_views_and_unmatched_datasets_conservatively() -> None:
    findings = _run_chk13(dataset_id="unclassified", table_type="VIEW")

    assert len(findings) == 2
    assert all("/datasets/unclassified/" in finding.resource for finding in findings)
