import copy
import importlib.util
import subprocess
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).parents[2]
SPEC = importlib.util.spec_from_file_location(
    "github_governance_apply_execution", ROOT / "scripts/github_governance.py"
)
governance = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(governance)
REPOSITORY = "acme/demo"
BRANCH = "main"


def action(action_id="security.secret_scanning", control="security.secret_scanning"):
    return {
        "body": {"security_and_analysis": {"secret_scanning": {"status": "enabled"}}},
        "endpoint": f"repos/{REPOSITORY}",
        "id": action_id,
        "method": "PATCH",
        "side_effects": [],
        "verify_controls": [control],
    }


def plan(actions, repository=REPOSITORY):
    return {
        "actions": actions,
        "before_status": "drift",
        "repository": repository,
        "schema_version": 1,
        "status": "ready" if actions else "compliant",
        "target_branch": BRANCH,
    }


def report(**statuses):
    return {
        "controls": [{"id": control, "status": status} for control, status in statuses.items()],
        "repository": REPOSITORY,
        "schema_version": 1,
        "status": "compliant" if set(statuses.values()) == {"compliant"} else "drift",
    }


def runner(returncode=0, stderr=""):
    completed = subprocess.CompletedProcess([], returncode, stdout="{}", stderr=stderr)
    return mock.Mock(return_value=completed)


def execute(monkeypatch, plans, reports, *, run=None, discover=None, confirmed=REPOSITORY):
    monkeypatch.setattr(governance, "build_apply_actions", mock.Mock(side_effect=plans))
    monkeypatch.setattr(governance, "compare_governance", mock.Mock(side_effect=reports))
    return governance.execute_apply(
        {},
        {},
        confirmed,
        runner=run or runner(),
        discoverer=discover or mock.Mock(return_value={}),
    )


def test_actions_refresh_and_verify_one_at_a_time_without_mutating_inputs(monkeypatch) -> None:
    first = action()
    second = action("repository.delete_branch_on_merge", "repository.delete_branch_on_merge")
    second["body"] = {"delete_branch_on_merge": True}
    refreshed = copy.deepcopy(second)
    refreshed["body"] = {"delete_branch_on_merge": False}
    plans = [plan([first, second]), plan([first, second]), plan([refreshed]), plan([])]
    reports = [
        report(**{"security.secret_scanning": "drift", second["id"]: "drift"}),
        report(**{"security.secret_scanning": "compliant", second["id"]: "drift"}),
        report(**{"security.secret_scanning": "compliant", second["id"]: "compliant"}),
    ]
    policy, inventory = {"policy": True}, {"inventory": True}
    before = copy.deepcopy((policy, inventory))
    run, discover = runner(), mock.Mock(side_effect=[{}, {}, {}])
    monkeypatch.setattr(governance, "build_apply_actions", mock.Mock(side_effect=plans))
    monkeypatch.setattr(governance, "compare_governance", mock.Mock(side_effect=reports))

    result = governance.execute_apply(
        policy, inventory, REPOSITORY, runner=run, discoverer=discover
    )

    assert result["attempted_actions"] == result["verified_actions"] == [first["id"], second["id"]]
    assert (policy, inventory) == before
    assert (run.call_count, discover.call_count) == (2, 3)
    assert run.call_args_list[1].kwargs["input"] == '{"delete_branch_on_merge":false}'


@pytest.mark.parametrize("case", ["confirmation", "stale", "changed_target"])
def test_preflight_blocks_or_discards_untrusted_stale_plans(monkeypatch, case) -> None:
    current = plan([action()])
    fresh = plan([]) if case == "stale" else plan([action()])
    if case == "changed_target":
        fresh = plan([action()], "acme/other")
    run, discover = mock.Mock(), mock.Mock(return_value={})
    monkeypatch.setattr(
        governance,
        "build_apply_actions",
        mock.Mock(side_effect=[current, fresh] if case != "confirmation" else [current]),
    )
    monkeypatch.setattr(
        governance,
        "compare_governance",
        mock.Mock(return_value=report(**{"security.secret_scanning": "compliant"})),
    )

    if case == "stale":
        result = governance.execute_apply({}, {}, REPOSITORY, runner=run, discoverer=discover)
        assert result["attempted_actions"] == []
    else:
        confirmed = "acme/other" if case == "confirmation" else REPOSITORY
        with pytest.raises(governance.PolicyError):
            governance.execute_apply({}, {}, confirmed, runner=run, discoverer=discover)
    run.assert_not_called()


def test_preflight_discovery_failure_performs_zero_writes(monkeypatch) -> None:
    current, run = plan([action()]), mock.Mock()
    monkeypatch.setattr(governance, "build_apply_actions", mock.Mock(return_value=current))

    with pytest.raises(governance.PolicyError, match="discovery failed"):
        governance.execute_apply(
            {},
            {},
            REPOSITORY,
            runner=run,
            discoverer=mock.Mock(side_effect=governance.PolicyError("secret")),
        )

    run.assert_not_called()


def test_write_failure_returns_redacted_partial_evidence(monkeypatch) -> None:
    current, run = plan([action()]), runner(1, "token ghp_sensitive")
    with pytest.raises(governance.ApplyFailure) as failure:
        execute(
            monkeypatch,
            [current, current],
            [report(**{"security.secret_scanning": "drift"})],
            run=run,
        )
    assert failure.value.evidence["failure_phase"] == "write"
    assert failure.value.evidence["attempted_actions"] == ["security.secret_scanning"]
    assert "ghp_sensitive" not in f"{failure.value}{failure.value.evidence}"
    assert run.call_count == 1


@pytest.mark.parametrize(
    "phase",
    ["read_back", "comparison", "verification", "replanning", "changed_target", "final_audit"],
)
def test_post_write_failures_stop_in_the_exact_phase(monkeypatch, phase) -> None:
    current, run = plan([action()]), runner()
    discover = mock.Mock(side_effect=[{}, governance.PolicyError("ghp_sensitive")])
    reports = [report(**{"security.secret_scanning": "drift"})]
    plans = [current, current]
    if phase != "read_back":
        discover.side_effect = [{}, {}]
        reports.append(
            governance.PolicyError("ghp_sensitive")
            if phase == "comparison"
            else report(
                **{"security.secret_scanning": "drift" if phase == "verification" else "compliant"}
            )
        )
    if phase == "replanning":
        plans.append(governance.PolicyError("ghp_sensitive"))
    elif phase == "changed_target":
        plans.append(plan([], "acme/other"))
    elif phase == "final_audit":
        reports[-1] = report(
            **{"security.secret_scanning": "compliant", "repository.other": "drift"}
        )
        plans.append(plan([]))

    with pytest.raises(governance.ApplyFailure) as failure:
        execute(monkeypatch, plans, reports, run=run, discover=discover)

    expected = (
        "verification"
        if phase in {"comparison", "verification", "final_audit"}
        else "replanning"
        if phase == "changed_target"
        else phase
    )
    assert failure.value.evidence["failure_phase"] == expected
    assert "ghp_sensitive" not in f"{failure.value}{failure.value.evidence}"
    assert run.call_count == 1


def test_replanned_action_is_never_retried(monkeypatch) -> None:
    current, run = plan([action()]), runner()
    with pytest.raises(governance.ApplyFailure) as failure:
        execute(
            monkeypatch,
            [current, current, current],
            [
                report(**{"security.secret_scanning": "drift"}),
                report(**{"security.secret_scanning": "compliant"}),
            ],
            run=run,
        )
    assert failure.value.evidence["failure_phase"] == "replanning"
    assert run.call_count == 1
