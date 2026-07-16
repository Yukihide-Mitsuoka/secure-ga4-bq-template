import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
MODULE_PATH = ROOT / "scripts/github_governance.py"
SPEC = importlib.util.spec_from_file_location("github_governance_discovery", MODULE_PATH)
governance = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(governance)


class Completed:
    def __init__(self, returncode=0, payload=None):
        self.returncode = returncode
        self.stdout = json.dumps(payload) if payload is not None else ""
        self.stderr = "sensitive runner detail"


class FakeRunner:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def __call__(self, command, **kwargs):
        self.calls.append((command, kwargs))
        return self.responses.get(command[-1], Completed(returncode=1))


def repository_payload(security=True):
    payload = {"default_branch": "main", "delete_branch_on_merge": True}
    if security:
        payload["security_and_analysis"] = {
            "secret_scanning": {"status": "enabled"},
            "secret_scanning_push_protection": {"status": "enabled"},
            "dependabot_security_updates": {"status": "disabled"},
        }
    return payload


def fake_runner(*, rules=None, protected=True, security=True):
    return FakeRunner(
        {
            "repos/acme/demo": Completed(payload=repository_payload(security)),
            "repos/acme/demo/branches/main": Completed(payload={"protected": protected}),
            "repos/acme/demo/rules/branches/main?per_page=100": Completed(payload=[rules or []]),
        }
    )


def test_discovery_is_get_only_deterministic_and_redacts_bypass_identities() -> None:
    rules = [
        {
            "type": "pull_request",
            "ruleset_id": 7,
            "ruleset_source_type": "Repository",
            "ruleset_source": "acme/demo",
            "parameters": {"required_approving_review_count": 1},
        }
    ]
    runner = fake_runner(rules=rules)
    runner.responses.update(
        {
            "repos/acme/demo/rulesets/7": Completed(
                payload={"name": "main governance", "bypass_actors": [{"actor_id": 123}]}
            ),
            "repos/acme/demo/branches/main/protection": Completed(payload={}),
        }
    )

    result = governance.discover_github("acme/demo", "main", runner=runner)

    assert result["rulesets"][0]["has_bypass_actors"] is True
    assert result["legacy_branch_protection"]["status"] == "configured"
    assert "123" not in json.dumps(result)
    assert result["effective_rules"][0]["parameters"]["required_approving_review_count"] == 1
    for command, kwargs in runner.calls:
        assert command[command.index("--method") + 1] == "GET"
        assert "X-GitHub-Api-Version: 2026-03-10" in command
        assert kwargs == {"capture_output": True, "text": True, "timeout": 30, "check": False}
        assert not {"POST", "PUT", "PATCH", "DELETE"} & set(command)


def test_admin_invisible_fields_are_unknown_without_leaking_stderr() -> None:
    rules = [
        {
            "type": "pull_request",
            "ruleset_id": 9,
            "ruleset_source_type": "Repository",
            "ruleset_source": [],
        }
    ]
    runner = fake_runner(rules=rules, security=False)

    result = governance.discover_github("acme/demo", "main", runner=runner)

    assert result["security"]["secret_scanning"] == "unknown"
    assert result["rulesets"][0]["has_bypass_actors"] == "unknown"
    assert result["legacy_branch_protection"]["status"] == "unknown"
    assert result["effective_rules"][0]["source"] == "unknown"
    assert "sensitive runner detail" not in json.dumps(result)


def test_unprotected_branch_skips_legacy_admin_endpoint() -> None:
    runner = fake_runner(protected=False)

    result = governance.discover_github("acme/demo", "main", runner=runner)

    assert result["legacy_branch_protection"] == {"status": "absent"}
    assert "repos/acme/demo/branches/main/protection" not in [
        command[-1] for command, _ in runner.calls
    ]


def test_required_read_and_runner_failures_stop_closed() -> None:
    with pytest.raises(governance.PolicyError, match="GitHub GET failed") as failure:
        governance.discover_github(
            "acme/demo", "main", runner=FakeRunner({"repos/acme/demo": Completed(returncode=1)})
        )
    assert "sensitive runner detail" not in str(failure.value)

    def unavailable(*args, **kwargs):
        raise OSError("gh unavailable")

    with pytest.raises(governance.PolicyError, match="could not run"):
        governance.discover_github("acme/demo", "main", runner=unavailable)


@pytest.mark.parametrize(
    ("repository", "branch"),
    [("../..", "main"), ("acme/demo", "../main"), ("acme", "main")],
)
def test_invalid_targets_are_rejected_before_runner(repository, branch) -> None:
    runner = FakeRunner({})

    with pytest.raises(governance.PolicyError):
        governance.discover_github(repository, branch, runner=runner)
    assert runner.calls == []


@pytest.mark.parametrize(
    "responses",
    [
        {"repos/acme/demo": Completed(payload=[])},
        {
            "repos/acme/demo": Completed(payload=repository_payload()),
            "repos/acme/demo/branches/main": Completed(payload={"protected": "yes"}),
            "repos/acme/demo/rules/branches/main?per_page=100": Completed(payload=[[]]),
        },
    ],
)
def test_malformed_required_responses_stop_closed(responses) -> None:
    with pytest.raises(governance.PolicyError):
        governance.discover_github("acme/demo", "main", runner=FakeRunner(responses))
