#!/usr/bin/env python3
"""Validate and resolve layered GitHub governance policy (ADR-0008)."""

import argparse
import copy
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

SCHEMA_VERSION = 1
MANAGER = "ai-dev-foundation"
API_VERSION = "2026-03-10"
UNKNOWN = "unknown"
MANAGED_RULESET_NAME = "ai-dev-foundation: branch-governance"
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
REPOSITORY_TARGET = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
BRANCH_CONTROL_IDS = {
    "admin": "branch.admin_bypass_allowed",
    "backend": "branch.enforcement_backend",
    "checks": "branch.required_status_checks",
    "force": "branch.force_pushes_allowed",
    "pull": "branch.pull_request",
}


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


def _gh_get_json(endpoint, runner, *, optional=False, paginate=False, collection_key=None):
    command = [
        "gh",
        "api",
        "--method",
        "GET",
        "-H",
        "Accept: application/vnd.github+json",
        "-H",
        f"X-GitHub-Api-Version: {API_VERSION}",
    ]
    if paginate:
        command.extend(("--paginate", "--slurp"))
    command.append(endpoint)
    try:
        result = runner(command, capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.SubprocessError) as error:
        raise PolicyError(f"GitHub GET could not run for {endpoint}: {error}") from error
    if result.returncode != 0:
        if optional:
            return None
        raise PolicyError(
            f"GitHub GET failed for {endpoint}; verify gh authentication and repository read access"
        )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise PolicyError(f"GitHub GET returned invalid JSON for {endpoint}") from error
    if paginate:
        if collection_key:
            if type(payload) is not list or any(
                type(page) is not dict or type(page.get(collection_key)) is not list
                for page in payload
            ):
                raise PolicyError(
                    f"GitHub GET returned an invalid paginated response for {endpoint}"
                )
            return [item for page in payload for item in page[collection_key]]
        if type(payload) is not list or any(type(page) is not list for page in payload):
            raise PolicyError(f"GitHub GET returned an invalid paginated response for {endpoint}")
        return [item for page in payload for item in page]
    return payload


def _known(value, expected_type):
    return value if type(value) is expected_type else UNKNOWN


def _security_inventory(repository):
    security = repository.get("security_and_analysis")

    def status(name):
        feature = security.get(name) if type(security) is dict else None
        value = feature.get("status") if type(feature) is dict else None
        return value if value in {"enabled", "disabled"} else UNKNOWN

    return {
        "dependabot_security_updates": status("dependabot_security_updates"),
        "push_protection": status("secret_scanning_push_protection"),
        "secret_scanning": status("secret_scanning"),
    }


def _observed_checks(repository, branch, runner):
    commit = branch.get("commit")
    sha = commit.get("sha") if type(commit) is dict else None
    if type(sha) is not str or not re.fullmatch(r"[0-9a-fA-F]{40,64}", sha):
        raise PolicyError("GitHub branch response is missing a valid commit SHA")
    runs = _gh_get_json(
        f"repos/{repository}/commits/{sha}/check-runs?per_page=100",
        runner,
        paginate=True,
        collection_key="check_runs",
    )
    statuses = _gh_get_json(
        f"repos/{repository}/commits/{sha}/statuses?per_page=100",
        runner,
        paginate=True,
    )
    if any(type(run) is not dict or type(run.get("name")) is not str for run in runs):
        raise PolicyError("GitHub check-runs response contains an invalid check name")
    if any(
        type(status) is not dict or type(status.get("context")) is not str for status in statuses
    ):
        raise PolicyError("GitHub statuses response contains an invalid context")
    return sorted({run["name"] for run in runs} | {status["context"] for status in statuses})


def _safe_rule_parameters(rule):
    parameters = rule.get("parameters")
    if type(parameters) is not dict:
        return {}
    if rule["type"] == "pull_request":
        return {
            "required_approving_review_count": _known(
                parameters.get("required_approving_review_count"), int
            ),
            "require_last_push_approval": _known(
                parameters.get("require_last_push_approval"), bool
            ),
        }
    if rule["type"] == "required_status_checks":
        checks = parameters.get("required_status_checks")
        contexts = (
            sorted(check["context"] for check in checks)
            if type(checks) is list
            and all(type(check) is dict and type(check.get("context")) is str for check in checks)
            else UNKNOWN
        )
        return {
            "contexts": contexts,
            "strict": _known(parameters.get("strict_required_status_checks_policy"), bool),
        }
    return {}


def _normalize_rules(rules):
    normalized = []
    for rule in rules:
        if type(rule) is not dict or type(rule.get("type")) is not str:
            raise PolicyError("GitHub effective rules response has an invalid rule")
        normalized.append(
            {
                "parameters": _safe_rule_parameters(rule),
                "ruleset_id": _known(rule.get("ruleset_id"), int),
                "source": _known(rule.get("ruleset_source"), str),
                "source_type": _known(rule.get("ruleset_source_type"), str),
                "type": rule["type"],
            }
        )
    return sorted(normalized, key=lambda rule: json.dumps(rule, sort_keys=True))


def _ruleset_endpoint(source_type, source, ruleset_id):
    if source_type == "Repository" and REPOSITORY_TARGET.fullmatch(str(source)):
        return f"repos/{source}/rulesets/{ruleset_id}"
    if source_type == "Organization" and re.fullmatch(r"[A-Za-z0-9_.-]+", str(source)):
        return f"orgs/{quote(source, safe='')}/rulesets/{ruleset_id}"
    return None


def _discover_rulesets(rules, runner):
    references = {
        (rule["source_type"], rule["source"], rule["ruleset_id"])
        for rule in rules
        if type(rule["ruleset_id"]) is int
    }
    inventory = []
    for source_type, source, ruleset_id in sorted(references, key=lambda item: str(item)):
        endpoint = _ruleset_endpoint(source_type, source, ruleset_id)
        detail = _gh_get_json(endpoint, runner, optional=True) if endpoint else None
        if detail is not None and type(detail) is not dict:
            raise PolicyError(f"GitHub ruleset {ruleset_id} response must be an object")
        actors = detail.get("bypass_actors") if detail else None
        inventory.append(
            {
                "has_bypass_actors": bool(actors) if type(actors) is list else UNKNOWN,
                "id": ruleset_id,
                "name": _known(detail.get("name"), str) if detail else UNKNOWN,
                "source": source,
                "source_type": source_type,
            }
        )
    return inventory


def _legacy_inventory(protected, protection):
    if not protected:
        return {"status": "absent"}
    if protection is None:
        return {"status": UNKNOWN}
    if type(protection) is not dict:
        raise PolicyError("GitHub branch protection response must be an object")

    def enabled(name):
        value = protection.get(name)
        return _known(value.get("enabled"), bool) if type(value) is dict else UNKNOWN

    checks = protection.get("required_status_checks")
    reviews = protection.get("required_pull_request_reviews")
    contexts = checks.get("contexts") if type(checks) is dict else None
    return {
        "allow_force_pushes": enabled("allow_force_pushes"),
        "enforce_admins": enabled("enforce_admins"),
        "required_pull_request_reviews": (
            {
                "require_last_push_approval": _known(
                    reviews.get("require_last_push_approval"), bool
                ),
                "required_approvals": _known(reviews.get("required_approving_review_count"), int),
            }
            if type(reviews) is dict
            else None
        ),
        "required_status_checks": (
            {
                "contexts": (
                    sorted(contexts)
                    if type(contexts) is list and all(type(context) is str for context in contexts)
                    else UNKNOWN
                ),
                "strict": _known(checks.get("strict"), bool),
            }
            if type(checks) is dict
            else None
        ),
        "status": "configured",
    }


def discover_github(repository, branch, runner=None):
    """Read and redact GitHub governance state without making write requests."""
    if (
        type(repository) is not str
        or not REPOSITORY_TARGET.fullmatch(repository)
        or any(part in {".", ".."} for part in repository.split("/"))
    ):
        raise PolicyError("repository target must use OWNER/REPOSITORY format")
    _validate_branch_name(branch, "target branch")
    runner = runner or subprocess.run
    branch_path = quote(branch, safe="")
    repository_data = _gh_get_json(f"repos/{repository}", runner)
    branch_data = _gh_get_json(f"repos/{repository}/branches/{branch_path}", runner)
    rules_data = _gh_get_json(
        f"repos/{repository}/rules/branches/{branch_path}?per_page=100",
        runner,
        paginate=True,
    )
    if type(repository_data) is not dict or type(branch_data) is not dict:
        raise PolicyError("GitHub repository and branch responses must be objects")
    protected = branch_data.get("protected")
    if type(protected) is not bool:
        raise PolicyError("GitHub branch response is missing the protected boolean")
    rules = _normalize_rules(rules_data)
    protection = (
        _gh_get_json(f"repos/{repository}/branches/{branch_path}/protection", runner, optional=True)
        if protected
        else None
    )
    return {
        "api_version": API_VERSION,
        "branch": {"name": branch, "protected": protected},
        "effective_rules": rules,
        "legacy_branch_protection": _legacy_inventory(protected, protection),
        "observed_checks": _observed_checks(repository, branch_data, runner),
        "repository": {
            "default_branch": _known(repository_data.get("default_branch"), str),
            "delete_branch_on_merge": _known(repository_data.get("delete_branch_on_merge"), bool),
            "full_name": repository,
        },
        "rulesets": _discover_rulesets(rules, runner),
        "security": _security_inventory(repository_data),
    }


def _has_unknown(value):
    if value == UNKNOWN:
        return True
    return type(value) is dict and any(_has_unknown(item) for item in value.values())


def _control(control_id, current, desired, rule_refs=()):
    status = UNKNOWN if _has_unknown(current) else "compliant" if current == desired else "drift"
    return {
        "current": current,
        "desired": desired,
        "id": control_id,
        "rule_refs": sorted(rule_refs),
        "status": status,
    }


def _single_rule(rules, rule_type):
    matches = [rule for rule in rules if rule["type"] == rule_type]
    if len(matches) > 1:
        raise PolicyError(f"managed ruleset contains multiple {rule_type} rules")
    return matches[0] if matches else None


def _branch_desired(policy):
    settings = policy["settings"]
    minimums = policy["minimums"]
    return {
        "admin": (False, minimums["admin_bypass_allowed"]["rule_refs"]),
        "backend": (settings["enforcement_backend"], ()),
        "force": (False, minimums["force_pushes_allowed"]["rule_refs"]),
        "pull": (
            {
                "require_last_push_approval": settings["require_last_push_approval"],
                "required_approvals": settings["required_approvals"],
            },
            minimums["pull_request_required"]["rule_refs"],
        ),
        "checks": (
            sorted(settings["required_checks"]),
            minimums["status_checks_required"]["rule_refs"],
        ),
    }


def _ruleset_branch_controls(policy, inventory):
    desired = _branch_desired(policy)
    matches = [
        ruleset for ruleset in inventory["rulesets"] if ruleset["name"] == MANAGED_RULESET_NAME
    ]
    if len(matches) > 1:
        raise PolicyError(f"multiple active rulesets use managed name {MANAGED_RULESET_NAME}")
    uncertain = any(ruleset["name"] == UNKNOWN for ruleset in inventory["rulesets"])
    uncertain = uncertain or any(
        rule["ruleset_id"] == UNKNOWN for rule in inventory["effective_rules"]
    )
    if not matches:
        current = UNKNOWN if uncertain else None
        values = {name: current for name in desired}
        managed_id = None
    else:
        managed = matches[0]
        managed_id = managed["id"]
        rules = [rule for rule in inventory["effective_rules"] if rule["ruleset_id"] == managed_id]
        pull = _single_rule(rules, "pull_request")
        checks = _single_rule(rules, "required_status_checks")
        no_force = _single_rule(rules, "non_fast_forward")
        values = {
            "admin": managed["has_bypass_actors"],
            "backend": "ruleset",
            "checks": checks["parameters"].get("contexts", UNKNOWN) if checks else None,
            "force": not no_force,
            "pull": (
                {
                    "require_last_push_approval": pull["parameters"].get(
                        "require_last_push_approval", UNKNOWN
                    ),
                    "required_approvals": pull["parameters"].get(
                        "required_approving_review_count", UNKNOWN
                    ),
                }
                if pull
                else None
            ),
        }
    controls = [
        _control(BRANCH_CONTROL_IDS[name], values[name], *desired[name]) for name in desired
    ]
    unmanaged = [rule for rule in inventory["effective_rules"] if rule["ruleset_id"] != managed_id]
    legacy = inventory["legacy_branch_protection"]
    return controls, unmanaged, None if legacy["status"] == "absent" else legacy


def _legacy_branch_controls(policy, inventory):
    desired = _branch_desired(policy)
    legacy = inventory["legacy_branch_protection"]
    if legacy["status"] != "configured":
        current = UNKNOWN if legacy["status"] == UNKNOWN else None
        values = {name: current for name in desired}
    else:
        reviews = legacy["required_pull_request_reviews"]
        checks = legacy["required_status_checks"]
        enforce_admins = legacy["enforce_admins"]
        values = {
            "admin": UNKNOWN if enforce_admins == UNKNOWN else not enforce_admins,
            "backend": "legacy_branch_protection",
            "checks": checks["contexts"] if checks else None,
            "force": legacy["allow_force_pushes"],
            "pull": reviews,
        }
    controls = [
        _control(BRANCH_CONTROL_IDS[name], values[name], *desired[name]) for name in desired
    ]
    return controls, inventory["effective_rules"], None


def compare_governance(policy, inventory):
    """Return a deterministic, redacted current-versus-desired governance report."""
    required = {
        "branch",
        "effective_rules",
        "legacy_branch_protection",
        "observed_checks",
        "repository",
        "rulesets",
        "security",
    }
    if type(inventory) is not dict or not required <= set(inventory):
        raise PolicyError("GitHub inventory is missing required governance fields")
    settings = policy["settings"]
    if inventory["branch"].get("name") != settings["target_branch"]:
        raise PolicyError("GitHub inventory branch does not match resolved target_branch")
    if settings["enforcement_backend"] == "ruleset":
        controls, unmanaged_rules, unmanaged_legacy = _ruleset_branch_controls(policy, inventory)
    else:
        controls, unmanaged_rules, unmanaged_legacy = _legacy_branch_controls(policy, inventory)
    minimums = policy["minimums"]
    security = inventory["security"]
    observed_checks = inventory["observed_checks"]
    if type(observed_checks) is not list or any(
        type(check) is not str for check in observed_checks
    ):
        raise PolicyError("GitHub inventory observed_checks must be a list of names")
    required_checks = sorted(settings["required_checks"])
    controls.extend(
        [
            _control(
                "branch.required_status_checks_observed",
                sorted(set(required_checks) & set(observed_checks)),
                required_checks,
                minimums["status_checks_required"]["rule_refs"],
            ),
            _control(
                "repository.delete_branch_on_merge",
                inventory["repository"].get("delete_branch_on_merge", UNKNOWN),
                settings["delete_branch_on_merge"],
            ),
            _control(
                "security.dependabot_security_updates",
                security.get("dependabot_security_updates", UNKNOWN),
                "enabled" if settings["dependency_update_provider"] == "dependabot" else "disabled",
            ),
            _control(
                "security.push_protection",
                security.get("push_protection", UNKNOWN),
                "enabled",
                minimums["push_protection_enabled"]["rule_refs"],
            ),
            _control(
                "security.secret_scanning",
                security.get("secret_scanning", UNKNOWN),
                "enabled",
                minimums["secret_scanning_enabled"]["rule_refs"],
            ),
        ]
    )
    statuses = {control["status"] for control in controls}
    if unmanaged_legacy and unmanaged_legacy["status"] == UNKNOWN:
        statuses.add(UNKNOWN)
    status = UNKNOWN if UNKNOWN in statuses else "drift" if "drift" in statuses else "compliant"
    return {
        "branch": settings["target_branch"],
        "controls": sorted(controls, key=lambda control: control["id"]),
        "managed_ruleset_name": MANAGED_RULESET_NAME,
        "repository": inventory["repository"].get("full_name", UNKNOWN),
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "unmanaged": {
            "effective_rules": sorted(
                unmanaged_rules, key=lambda rule: json.dumps(rule, sort_keys=True)
            ),
            "legacy_branch_protection": unmanaged_legacy,
        },
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
    parser.add_argument("command", choices=("validate", "plan", "audit"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--foundation", type=Path)
    parser.add_argument("--repository", type=Path)
    parser.add_argument("--repo", help="GitHub repository in OWNER/REPOSITORY form")
    args = parser.parse_args(argv)
    if args.command in {"plan", "audit"} and not args.repo:
        parser.error("--repo is required for plan and audit")
    root = args.root.resolve()
    foundation = args.foundation or root / ".github/governance/foundation.json"
    repository = args.repository or root / ".github/governance/repository.json"
    try:
        resolved = resolve_policy(
            _load_json(foundation),
            _load_json(repository),
            _known_rule_ids(root),
        )
        if args.command == "validate":
            report = resolved
        else:
            inventory = discover_github(
                args.repo,
                resolved["settings"]["target_branch"],
            )
            report = compare_governance(resolved, inventory)
    except PolicyError as error:
        print(f"governance policy error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if args.command == "audit" and report["status"] != "compliant" else 0


if __name__ == "__main__":
    raise SystemExit(main())
