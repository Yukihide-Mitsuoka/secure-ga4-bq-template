"""Unit tests for column-security checkpoints CHK-04..05."""

from src.modules.inspection.domain.checks.column_security import (
    check_chk04_catalog_columns_untagged,
    check_chk05_taxonomy_consistency,
)
from src.modules.inspection.domain.finding import Severity
from src.modules.inspection.domain.snapshot import PolicyTag, SchemaField, Taxonomy
from tests.modules.inspection.builders import a_catalog, a_dataset, a_snapshot, a_table, params

TAG = "projects/verify-project/locations/asia-northeast1/taxonomies/1/policyTags/9"


def _mart_with(fields: tuple[SchemaField, ...], *, table_type: str = "TABLE"):  # type: ignore[no-untyped-def]
    table = a_table("fct_events", table_type=table_type, schema_fields=fields)
    return a_snapshot(datasets=(a_dataset("marts", tables=(table,)),))


def test_chk04_untagged_high_column_is_high() -> None:
    snapshot = _mart_with((SchemaField("user_id", "STRING"),))
    findings = check_chk04_catalog_columns_untagged(snapshot, params(), a_catalog())
    assert [f.severity for f in findings] == [Severity.HIGH]
    assert findings[0].resource.endswith("/tables/fct_events/columns/user_id")


def test_chk04_untagged_medium_column_is_medium() -> None:
    snapshot = _mart_with((SchemaField("user_pseudo_id", "STRING"),))
    findings = check_chk04_catalog_columns_untagged(snapshot, params(), a_catalog())
    assert [f.severity for f in findings] == [Severity.MEDIUM]


def test_chk04_tagged_column_passes() -> None:
    snapshot = _mart_with((SchemaField("user_id", "STRING", policy_tag_ids=(TAG,)),))
    assert check_chk04_catalog_columns_untagged(snapshot, params(), a_catalog()) == []


def test_chk04_views_are_skipped_by_design() -> None:
    # BigQuery cannot tag view columns; staging views rely on dataset IAM (LOG-0010).
    snapshot = _mart_with((SchemaField("user_id", "STRING"),), table_type="VIEW")
    assert check_chk04_catalog_columns_untagged(snapshot, params(), a_catalog()) == []


def test_chk04_uncataloged_column_is_not_flagged() -> None:
    snapshot = _mart_with((SchemaField("event_name", "STRING"),))
    assert check_chk04_catalog_columns_untagged(snapshot, params(), a_catalog()) == []


def test_chk04_raw_export_dataset_is_containment_only() -> None:
    table = a_table("events_20260711", schema_fields=(SchemaField("user_id", "STRING"),))
    snapshot = a_snapshot(datasets=(a_dataset("analytics_123", tables=(table,)),))
    assert check_chk04_catalog_columns_untagged(snapshot, params(), a_catalog()) == []


def test_chk04_unmatched_dataset_is_inspected_like_a_mart() -> None:
    table = a_table("t", schema_fields=(SchemaField("user_id", "STRING"),))
    snapshot = a_snapshot(datasets=(a_dataset("random_name", tables=(table,)),))
    findings = check_chk04_catalog_columns_untagged(snapshot, params(), a_catalog())
    assert len(findings) == 1


def _taxonomy(location: str = "asia-northeast1") -> Taxonomy:
    return Taxonomy(
        name=f"projects/verify-project/locations/{location}/taxonomies/1",
        display_name="ga4-sensitivity",
        location=location,
        policy_tags=(PolicyTag(TAG, "high"),),
    )


def test_chk05_dangling_tag_reference_is_high() -> None:
    dangling = TAG + "999"
    table = a_table("t", schema_fields=(SchemaField("user_id", "STRING", (dangling,)),))
    snapshot = a_snapshot(datasets=(a_dataset("marts", tables=(table,)),), taxonomies=())
    findings = check_chk05_taxonomy_consistency(snapshot, params(), a_catalog())
    assert [f.severity for f in findings] == [Severity.HIGH]
    assert "no taxonomy defines" in findings[0].observed


def test_chk05_location_mismatch_is_high() -> None:
    table = a_table("t", schema_fields=(SchemaField("user_id", "STRING", (TAG,)),))
    dataset = a_dataset("marts", location="us-central1", tables=(table,))
    snapshot = a_snapshot(datasets=(dataset,), taxonomies=(_taxonomy(),))
    findings = check_chk05_taxonomy_consistency(snapshot, params(), a_catalog())
    assert [f.severity for f in findings] == [Severity.HIGH]
    assert "location" in findings[0].observed


def test_chk05_location_comparison_is_case_insensitive() -> None:
    tag = "projects/verify-project/locations/us/taxonomies/1/policyTags/9"
    table = a_table("t", schema_fields=(SchemaField("user_id", "STRING", (tag,)),))
    dataset = a_dataset("marts", location="US", tables=(table,))
    taxonomy = Taxonomy(
        name="projects/verify-project/locations/us/taxonomies/1",
        display_name="ga4-sensitivity",
        location="us",
        policy_tags=(PolicyTag(tag, "high"),),
    )
    snapshot = a_snapshot(datasets=(dataset,), taxonomies=(taxonomy,))

    assert check_chk05_taxonomy_consistency(snapshot, params(), a_catalog()) == []


def test_chk05_orphan_tag_is_info() -> None:
    snapshot = a_snapshot(taxonomies=(_taxonomy(),))
    findings = check_chk05_taxonomy_consistency(snapshot, params(), a_catalog())
    assert [f.severity for f in findings] == [Severity.INFO]
    assert findings[0].resource == TAG


def test_chk05_consistent_tagging_yields_nothing() -> None:
    table = a_table("t", schema_fields=(SchemaField("user_id", "STRING", (TAG,)),))
    snapshot = a_snapshot(
        datasets=(a_dataset("marts", tables=(table,)),), taxonomies=(_taxonomy(),)
    )
    assert check_chk05_taxonomy_consistency(snapshot, params(), a_catalog()) == []
