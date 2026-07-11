"""Unit tests for the inspection domain's Finding model.

Mirror src/ layout (TST-001); names read as specifications (TST-010); error paths
and boundaries covered, not just the happy path (TST-002). Pure domain — no I/O.
"""

import pytest

from src.modules.inspection.domain.finding import Finding, Severity, sorted_findings


def make_finding(check_id: str = "CHK-01", resource: str = "projects/p") -> Finding:
    return Finding(
        check_id=check_id,
        severity=Severity.HIGH,
        resource=resource,
        observed="roles/owner bound to user:a@example.com",
        expected="no basic roles on the project (FR-2)",
        rule_ref="FR-4 #1",
        remediation_hint="replace with a dataset-grain predefined role",
    )


def test_valid_check_ids_are_accepted_across_the_full_range() -> None:
    for check_id in ("CHK-01", "CHK-09", "CHK-10", "CHK-11"):
        assert make_finding(check_id=check_id).check_id == check_id


def test_check_id_outside_chk01_to_chk11_is_rejected() -> None:
    for bad in ("CHK-00", "CHK-12", "CHK-1", "chk-01", "FR-4", ""):
        with pytest.raises(ValueError):
            make_finding(check_id=bad)


def test_empty_resource_is_rejected() -> None:
    with pytest.raises(ValueError):
        make_finding(resource="")


def test_findings_are_immutable() -> None:
    finding = make_finding()
    with pytest.raises(AttributeError):
        finding.severity = Severity.LOW  # type: ignore[misc]


def test_sorted_findings_orders_by_check_id_then_resource() -> None:
    unordered = [
        make_finding("CHK-03", "projects/p/datasets/b"),
        make_finding("CHK-01", "projects/p/datasets/z"),
        make_finding("CHK-03", "projects/p/datasets/a"),
        make_finding("CHK-01", "projects/p/datasets/a"),
    ]
    ordered = sorted_findings(unordered)
    assert [(f.check_id, f.resource) for f in ordered] == [
        ("CHK-01", "projects/p/datasets/a"),
        ("CHK-01", "projects/p/datasets/z"),
        ("CHK-03", "projects/p/datasets/a"),
        ("CHK-03", "projects/p/datasets/b"),
    ]


def test_sorted_findings_is_deterministic_for_equal_inputs() -> None:
    findings = [make_finding("CHK-02", f"projects/p/datasets/d{i}") for i in (3, 1, 2)]
    assert sorted_findings(findings) == sorted_findings(list(reversed(findings)))


def test_sorted_findings_handles_empty_input() -> None:
    assert sorted_findings([]) == []
