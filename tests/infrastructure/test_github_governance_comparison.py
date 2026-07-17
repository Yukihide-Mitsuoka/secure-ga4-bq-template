import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
MODULE_PATH = ROOT / "scripts/github_governance.py"
SPEC = importlib.util.spec_from_file_location("github_governance_comparison", MODULE_PATH)
governance = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(governance)

CHECKS = sorted(
    [
        "lint",
        "test",
        "build",
        "doctor",
        "link-check",
        "pr-quality",
        "secret-scan",
        "dependency-scan",
        "license-check",
        "iac-scan",
    ]
)


def resolved_policy(backend="ruleset"):
    return {
        "minimums": {
            name: {"rule_refs": sorted(rule_refs)}
            for name, (_, rule_refs) in governance.MINIMUM_CONTRACT.items()
        },
        "settings": {
            "target_branch": "main",
            "enforcement_backend": backend,
            "required_approvals": 0,
            "require_last_push_approval": False,
            "required_checks": CHECKS,
            "dependency_update_provider": "renovate",
            "delete_branch_on_merge": True,
        },
    }


def ruleset_inventory():
    rule_base = {"ruleset_id": 7, "source": "acme/demo", "source_type": "Repository"}
    return {
        "branch": {"name": "main", "protected": True},
        "effective_rules": [
            {
                **rule_base,
                "type": "pull_request",
                "parameters": {
                    "required_approving_review_count": 0,
                    "require_last_push_approval": False,
                },
            },
            {
                **rule_base,
                "type": "required_status_checks",
                "parameters": {"contexts": list(CHECKS)},
            },
            {**rule_base, "type": "non_fast_forward", "parameters": {}},
        ],
        "legacy_branch_protection": {"status": "absent"},
        "observed_checks": list(CHECKS),
        "repository": {"delete_branch_on_merge": True, "full_name": "acme/demo"},
        "rulesets": [
            {
                "has_bypass_actors": False,
                "id": 7,
                "name": governance.MANAGED_RULESET_NAME,
                "source": "acme/demo",
                "source_type": "Repository",
            }
        ],
        "security": {
            "dependabot_security_updates": "disabled",
            "push_protection": "enabled",
            "secret_scanning": "enabled",
        },
    }


def legacy_inventory():
    inventory = ruleset_inventory()
    inventory["effective_rules"] = []
    inventory["rulesets"] = []
    inventory["legacy_branch_protection"] = {
        "allow_force_pushes": False,
        "enforce_admins": True,
        "required_pull_request_reviews": {
            "require_last_push_approval": False,
            "required_approvals": 0,
        },
        "required_status_checks": {"contexts": list(CHECKS), "strict": True},
        "status": "configured",
    }
    return inventory


def control(report, control_id):
    return next(item for item in report["controls"] if item["id"] == control_id)


def test_ruleset_report_is_compliant_deterministic_and_does_not_mutate_inputs() -> None:
    policy = resolved_policy()
    inventory = ruleset_inventory()
    before = copy.deepcopy((policy, inventory))

    first = governance.compare_governance(policy, inventory)
    second = governance.compare_governance(policy, inventory)

    assert first["status"] == "compliant"
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert [item["id"] for item in first["controls"]] == sorted(
        item["id"] for item in first["controls"]
    )
    assert control(first, "branch.required_status_checks")["current"] == CHECKS
    assert first["unmanaged"] == {"effective_rules": [], "legacy_branch_protection": None}
    assert (policy, inventory) == before


def test_managed_repository_source_matching_is_case_insensitive() -> None:
    inventory = ruleset_inventory()
    inventory["rulesets"][0]["source"] = "Acme/Demo"

    assert governance.compare_governance(resolved_policy(), inventory)["status"] == "compliant"


def test_missing_iac_scan_and_unmanaged_controls_report_drift() -> None:
    inventory = ruleset_inventory()
    inventory["effective_rules"][1]["parameters"]["contexts"].remove("iac-scan")
    inventory["legacy_branch_protection"] = {"status": "configured"}
    inventory["effective_rules"].append(
        {
            "parameters": {},
            "ruleset_id": 8,
            "source": "acme/demo",
            "source_type": "Repository",
            "type": "required_linear_history",
        }
    )

    report = governance.compare_governance(resolved_policy(), inventory)

    assert report["status"] == "drift"
    assert control(report, "branch.required_status_checks")["status"] == "drift"
    assert len(report["unmanaged"]["effective_rules"]) == 1
    assert report["unmanaged"]["legacy_branch_protection"]["status"] == "configured"


def test_admin_invisible_control_makes_report_unknown() -> None:
    inventory = ruleset_inventory()
    inventory["rulesets"][0]["has_bypass_actors"] = "unknown"

    report = governance.compare_governance(resolved_policy(), inventory)

    assert report["status"] == "unknown"
    assert control(report, "branch.admin_bypass_allowed")["status"] == "unknown"


def test_unobserved_iac_scan_is_drift_but_unrelated_checks_are_ignored() -> None:
    inventory = ruleset_inventory()
    inventory["observed_checks"].remove("iac-scan")
    inventory["observed_checks"].append("unrelated")

    report = governance.compare_governance(resolved_policy(), inventory)

    observed = control(report, "branch.required_status_checks_observed")
    assert observed["status"] == "drift"
    assert "unrelated" not in observed["current"]


def test_legacy_backend_can_be_compliant() -> None:
    report = governance.compare_governance(
        resolved_policy("legacy_branch_protection"), legacy_inventory()
    )

    assert report["status"] == "compliant"
    assert control(report, "branch.enforcement_backend")["current"] == ("legacy_branch_protection")


@pytest.mark.parametrize("duplicate", ["ruleset", "required_status_checks"])
def test_duplicate_managed_inputs_are_rejected(duplicate) -> None:
    inventory = ruleset_inventory()
    if duplicate == "ruleset":
        extra = copy.deepcopy(inventory["rulesets"][0])
        extra["id"] = 9
        inventory["rulesets"].append(extra)
    else:
        inventory["effective_rules"].append(copy.deepcopy(inventory["effective_rules"][1]))

    with pytest.raises(governance.PolicyError):
        governance.compare_governance(resolved_policy(), inventory)


def test_missing_inventory_fields_and_branch_mismatch_are_rejected() -> None:
    with pytest.raises(governance.PolicyError, match="missing required"):
        governance.compare_governance(resolved_policy(), {})

    inventory = ruleset_inventory()
    inventory["branch"]["name"] = "develop"
    with pytest.raises(governance.PolicyError, match="does not match"):
        governance.compare_governance(resolved_policy(), inventory)
