import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
MODULE_PATH = ROOT / "scripts/github_governance.py"
SPEC = importlib.util.spec_from_file_location("github_governance_discovery", MODULE_PATH)
governance = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(governance)
SHA = "a" * 40


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
            "repos/acme/demo/branches/main": Completed(
                payload={"commit": {"sha": SHA}, "protected": protected}
            ),
            "repos/acme/demo/rules/branches/main?per_page=100": Completed(payload=[rules or []]),
            "repos/acme/demo/rulesets?includes_parents=false&per_page=100": Completed(payload=[[]]),
            f"repos/acme/demo/commits/{SHA}/check-runs?per_page=100": Completed(
                payload=[{"check_runs": [{"name": "test"}, {"name": "iac-scan"}]}]
            ),
            f"repos/acme/demo/commits/{SHA}/statuses?per_page=100": Completed(
                payload=[[{"context": "lint"}, {"context": "test"}]]
            ),
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
    assert result["observed_checks"] == ["iac-scan", "lint", "test"]
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


def test_inactive_repository_ruleset_is_listed_without_detail_metadata() -> None:
    runner = fake_runner(protected=False)
    runner.responses["repos/acme/demo/rulesets?includes_parents=false&per_page=100"] = Completed(
        payload=[
            [
                {
                    "id": 8,
                    "name": "inactive governance",
                    "source": "acme/demo",
                    "source_type": "Repository",
                }
            ]
        ]
    )

    result = governance.discover_github("acme/demo", "main", runner=runner)

    assert result["rulesets"] == [
        {
            "has_bypass_actors": "unknown",
            "id": 8,
            "name": "inactive governance",
            "source": "acme/demo",
            "source_type": "Repository",
        }
    ]
    assert "repos/acme/demo/rulesets/8" not in [call[0][-1] for call in runner.calls]


def test_repository_ruleset_summary_for_another_source_stops_closed() -> None:
    runner = fake_runner(protected=False)
    endpoint = "repos/acme/demo/rulesets?includes_parents=false&per_page=100"
    runner.responses[endpoint] = Completed(
        payload=[[{"id": 8, "name": "x", "source": "other/repo", "source_type": "Repository"}]]
    )
    with pytest.raises(governance.PolicyError, match="invalid ruleset"):
        governance.discover_github("acme/demo", "main", runner=runner)


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


def test_invalid_check_run_page_stops_closed_without_leaking_metadata() -> None:
    runner = fake_runner(protected=False)
    runner.responses[f"repos/acme/demo/commits/{SHA}/check-runs?per_page=100"] = Completed(
        payload=[[{"name": "secret-name"}]]
    )

    with pytest.raises(governance.PolicyError, match="invalid paginated") as failure:
        governance.discover_github("acme/demo", "main", runner=runner)
    assert "secret-name" not in str(failure.value)


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
        {
            "repos/acme/demo": Completed(payload=repository_payload()),
            "repos/acme/demo/branches/main": Completed(payload={"protected": False}),
            "repos/acme/demo/rules/branches/main?per_page=100": Completed(payload=[[]]),
        },
    ],
)
def test_malformed_required_responses_stop_closed(responses) -> None:
    with pytest.raises(governance.PolicyError):
        governance.discover_github("acme/demo", "main", runner=FakeRunner(responses))


def run_online(monkeypatch, capsys, command, status):
    calls = []

    def discover(repository, branch):
        calls.append((repository, branch))
        return {"inventory": True}

    monkeypatch.setattr(governance, "discover_github", discover)
    monkeypatch.setattr(
        governance,
        "compare_governance",
        lambda policy, inventory: {"repository": "acme/demo", "status": status},
    )
    exit_code = governance.main([command, "--root", str(ROOT), "--repo", "acme/demo"])
    return exit_code, json.loads(capsys.readouterr().out), calls


@pytest.mark.parametrize("status", ["compliant", "drift", "unknown"])
def test_plan_reports_every_completed_status_without_failing(monkeypatch, capsys, status) -> None:
    exit_code, report, calls = run_online(monkeypatch, capsys, "plan", status)

    assert exit_code == 0
    assert report["status"] == status
    assert calls == [("acme/demo", "main")]


@pytest.mark.parametrize(("status", "expected"), [("compliant", 0), ("drift", 1), ("unknown", 1)])
def test_audit_exit_distinguishes_compliance(monkeypatch, capsys, status, expected) -> None:
    exit_code, report, _ = run_online(monkeypatch, capsys, "audit", status)

    assert exit_code == expected
    assert report["status"] == status


def test_online_commands_require_repository(capsys) -> None:
    for command in ("plan", "audit"):
        with pytest.raises(SystemExit) as failure:
            governance.main([command, "--root", str(ROOT)])
        assert failure.value.code == 2
    capsys.readouterr()


def test_github_read_failure_returns_policy_error(monkeypatch, capsys) -> None:
    def fail(*args):
        raise governance.PolicyError("read failed")

    monkeypatch.setattr(governance, "discover_github", fail)

    assert governance.main(["audit", "--root", str(ROOT), "--repo", "acme/demo"]) == 2
    assert "governance policy error: read failed" in capsys.readouterr().err


def test_validate_remains_offline(monkeypatch, capsys) -> None:
    def unexpected(*args):
        raise AssertionError("validate called GitHub discovery")

    monkeypatch.setattr(governance, "discover_github", unexpected)

    assert governance.main(["validate", "--root", str(ROOT)]) == 0
    assert json.loads(capsys.readouterr().out)["managed_by"] == "ai-dev-foundation"
