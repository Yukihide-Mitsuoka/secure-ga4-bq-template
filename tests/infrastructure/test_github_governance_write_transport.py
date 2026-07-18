import copy
import importlib.util
import subprocess
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).parents[2]
SPEC = importlib.util.spec_from_file_location(
    "github_governance_write_transport", ROOT / "scripts/github_governance.py"
)
governance = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(governance)
REPOSITORY = "acme/demo"


def action():
    return {
        "body": {"security_and_analysis": {"secret_scanning": {"status": "enabled"}}},
        "endpoint": f"repos/{REPOSITORY}",
        "id": "security.secret_scanning",
        "method": "PATCH",
        "side_effects": [],
        "verify_controls": ["security.secret_scanning"],
    }


def test_write_uses_json_stdin_fixed_api_version_and_no_shell() -> None:
    current = action()
    before = copy.deepcopy(current)
    completed = subprocess.CompletedProcess([], 0, stdout="{}", stderr="")
    runner = mock.Mock(return_value=completed)

    governance._gh_write_action(current, REPOSITORY, runner)

    command = runner.call_args.args[0]
    assert command[:4] == ["gh", "api", "--method", "PATCH"]
    assert f"X-GitHub-Api-Version: {governance.API_VERSION}" in command
    assert command[-3:] == [f"repos/{REPOSITORY}", "--input", "-"]
    assert runner.call_args.kwargs["timeout"] == 30
    assert "shell" not in runner.call_args.kwargs
    assert runner.call_args.kwargs["input"] == (
        '{"security_and_analysis":{"secret_scanning":{"status":"enabled"}}}'
    )
    assert current == before


@pytest.mark.parametrize(
    "unsafe",
    ["id", "method", "endpoint", "body", "body_fields", "body_keys", "controls"],
)
def test_write_allowlist_rejects_untrusted_actions(unsafe) -> None:
    candidate = action()
    field, value = {
        "id": ("id", "unknown.action"),
        "method": ("method", "GET"),
        "endpoint": ("endpoint", "repos/acme/other"),
        "body": ("body", None),
        "body_fields": ("body", {"visibility": "private"}),
        "body_keys": (
            "body",
            {"security_and_analysis": {1: {"status": "enabled"}}},
        ),
        "controls": ("verify_controls", []),
    }[unsafe]
    candidate[field] = value
    runner = mock.Mock()

    with pytest.raises(governance.PolicyError, match="invalid|not allowed"):
        governance._gh_write_action(candidate, REPOSITORY, runner)

    runner.assert_not_called()


@pytest.mark.parametrize(
    ("action_id", "method", "endpoint", "body"),
    [
        (
            "branch.ruleset",
            "POST",
            f"repos/{REPOSITORY}/rulesets",
            governance._ruleset_payload(
                {
                    "required_checks": ["CI", "iac-scan"],
                    "required_approvals": 0,
                    "require_last_push_approval": False,
                    "target_branch": "main",
                }
            ),
        ),
        (
            "branch.ruleset",
            "PUT",
            f"repos/{REPOSITORY}/rulesets/42",
            governance._ruleset_payload(
                {
                    "required_checks": ["CI", "iac-scan"],
                    "required_approvals": 0,
                    "require_last_push_approval": False,
                    "target_branch": "main",
                }
            ),
        ),
        (
            "security.dependabot_security_updates",
            "DELETE",
            f"repos/{REPOSITORY}/automated-security-fixes",
            None,
        ),
        (
            "security.vulnerability_alerts",
            "PUT",
            f"repos/{REPOSITORY}/vulnerability-alerts",
            None,
        ),
        (
            "security.private_vulnerability_reporting",
            "PUT",
            f"repos/{REPOSITORY}/private-vulnerability-reporting",
            None,
        ),
    ],
)
def test_write_allowlist_accepts_only_current_planner_shapes(
    action_id, method, endpoint, body
) -> None:
    candidate = action()
    candidate.update(id=action_id, method=method, endpoint=endpoint, body=body)
    candidate["verify_controls"] = (
        sorted(governance.BRANCH_CONTROL_IDS.values())
        if action_id == "branch.ruleset"
        else [action_id]
    )
    completed = subprocess.CompletedProcess([], 0, stdout="{}", stderr="")
    runner = mock.Mock(return_value=completed)

    governance._gh_write_action(candidate, REPOSITORY, runner)

    assert runner.call_count == 1


@pytest.mark.parametrize(
    ("action_id", "endpoint"),
    [
        ("security.vulnerability_alerts", f"repos/{REPOSITORY}/vulnerability-alerts"),
        (
            "security.private_vulnerability_reporting",
            f"repos/{REPOSITORY}/private-vulnerability-reporting",
        ),
    ],
)
@pytest.mark.parametrize("mutation", ["method", "endpoint", "body", "controls"])
def test_vulnerability_intake_write_allowlist_requires_exact_shape(
    action_id, endpoint, mutation
) -> None:
    candidate = action()
    candidate.update(
        id=action_id,
        method="PUT",
        endpoint=endpoint,
        body=None,
        verify_controls=[action_id],
    )
    if mutation == "method":
        candidate["method"] = "DELETE"
    elif mutation == "endpoint":
        candidate["endpoint"] = f"repos/{REPOSITORY}/automated-security-fixes"
    elif mutation == "body":
        candidate["body"] = {}
    else:
        candidate["verify_controls"] = ["security.secret_scanning"]
    runner = mock.Mock()

    with pytest.raises(governance.PolicyError, match="not allowed"):
        governance._gh_write_action(candidate, REPOSITORY, runner)

    runner.assert_not_called()


def test_write_failure_redacts_response_and_stderr() -> None:
    completed = subprocess.CompletedProcess(
        [], 1, stdout='{"token":"ghp_response"}', stderr="token ghp_sensitive"
    )
    runner = mock.Mock(return_value=completed)

    with pytest.raises(governance.PolicyError) as failure:
        governance._gh_write_action(action(), REPOSITORY, runner)

    assert "ghp_sensitive" not in str(failure.value)
    assert "ghp_response" not in str(failure.value)
    assert runner.call_count == 1


def test_write_rejects_an_unsafe_confirmed_repository() -> None:
    runner = mock.Mock()

    with pytest.raises(governance.PolicyError, match="safe write target"):
        governance._gh_write_action(action(), "acme/..", runner)

    runner.assert_not_called()
