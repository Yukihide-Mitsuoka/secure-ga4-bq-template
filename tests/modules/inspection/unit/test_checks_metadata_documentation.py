"""Unit tests for mart-description completeness checkpoint CHK-12."""

from dataclasses import replace

import pytest

from src.modules.inspection.domain.checks.metadata_documentation import (
    check_chk12_missing_descriptions,
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
