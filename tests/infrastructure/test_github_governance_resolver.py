import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
MODULE_PATH = ROOT / "scripts/github_governance.py"
GOVERNANCE = ROOT / ".github/governance"
KNOWN_RULES = {"GR-010", "GR-011", "GR-012", "SEC-002", "SEC-003", "WF-030"}


@pytest.fixture(scope="module")
def resolver():
    spec = importlib.util.spec_from_file_location("github_governance_resolver", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def policy(name: str) -> dict:
    return json.loads((GOVERNANCE / name).read_text(encoding="utf-8"))


def resolve(resolver, foundation=None, repository=None):
    return resolver.resolve_policy(
        foundation or policy("foundation.json"),
        repository or policy("repository.json"),
        KNOWN_RULES,
    )


def test_repository_policy_resolves_deterministically(resolver) -> None:
    result = resolve(resolver)

    assert result["schema_version"] == 1
    assert result["managed_by"] == "ai-dev-foundation"
    assert result["settings"] == {
        "target_branch": "main",
        "enforcement_backend": "ruleset",
        "required_approvals": 0,
        "require_last_push_approval": False,
        "required_checks": [
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
        ],
        "dependency_update_provider": "renovate",
        "delete_branch_on_merge": True,
        "discussions_enabled": False,
        "squash_merge_commit_title": "PR_TITLE",
        "squash_merge_commit_message": "PR_BODY",
    }


def test_foundation_requires_vulnerability_intake_minimums(resolver) -> None:
    minimums = resolve(resolver)["minimums"]

    assert minimums["vulnerability_alerts_enabled"] == {
        "value": True,
        "rule_refs": ["SEC-003"],
    }
    assert minimums["private_vulnerability_reporting_enabled"] == {
        "value": True,
        "rule_refs": ["SEC-003"],
    }
    assert minimums["squash_merge_only"] == {
        "value": True,
        "rule_refs": ["WF-030"],
    }


def test_repository_may_add_but_not_remove_foundation_checks(resolver) -> None:
    foundation = policy("foundation.json")
    foundation_checks = foundation["defaults"]["required_checks"]
    additive = {"schema_version": 1, "overrides": {"required_checks": [*foundation_checks, "x"]}}

    assert resolve(resolver, foundation, additive)["settings"]["required_checks"][-1] == "x"

    with pytest.raises(resolver.PolicyError, match="cannot remove foundation checks"):
        resolve(
            resolver,
            foundation,
            {"schema_version": 1, "overrides": {"required_checks": foundation_checks[1:]}},
        )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.update(schema_version=2),
        lambda value: value.update(managed_by="downstream"),
        lambda value: value.update(extra=True),
        lambda value: value.pop("defaults"),
        lambda value: value["minimums"]["force_pushes_allowed"].update(value=True),
        lambda value: value["minimums"]["pull_request_required"].update(rule_refs=[]),
        lambda value: value["minimums"]["pull_request_required"].update(rule_refs=["GR-999"]),
        lambda value: value["minimums"]["pull_request_required"].update(rule_refs=["GR-011"]),
    ],
)
def test_foundation_contract_is_strict(resolver, mutate) -> None:
    foundation = copy.deepcopy(policy("foundation.json"))
    mutate(foundation)

    with pytest.raises(resolver.PolicyError):
        resolve(resolver, foundation=foundation)


@pytest.mark.parametrize(
    "overrides",
    [
        {"target_branch": "feature//main"},
        {"target_branch": "release/.hidden"},
        {"required_approvals": -1},
        {"required_approvals": True},
        {"enforcement_backend": "automatic"},
        {"enforcement_backend": ["ruleset"]},
        {"required_checks": []},
        {"required_checks": ["lint", "lint"]},
        {"required_checks": ["lint\ntest"]},
        {"required_checks": ["lint", ["test"]]},
        {"dependency_update_provider": ["renovate", "dependabot"]},
        {"discussions_enabled": "yes"},
        {"squash_merge_commit_title": "ISSUE_TITLE"},
        {"squash_merge_commit_message": "FULL_DIFF"},
        {"required_approvals": 0, "require_last_push_approval": True},
        {"unknown": True},
    ],
)
def test_invalid_repository_values_fail_closed(resolver, overrides) -> None:
    repository = copy.deepcopy(policy("repository.json"))
    repository["overrides"].update(overrides)

    with pytest.raises(resolver.PolicyError):
        resolve(resolver, repository=repository)


def test_validate_cli_prints_stable_json_without_network(resolver, capsys) -> None:
    assert resolver.main(["validate", "--root", str(ROOT)]) == 0

    captured = capsys.readouterr()
    assert json.loads(captured.out) == resolve(resolver)
    assert captured.err == ""


@pytest.mark.parametrize(
    ("contents", "message"),
    [
        ('{"schema_version": 1, "schema_version": 1}', "duplicate JSON field"),
        ("not-json", "cannot read policy"),
        (None, "cannot read policy"),
    ],
)
def test_validate_cli_reports_invalid_policy(resolver, tmp_path, capsys, contents, message) -> None:
    invalid = tmp_path / "invalid.json"
    if contents is not None:
        invalid.write_text(contents, encoding="utf-8")

    assert (
        resolver.main(
            [
                "validate",
                "--root",
                str(ROOT),
                "--foundation",
                str(invalid),
                "--repository",
                str(GOVERNANCE / "repository.json"),
            ]
        )
        == 2
    )
    assert message in capsys.readouterr().err
