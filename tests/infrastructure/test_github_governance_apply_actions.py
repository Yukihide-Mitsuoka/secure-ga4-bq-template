import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
MODULE_PATH = ROOT / "scripts/github_governance.py"
COMPARISON_PATH = Path(__file__).with_name("test_github_governance_comparison.py")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


governance = load("github_governance_apply_actions", MODULE_PATH)
comparison = load("github_governance_apply_fixtures", COMPARISON_PATH)


def missing_ruleset_inventory():
    inventory = comparison.ruleset_inventory()
    inventory["branch"]["protected"] = False
    inventory["effective_rules"] = []
    inventory["rulesets"] = []
    return inventory


def managed_update_state():
    return {
        "conditions": {"exclude": [], "include": ["refs/heads/main"]},
        "pull_request": {
            "allowed_merge_methods": ["squash"],
            "dismiss_stale_reviews_on_push": True,
            "require_code_owner_review": True,
            "require_last_push_approval": False,
            "required_approving_review_count": 0,
            "required_review_thread_resolution": True,
        },
        "required_status_checks": [
            {"context": "iac-scan", "integration_id": 42},
            {"context": "test", "integration_id": None},
        ],
        "rule_types": ["non_fast_forward", "pull_request", "required_status_checks"],
        "unsupported": [],
    }


def test_missing_ruleset_builds_child_safe_action_without_io(monkeypatch) -> None:
    monkeypatch.setattr(
        governance.subprocess,
        "run",
        lambda *args, **kwargs: pytest.fail("pure planner invoked subprocess"),
    )

    result = governance.build_apply_actions(
        comparison.resolved_policy(), missing_ruleset_inventory()
    )

    assert result["status"] == "ready"
    assert [action["id"] for action in result["actions"]] == ["branch.ruleset"]
    action = result["actions"][0]
    assert set(action) == {"body", "endpoint", "id", "method", "side_effects", "verify_controls"}
    assert (action["method"], action["endpoint"]) == ("POST", "repos/acme/demo/rulesets")
    assert set(action["verify_controls"]) == set(governance.BRANCH_CONTROL_IDS.values())
    assert action["side_effects"] == ["target_branch_merge_requirements_change_immediately"]
    assert action["body"]["bypass_actors"] == []
    pull, checks, no_force = action["body"]["rules"]
    assert pull["parameters"]["required_approving_review_count"] == 0
    assert pull["parameters"]["required_review_thread_resolution"] is True
    assert checks["parameters"]["strict_required_status_checks_policy"] is True
    assert {item["context"] for item in checks["parameters"]["required_status_checks"]} == set(
        comparison.CHECKS
    )
    assert {"iac-scan"} <= {
        item["context"] for item in checks["parameters"]["required_status_checks"]
    }
    assert no_force == {"type": "non_fast_forward"}


def test_existing_ruleset_builds_update_preserving_supported_constraints(monkeypatch) -> None:
    monkeypatch.setattr(
        governance.subprocess,
        "run",
        lambda *args, **kwargs: pytest.fail("pure planner invoked subprocess"),
    )
    policy = comparison.resolved_policy()
    inventory = comparison.ruleset_inventory()
    inventory["effective_rules"] = []
    inventory["rulesets"][0]["update_state"] = managed_update_state()
    before = copy.deepcopy((policy, inventory))

    result = governance.build_apply_actions(policy, inventory)

    assert result["status"] == "ready"
    assert len(result["actions"]) == 1
    action = result["actions"][0]
    assert (action["method"], action["endpoint"]) == ("PUT", "repos/acme/demo/rulesets/7")
    pull, checks, no_force = action["body"]["rules"]
    assert pull["parameters"] == {
        "allowed_merge_methods": ["squash"],
        "dismiss_stale_reviews_on_push": True,
        "require_code_owner_review": True,
        "require_last_push_approval": False,
        "required_approving_review_count": 0,
        "required_review_thread_resolution": True,
    }
    by_context = {
        check["context"]: check for check in checks["parameters"]["required_status_checks"]
    }
    assert set(by_context) == set(comparison.CHECKS)
    assert by_context["iac-scan"]["integration_id"] == 42
    assert "integration_id" not in by_context["test"]
    assert no_force == {"type": "non_fast_forward"}
    assert (policy, inventory) == before


@pytest.mark.parametrize(
    "unsafe",
    [
        "unavailable",
        "unsupported",
        "conditions",
        "unknown",
        "methods",
        "types",
        "extra_check",
        "review_count",
        "last_push",
        "inventory_mismatch",
        "duplicate_check",
        "id",
    ],
)
def test_existing_ruleset_update_rejects_unpreservable_state(unsafe) -> None:
    inventory = comparison.ruleset_inventory()
    inventory["effective_rules"] = []
    state = managed_update_state()
    if unsafe == "unavailable":
        pass
    elif unsafe == "unsupported":
        state["unsupported"] = ["unsupported_rule"]
    elif unsafe == "conditions":
        state["conditions"]["include"].append("refs/heads/release")
    elif unsafe == "unknown":
        state["pull_request"]["require_code_owner_review"] = "unknown"
    elif unsafe == "methods":
        state["pull_request"]["allowed_merge_methods"] = [[]]
    elif unsafe == "types":
        state["rule_types"] = [[]]
    elif unsafe == "extra_check":
        state["required_status_checks"].append(
            {"context": "external-approval", "integration_id": None}
        )
    elif unsafe == "review_count":
        state["pull_request"]["required_approving_review_count"] = 1
    elif unsafe == "last_push":
        state["pull_request"]["require_last_push_approval"] = True
    elif unsafe == "inventory_mismatch":
        state["pull_request"] = None
    elif unsafe == "duplicate_check":
        state["required_status_checks"].append({"context": "test", "integration_id": None})
    else:
        inventory["rulesets"][0]["id"] = 0
    if unsafe != "unavailable":
        inventory["rulesets"][0]["update_state"] = state

    with pytest.raises(governance.PolicyError):
        governance.build_apply_actions(comparison.resolved_policy(), inventory)


def test_common_actions_are_ordered_and_describe_side_effects() -> None:
    inventory = comparison.ruleset_inventory()
    inventory["repository"]["delete_branch_on_merge"] = False
    inventory["security"] = {
        "dependabot_security_updates": "enabled",
        "push_protection": "disabled",
        "secret_scanning": "disabled",
    }

    result = governance.build_apply_actions(comparison.resolved_policy(), inventory)

    assert [action["id"] for action in result["actions"]] == [
        "security.secret_scanning",
        "repository.delete_branch_on_merge",
        "security.dependabot_security_updates",
    ]
    assert result["actions"][0]["method"] == "PATCH"
    assert "pushes_containing_detected_secrets_are_rejected" in result["actions"][0]["side_effects"]
    assert result["actions"][2]["method"] == "DELETE"


def test_compliant_inventory_returns_no_actions_without_mutation() -> None:
    policy = comparison.resolved_policy()
    inventory = comparison.ruleset_inventory()
    before = copy.deepcopy((policy, inventory))

    result = governance.build_apply_actions(policy, inventory)

    assert result["status"] == "compliant"
    assert result["actions"] == []
    assert (policy, inventory) == before


@pytest.mark.parametrize(
    "unsafe", ["unknown", "unobserved", "existing", "duplicate", "legacy", "target"]
)
def test_unsafe_preconditions_fail_closed(unsafe) -> None:
    policy = comparison.resolved_policy()
    inventory = missing_ruleset_inventory()
    if unsafe == "unknown":
        inventory["security"]["secret_scanning"] = "unknown"
    elif unsafe == "unobserved":
        inventory["observed_checks"] = ["lint"]
    elif unsafe in {"existing", "duplicate"}:
        inventory = comparison.ruleset_inventory()
        inventory["effective_rules"] = []
        if unsafe == "duplicate":
            duplicate = copy.deepcopy(inventory["rulesets"][0])
            duplicate["id"] = 9
            inventory["rulesets"].append(duplicate)
    elif unsafe == "legacy":
        policy = comparison.resolved_policy("legacy_branch_protection")
    else:
        inventory["repository"]["full_name"] = "../unsafe"

    with pytest.raises(governance.PolicyError):
        governance.build_apply_actions(policy, inventory)


def test_organization_ruleset_with_managed_name_is_never_updated() -> None:
    inventory = comparison.ruleset_inventory()
    inventory["rulesets"][0].update(source="acme", source_type="Organization")
    for rule in inventory["effective_rules"]:
        rule.update(source="acme", source_type="Organization")

    result = governance.build_apply_actions(comparison.resolved_policy(), inventory)

    assert result["actions"][0]["method"] == "POST"
    assert result["actions"][0]["endpoint"] == "repos/acme/demo/rulesets"


def test_apply_requires_repository(capsys) -> None:
    with pytest.raises(SystemExit) as failure:
        governance.main(["apply", "--root", str(ROOT)])
    assert failure.value.code == 2
    assert "--repo is required" in capsys.readouterr().err


@pytest.mark.parametrize("confirmation", [None, "acme/other"])
def test_apply_requires_exact_confirmation_before_discovery(
    monkeypatch, capsys, confirmation
) -> None:
    calls = []

    def discover(*args):
        calls.append(args)

    monkeypatch.setattr(governance, "discover_github", discover)
    arguments = ["apply", "--root", str(ROOT), "--repo", "acme/demo"]
    if confirmation:
        arguments.extend(("--confirm-repo", confirmation))

    with pytest.raises(SystemExit) as failure:
        governance.main(arguments)

    assert failure.value.code == 2
    assert "--confirm-repo must exactly match --repo" in capsys.readouterr().err
    assert calls == []


@pytest.mark.parametrize(
    ("evidence", "error", "expected_exit"),
    [
        ({"repository": "acme/demo", "status": "compliant"}, None, 0),
        (
            {"failed_action": "branch.ruleset", "status": "failed"},
            "verification failed",
            2,
        ),
    ],
)
def test_apply_emits_success_or_partial_failure_evidence(
    monkeypatch, capsys, evidence, error, expected_exit
) -> None:
    inventory = {"inventory": True}
    calls = []

    monkeypatch.setattr(governance, "discover_github", lambda *args: inventory)

    def execute(policy, discovered, confirmed):
        calls.append((policy, discovered, confirmed))
        if error:
            raise governance.ApplyFailure(error, evidence)
        return evidence

    monkeypatch.setattr(governance, "execute_apply", execute)

    exit_code = governance.main(
        [
            "apply",
            "--root",
            str(ROOT),
            "--repo",
            "acme/demo",
            "--confirm-repo",
            "acme/demo",
        ]
    )
    streams = capsys.readouterr()

    assert exit_code == expected_exit
    assert json.loads(streams.out) == evidence
    assert len(calls) == 1
    assert "iac-scan" in calls[0][0]["settings"]["required_checks"]
    assert calls[0][1:] == (inventory, "acme/demo")
    if error:
        assert "governance apply error: verification failed" in streams.err
