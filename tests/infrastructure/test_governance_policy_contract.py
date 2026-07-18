import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).parents[2]
GOVERNANCE = ROOT / ".github/governance"
PARENT_FOUNDATION_BLOB = "923aaf46a5c7fff7328b215fa107f039eccb1082"
FOUNDATION_CHECKS = [
    "lint",
    "test",
    "build",
    "doctor",
    "link-check",
    "pr-quality",
    "secret-scan",
    "dependency-scan",
    "license-check",
]
MINIMUMS = {
    "pull_request_required": (True, ["GR-010"]),
    "status_checks_required": (True, ["GR-012"]),
    "force_pushes_allowed": (False, ["GR-011"]),
    "admin_bypass_allowed": (False, ["GR-010", "GR-012"]),
    "squash_merge_only": (True, ["WF-030"]),
    "secret_scanning_enabled": (True, ["SEC-002"]),
    "push_protection_enabled": (True, ["SEC-002"]),
    "vulnerability_alerts_enabled": (True, ["SEC-003"]),
    "private_vulnerability_reporting_enabled": (True, ["SEC-003"]),
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def known_rule_ids() -> set[str]:
    pattern = re.compile(r"^#{2,3} ((?:GR|SEC|WF)-\d{3}):", re.MULTILINE)
    return {
        rule_id
        for path in sorted((ROOT / ".ai").glob("*.md"))
        for rule_id in pattern.findall(path.read_text(encoding="utf-8"))
    }


def test_foundation_policy_matches_the_accepted_parent_contract() -> None:
    contents = (GOVERNANCE / "foundation.json").read_bytes()
    blob = b"blob " + str(len(contents)).encode() + b"\0" + contents
    foundation = json.loads(contents)

    assert hashlib.sha1(blob, usedforsecurity=False).hexdigest() == PARENT_FOUNDATION_BLOB
    assert foundation["schema_version"] == 1
    assert foundation["managed_by"] == "ai-dev-foundation"
    assert {
        name: (control["value"], control["rule_refs"])
        for name, control in foundation["minimums"].items()
    } == MINIMUMS
    assert foundation["defaults"] == {
        "target_branch": "main",
        "enforcement_backend": "ruleset",
        "required_approvals": 0,
        "require_last_push_approval": False,
        "required_checks": FOUNDATION_CHECKS,
        "dependency_update_provider": "renovate",
        "delete_branch_on_merge": True,
        "discussions_enabled": False,
        "squash_merge_commit_title": "PR_TITLE",
        "squash_merge_commit_message": "PR_BODY",
    }
    assert {
        rule_id for control in foundation["minimums"].values() for rule_id in control["rule_refs"]
    } <= known_rule_ids()


def test_terraform_profile_owns_the_proven_iac_context() -> None:
    repository = load(GOVERNANCE / "repository.json")
    profile = load(GOVERNANCE / "profiles/terraform-gcp.json")
    overrides = repository["overrides"]

    assert repository["schema_version"] == 1
    assert profile == {
        "schema_version": 1,
        "id": "terraform-gcp",
        "parent": "ai-dev-foundation",
        "required_checks": ["iac-scan"],
    }
    assert overrides["required_approvals"] == 0
    assert overrides["require_last_push_approval"] is False
    assert "required_checks" not in overrides
    assert overrides["delete_branch_on_merge"] is True


def test_governance_policy_ownership_is_disjoint() -> None:
    manifest = load(ROOT / ".github/inheritance/manifest.json")

    assert ".github/governance/foundation.json" in manifest["inherited_paths"]
    assert ".github/governance/profiles/" in manifest["inherited_paths"]
    assert ".github/governance/repository.json" in manifest["protected_paths"]
    assert not set(manifest["inherited_paths"]) & set(manifest["protected_paths"])
