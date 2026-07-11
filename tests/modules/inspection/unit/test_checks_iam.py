"""Unit tests for IAM checkpoints CHK-01..03."""

from src.modules.inspection.domain.checks.iam import (
    check_chk01_basic_roles,
    check_chk02_public_members,
    check_chk03_project_wide_data_roles,
)
from src.modules.inspection.domain.finding import Severity
from src.modules.inspection.domain.snapshot import AccessEntry, IamBinding, ProjectIam
from tests.modules.inspection.builders import a_catalog, a_dataset, a_snapshot, params


def test_chk01_project_owner_is_high() -> None:
    snapshot = a_snapshot(
        iam=ProjectIam(bindings=(IamBinding("roles/owner", ("user:a@example.com",)),))
    )
    findings = check_chk01_basic_roles(snapshot, params(), a_catalog())
    assert [f.severity for f in findings] == [Severity.HIGH]
    assert findings[0].resource == "projects/verify-project"


def test_chk01_viewer_is_detected_one_notch_lighter_at_medium() -> None:
    # Owner ruling LOG-0014: FR-2 bans all three basic roles; viewer -> MEDIUM.
    snapshot = a_snapshot(
        iam=ProjectIam(bindings=(IamBinding("roles/viewer", ("user:a@example.com",)),))
    )
    findings = check_chk01_basic_roles(snapshot, params(), a_catalog())
    assert [f.severity for f in findings] == [Severity.MEDIUM]


def test_chk01_editor_on_dataset_access_is_flagged_on_the_dataset() -> None:
    dataset = a_dataset("marts", access=(AccessEntry("roles/editor", "user:b@example.com"),))
    findings = check_chk01_basic_roles(a_snapshot(datasets=(dataset,)), params(), a_catalog())
    assert [f.resource for f in findings] == ["projects/verify-project/datasets/marts"]
    assert findings[0].severity is Severity.HIGH


def test_chk01_excluded_dataset_is_not_scanned() -> None:
    dataset = a_dataset("scratch", access=(AccessEntry("roles/owner", "user:b@example.com"),))
    scoped = params(exclude=("scratch",))
    assert check_chk01_basic_roles(a_snapshot(datasets=(dataset,)), scoped, a_catalog()) == []


def test_chk01_predefined_roles_are_not_findings() -> None:
    snapshot = a_snapshot(
        iam=ProjectIam(bindings=(IamBinding("roles/bigquery.jobUser", ("user:a@x.com",)),))
    )
    assert check_chk01_basic_roles(snapshot, params(), a_catalog()) == []


def test_chk02_all_users_on_project_is_high() -> None:
    snapshot = a_snapshot(
        iam=ProjectIam(bindings=(IamBinding("roles/bigquery.dataViewer", ("allUsers",)),))
    )
    findings = check_chk02_public_members(snapshot, params(), a_catalog())
    assert [f.severity for f in findings] == [Severity.HIGH]


def test_chk02_special_group_all_authenticated_on_dataset_is_high() -> None:
    dataset = a_dataset(
        "marts", access=(AccessEntry("READER", "specialGroup:allAuthenticatedUsers"),)
    )
    findings = check_chk02_public_members(a_snapshot(datasets=(dataset,)), params(), a_catalog())
    assert [f.resource for f in findings] == ["projects/verify-project/datasets/marts"]


def test_chk02_clean_project_yields_nothing() -> None:
    assert check_chk02_public_members(a_snapshot(), params(), a_catalog()) == []


def test_chk03_project_wide_data_viewer_is_medium() -> None:
    snapshot = a_snapshot(
        iam=ProjectIam(bindings=(IamBinding("roles/bigquery.dataViewer", ("group:g@x.com",)),))
    )
    findings = check_chk03_project_wide_data_roles(snapshot, params(), a_catalog())
    assert [f.severity for f in findings] == [Severity.MEDIUM]


def test_chk03_non_data_roles_project_wide_are_not_flagged() -> None:
    snapshot = a_snapshot(
        iam=ProjectIam(bindings=(IamBinding("roles/bigquery.jobUser", ("group:g@x.com",)),))
    )
    assert check_chk03_project_wide_data_roles(snapshot, params(), a_catalog()) == []
