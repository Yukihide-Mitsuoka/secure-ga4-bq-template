"""Registry-level tests: the B acceptance bar at unit scale.

Requirements §8 (B criteria) demands the engine detect >= 10 of the 11
checkpoints. `test_worst_case_project_triggers_all_eleven_checkpoints` builds a
deliberately broken project and asserts every checkpoint fires — i.e. the
registry detects 11/11 deterministically, without touching GCP.
"""

from datetime import timedelta

from src.modules.inspection.domain.checks import ALL_CHECKS
from src.modules.inspection.domain.finding import sorted_findings
from src.modules.inspection.domain.snapshot import (
    AccessEntry,
    AuditConfig,
    AuditLogConfig,
    IamBinding,
    LoggingConfig,
    LogSink,
    PolicyTag,
    ProjectIam,
    SchemaField,
    Taxonomy,
)
from tests.modules.inspection.builders import (
    FIXED_NOW,
    a_catalog,
    a_dataset,
    a_snapshot,
    a_table,
    params,
)


def worst_case_snapshot():  # type: ignore[no-untyped-def]
    dangling_tag = "projects/verify-project/locations/asia-northeast1/taxonomies/1/policyTags/404"
    orphan_taxonomy = Taxonomy(
        name="projects/verify-project/locations/asia-northeast1/taxonomies/2",
        display_name="ga4-sensitivity",
        location="asia-northeast1",
        policy_tags=(
            PolicyTag(
                "projects/verify-project/locations/asia-northeast1/taxonomies/2/policyTags/7",
                "high",
            ),
        ),
    )
    bad_table = a_table(
        "fct_events",
        num_bytes=11 * 1024**3,  # CHK-08: large...
        time_partitioning_field=None,  # ...and unpartitioned
        clustering_fields=(),
        creation_time=FIXED_NOW - timedelta(days=200),  # CHK-10: old, no expiration
        schema_fields=(
            SchemaField("user_id", "STRING"),  # CHK-04: cataloged high, untagged
            SchemaField("page_location", "STRING", (dangling_tag,)),  # CHK-05: dangling
        ),
    )
    partitioned_loose = a_table(
        "dim_users",
        require_partition_filter=False,  # CHK-09
        creation_time=FIXED_NOW - timedelta(days=1),
    )
    bad_dataset = a_dataset(
        "marts",
        location="us-central1",  # CHK-11: location deviation (+ no expiration, no CMEK)
        access=(
            AccessEntry("roles/editor", "user:contractor@example.com"),  # CHK-01
            AccessEntry("READER", "specialGroup:allAuthenticatedUsers"),  # CHK-02
        ),
        tables=(bad_table, partitioned_loose),
    )
    return a_snapshot(
        iam=ProjectIam(
            bindings=(
                IamBinding("roles/owner", ("user:admin@example.com",)),  # CHK-01
                IamBinding("roles/bigquery.dataViewer", ("allUsers",)),  # CHK-02 + CHK-03
            ),
            audit_configs=(
                AuditConfig("allServices", (AuditLogConfig("DATA_READ"),)),  # CHK-06
            ),
        ),
        datasets=(bad_dataset,),
        taxonomies=(orphan_taxonomy,),  # CHK-05: orphan tag
        logging=LoggingConfig(
            sinks=(
                LogSink(  # CHK-06: unrestricted data-access ingestion; also audit sink
                    "everything",
                    "storage.googleapis.com/all-logs",
                    filter='log_id("cloudaudit.googleapis.com/data_access")',
                ),
            ),
            exclusions=(),  # CHK-07: no exclusion filters
        ),
    )


def test_registry_holds_exactly_the_eleven_fr4_checkpoints() -> None:
    assert len(ALL_CHECKS) == 11


def test_worst_case_project_triggers_all_eleven_checkpoints() -> None:
    snapshot, scoped, catalog = worst_case_snapshot(), params(), a_catalog()
    findings = [f for check in ALL_CHECKS for f in check(snapshot, scoped, catalog)]
    fired = {f.check_id for f in findings}
    assert fired == {f"CHK-{i:02d}" for i in range(1, 12)}


def test_clean_project_triggers_almost_nothing() -> None:
    # A compliant snapshot: the only allowed noise is CHK-07 pipeline advice
    # (no audit sink configured in an empty project) — everything else is silent.
    snapshot, scoped, catalog = a_snapshot(), params(), a_catalog()
    findings = [f for check in ALL_CHECKS for f in check(snapshot, scoped, catalog)]
    assert {f.check_id for f in findings} <= {"CHK-07"}


def test_full_run_output_order_is_deterministic() -> None:
    snapshot, scoped, catalog = worst_case_snapshot(), params(), a_catalog()
    first = sorted_findings([f for check in ALL_CHECKS for f in check(snapshot, scoped, catalog)])
    second = sorted_findings(
        [f for check in reversed(ALL_CHECKS) for f in check(snapshot, scoped, catalog)]
    )
    assert first == second
