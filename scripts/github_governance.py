#!/usr/bin/env python3
"""Validate and resolve layered GitHub governance policy (ADR-0008)."""

import argparse
import copy
import json
import re
import sys
from pathlib import Path

SCHEMA_VERSION = 1
MANAGER = "ai-dev-foundation"
MINIMUM_CONTRACT = {
    "pull_request_required": (True, {"GR-010"}),
    "status_checks_required": (True, {"GR-012"}),
    "force_pushes_allowed": (False, {"GR-011"}),
    "admin_bypass_allowed": (False, {"GR-010", "GR-012"}),
    "secret_scanning_enabled": (True, {"SEC-002"}),
    "push_protection_enabled": (True, {"SEC-002"}),
}
SETTING_FIELDS = {
    "target_branch",
    "enforcement_backend",
    "required_approvals",
    "require_last_push_approval",
    "required_checks",
    "dependency_update_provider",
    "delete_branch_on_merge",
}
RULE_ID = re.compile(r"^(?:GR|SEC)-\d{3}$")
RULE_HEADING = re.compile(r"^### ((?:GR|SEC)-\d{3}):", re.MULTILINE)


class PolicyError(ValueError):
    """Raised when policy cannot safely be resolved."""


def _object(value, fields, label, *, partial=False):
    if type(value) is not dict:
        raise PolicyError(f"{label} must be an object")
    unknown = sorted(set(value) - fields)
    missing = [] if partial else sorted(fields - set(value))
    if unknown or missing:
        details = []
        if unknown:
            details.append(f"unknown fields: {', '.join(unknown)}")
        if missing:
            details.append(f"missing fields: {', '.join(missing)}")
        raise PolicyError(f"{label} has {'; '.join(details)}")


def _schema_version(policy, label):
    if type(policy["schema_version"]) is not int or policy["schema_version"] != SCHEMA_VERSION:
        raise PolicyError(f"{label}.schema_version must be {SCHEMA_VERSION}")


def _validate_rule_refs(refs, known_rule_ids, label):
    if type(refs) is not list or not refs or any(type(ref) is not str for ref in refs):
        raise PolicyError(f"{label}.rule_refs must be a non-empty unique list")
    if len(refs) != len(set(refs)):
        raise PolicyError(f"{label}.rule_refs must be a non-empty unique list")
    invalid = [ref for ref in refs if not RULE_ID.fullmatch(ref)]
    unknown = sorted(set(refs) - known_rule_ids) if not invalid else []
    if invalid or unknown:
        raise PolicyError(
            f"{label}.rule_refs contains invalid or unknown IDs: {invalid or unknown}"
        )


def _validate_branch_name(branch, label):
    if (
        type(branch) is not str
        or not branch
        or branch != branch.strip()
        or len(branch) > 255
        or branch in {"@", ".", ".."}
        or branch.startswith(("-", "/", "."))
        or branch.endswith(("/", ".", ".lock"))
        or "//" in branch
        or ".." in branch
        or "@{" in branch
        or any(part.startswith(".") or part.endswith(".lock") for part in branch.split("/"))
        or any(ord(char) < 32 or ord(char) == 127 or char in " ~^:?*[\\" for char in branch)
    ):
        raise PolicyError(f"{label} is not a safe branch name")


def _validate_required_checks(checks, label):
    if type(checks) is not list or not checks or any(type(check) is not str for check in checks):
        raise PolicyError(f"{label}.required_checks must be a non-empty unique list")
    if len(checks) != len(set(checks)):
        raise PolicyError(f"{label}.required_checks must be a non-empty unique list")
    if any(
        not check.strip()
        or check != check.strip()
        or any(ord(char) < 32 or ord(char) == 127 for char in check)
        for check in checks
    ):
        raise PolicyError(f"{label}.required_checks contains an invalid check name")


def _validate_settings(settings, label):
    _object(settings, SETTING_FIELDS, label)
    _validate_branch_name(settings["target_branch"], f"{label}.target_branch")
    backend = settings["enforcement_backend"]
    if type(backend) is not str or backend not in {"ruleset", "legacy_branch_protection"}:
        raise PolicyError(f"{label}.enforcement_backend is unsupported")
    approvals = settings["required_approvals"]
    if type(approvals) is not int or not 0 <= approvals <= 6:
        raise PolicyError(f"{label}.required_approvals must be an integer from 0 to 6")
    for field in ("require_last_push_approval", "delete_branch_on_merge"):
        if type(settings[field]) is not bool:
            raise PolicyError(f"{label}.{field} must be a boolean")
    if approvals == 0 and settings["require_last_push_approval"]:
        raise PolicyError(f"{label}.require_last_push_approval needs at least one approval")
    _validate_required_checks(settings["required_checks"], label)
    provider = settings["dependency_update_provider"]
    if type(provider) is not str or provider not in {"renovate", "dependabot"}:
        raise PolicyError(f"{label}.dependency_update_provider must select exactly one provider")


def _validate_foundation(foundation, known_rule_ids):
    _object(foundation, {"schema_version", "managed_by", "minimums", "defaults"}, "foundation")
    _schema_version(foundation, "foundation")
    if foundation["managed_by"] != MANAGER:
        raise PolicyError(f"foundation.managed_by must be {MANAGER}")
    _object(foundation["minimums"], set(MINIMUM_CONTRACT), "foundation.minimums")
    for name, (required_value, required_refs) in MINIMUM_CONTRACT.items():
        control = foundation["minimums"][name]
        label = f"foundation.minimums.{name}"
        _object(control, {"value", "rule_refs"}, label)
        if type(control["value"]) is not bool or control["value"] is not required_value:
            raise PolicyError(f"{label}.value cannot weaken the foundation")
        _validate_rule_refs(control["rule_refs"], known_rule_ids, label)
        if set(control["rule_refs"]) != required_refs:
            raise PolicyError(f"{label}.rule_refs does not match its contract")
    _validate_settings(foundation["defaults"], "foundation.defaults")


def resolve_policy(foundation, repository, known_rule_ids):
    """Validate both layers and return their deterministic effective policy."""
    _validate_foundation(foundation, known_rule_ids)
    _object(repository, {"schema_version", "overrides"}, "repository")
    _schema_version(repository, "repository")
    _object(repository["overrides"], SETTING_FIELDS, "repository.overrides", partial=True)

    settings = copy.deepcopy(foundation["defaults"])
    settings.update(copy.deepcopy(repository["overrides"]))
    _validate_settings(settings, "resolved.settings")
    missing_checks = [
        check
        for check in foundation["defaults"]["required_checks"]
        if check not in settings["required_checks"]
    ]
    if missing_checks:
        raise PolicyError(
            "repository.overrides.required_checks cannot remove foundation checks: "
            + ", ".join(missing_checks)
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "managed_by": MANAGER,
        "minimums": copy.deepcopy(foundation["minimums"]),
        "settings": settings,
    }


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise PolicyError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def _load_json(path):
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle, object_pairs_hook=_reject_duplicate_keys)
    except (OSError, json.JSONDecodeError) as error:
        raise PolicyError(f"cannot read policy {path}: {error}") from error


def _known_rule_ids(root):
    try:
        return {
            rule_id
            for path in sorted((root / ".ai").glob("*.md"))
            for rule_id in RULE_HEADING.findall(path.read_text(encoding="utf-8"))
        }
    except OSError as error:
        raise PolicyError(f"cannot read rule definitions under {root / '.ai'}: {error}") from error


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate",))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--foundation", type=Path)
    parser.add_argument("--repository", type=Path)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    foundation = args.foundation or root / ".github/governance/foundation.json"
    repository = args.repository or root / ".github/governance/repository.json"
    try:
        resolved = resolve_policy(
            _load_json(foundation),
            _load_json(repository),
            _known_rule_ids(root),
        )
    except PolicyError as error:
        print(f"governance policy error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(resolved, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
