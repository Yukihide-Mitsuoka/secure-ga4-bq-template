#!/usr/bin/env python3
"""Validate, plan, and report local template inheritance defined by project ADR-0008."""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SCHEMA_VERSION = 1
SUPPORTED_MANIFEST_SCHEMA_VERSIONS = {1, 2}
AGENT_PROFILE_SCHEMA_VERSION = 1
MANIFEST_PATH = ".github/inheritance/manifest.json"
AGENT_PROFILE_PATH = ".github/inheritance/agent-profile.json"
TEMPLATE_SYNC_IGNORE_PATH = ".templatesyncignore"
MAX_CONTRACT_BYTES = 1_000_000
MAX_OWNERSHIP_ROOTS = 1_000
MAX_AGENT_INPUTS = 32
MAX_FLEET_REPOSITORIES = 32
MAX_AUDITED_INHERITED_FILES = 10_000
HASH_BATCH_SIZE = 256
MAX_FIRST_PARENT_COMMITS = 100_000
MAX_CHANGED_PATHS = 1_000
REPOSITORY_TARGET = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
COMMIT_ID = re.compile(r"^[0-9a-f]{40}$")
REQUIRED_PROTECTED_PATHS = {
    ".gitignore",
    ".github/governance/repository.json",
    ".github/inheritance/manifest.json",
    ".github/workflows/template-sync.yml",
    ".templatesyncignore",
}
REQUIRED_TEMPLATE_SYNC_IGNORES = {".github/workflows/"}


class InheritanceError(ValueError):
    pass


def _object(value, fields, label):
    if type(value) is not dict:
        raise InheritanceError(f"{label} must be an object")
    unknown = sorted(set(value) - fields)
    missing = sorted(fields - set(value))
    if unknown or missing:
        details = []
        if unknown:
            details.append(f"unknown fields: {', '.join(unknown)}")
        if missing:
            details.append(f"missing fields: {', '.join(missing)}")
        raise InheritanceError(f"{label} has {'; '.join(details)}")


def _repository(value, label):
    if type(value) is not str or not REPOSITORY_TARGET.fullmatch(value):
        raise InheritanceError(f"{label} must be OWNER/REPOSITORY")
    return value


def _ownership_root(value, label, *, file_only=False):
    if type(value) is not str or not value or value != value.strip() or len(value) > 1_024:
        raise InheritanceError(f"{label} must be a safe repository-relative ownership root")
    is_directory = value.endswith("/")
    body = value[:-1] if is_directory else value
    parts = body.split("/")
    if (
        not body
        or body.startswith("/")
        or (file_only and is_directory)
        or any(part in {"", ".", "..", ".git"} for part in parts)
        or any(char in "*?[]\\" or ord(char) < 32 or ord(char) == 127 for char in value)
    ):
        raise InheritanceError(f"{label} must be a safe repository-relative ownership root")
    return value


def _branch(value, label):
    try:
        _ownership_root(value, label, file_only=True)
    except InheritanceError as error:
        raise InheritanceError(f"{label} is not a safe branch name") from error
    if (
        len(value) > 255
        or value == "@"
        or value.startswith(("-", "."))
        or value.endswith((".", ".lock"))
        or ".." in value
        or "@{" in value
        or any(part.startswith(".") or part.endswith(".lock") for part in value.split("/"))
        or any(char in " ~^:" for char in value)
    ):
        raise InheritanceError(f"{label} is not a safe branch name")
    return value


def _ownership_roots(value, label):
    if type(value) is not list or not value or len(value) > MAX_OWNERSHIP_ROOTS:
        raise InheritanceError(f"{label} must be a non-empty unique list of ownership roots")
    roots = [_ownership_root(root, f"{label}[{index}]") for index, root in enumerate(value)]
    if len(roots) != len(set(roots)):
        raise InheritanceError(f"{label} must be a non-empty unique list of ownership roots")
    return roots


def _overlaps(left, right):
    return (
        left == right
        or (left.endswith("/") and right.startswith(left))
        or (right.endswith("/") and left.startswith(right))
    )


def _reject_overlaps(roots, label):
    for index, left in enumerate(roots):
        for right in roots[index + 1 :]:
            if _overlaps(left, right):
                raise InheritanceError(f"{label} ownership roots overlap: {left}, {right}")


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise InheritanceError(f"contract JSON contains duplicate key: {key}")
        value[key] = item
    return value


def _read_json(root, relative_path):
    candidate = root / relative_path
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as error:
        raise InheritanceError(
            f"{relative_path} must be a file inside the repository root"
        ) from error
    if resolved != candidate:
        raise InheritanceError(f"{relative_path} must not use a symlink")
    if not resolved.is_relative_to(root):
        raise InheritanceError(f"{relative_path} must be a file inside the repository root")
    if not resolved.is_file():
        raise InheritanceError(f"{relative_path} must be a file inside the repository root")
    try:
        if resolved.stat().st_size > MAX_CONTRACT_BYTES:
            raise InheritanceError(f"{relative_path} exceeds {MAX_CONTRACT_BYTES} bytes")
        return json.loads(resolved.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise InheritanceError(f"{relative_path} must contain valid UTF-8 JSON") from error


def _read_template_sync_ignore(root):
    candidate = root / TEMPLATE_SYNC_IGNORE_PATH
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as error:
        raise InheritanceError(
            f"{TEMPLATE_SYNC_IGNORE_PATH} must be a file inside the repository root"
        ) from error
    if resolved != candidate or not resolved.is_relative_to(root) or not resolved.is_file():
        raise InheritanceError(
            f"{TEMPLATE_SYNC_IGNORE_PATH} must be a non-symlink file inside the repository root"
        )
    try:
        if resolved.stat().st_size > MAX_CONTRACT_BYTES:
            raise InheritanceError(
                f"{TEMPLATE_SYNC_IGNORE_PATH} exceeds {MAX_CONTRACT_BYTES} bytes"
            )
        lines = resolved.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise InheritanceError(
            f"{TEMPLATE_SYNC_IGNORE_PATH} must contain valid UTF-8 text"
        ) from error

    positive = []
    exceptions = []
    for line_number, line in enumerate(lines, start=1):
        entry = line.strip()
        if not entry or entry.startswith("#"):
            continue
        destination = exceptions if entry.startswith(":!") else positive
        root_entry = entry[2:] if destination is exceptions else entry
        if root_entry.endswith("/**"):
            root_entry = root_entry[:-2]
        try:
            destination.append(
                _ownership_root(root_entry, f"{TEMPLATE_SYNC_IGNORE_PATH}:{line_number}")
            )
        except InheritanceError as error:
            raise InheritanceError(
                f"{TEMPLATE_SYNC_IGNORE_PATH}:{line_number} must be a literal path, "
                "directory, directory/**, or :! exception"
            ) from error
    return positive, exceptions


def _covers(outer, inner):
    return outer == inner or (outer.endswith("/") and inner.startswith(outer))


def _owned_by(path, roots):
    return any(root == path or (root.endswith("/") and path.startswith(root)) for root in roots)


def _require_regular_file(root, relative_path, label):
    candidate = root / relative_path
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as error:
        raise InheritanceError(f"{label} must be a file inside the repository root") from error
    if resolved != candidate or not resolved.is_relative_to(root) or not resolved.is_file():
        raise InheritanceError(f"{label} must be a non-symlink file inside the repository root")


def _agent_profile_inputs(root, inputs):
    if type(inputs) is not list or not 2 <= len(inputs) <= MAX_AGENT_INPUTS:
        raise InheritanceError(
            f"agent profile.inputs must contain 2 to {MAX_AGENT_INPUTS} ordered inputs"
        )

    validated = []
    for index, item in enumerate(inputs):
        label = f"agent profile.inputs[{index}]"
        _object(item, {"layer", "repository", "path"}, label)
        layer = item["layer"]
        if layer not in {"foundation", "template", "project"}:
            raise InheritanceError(f"{label}.layer must be foundation, template, or project")
        repository = _repository(item["repository"], f"{label}.repository")
        path = _ownership_root(item["path"], f"{label}.path", file_only=True)
        _require_regular_file(root, path, f"{label}.path")
        validated.append({"layer": layer, "repository": repository, "path": path})
    return validated


def _validate_agent_input_order(inputs, parent_repository):
    layers = [item["layer"] for item in inputs]
    if (
        layers[0] != "foundation"
        or layers[-1] != "project"
        or layers.count("foundation") != 1
        or layers.count("project") != 1
        or any(layer != "template" for layer in layers[1:-1])
    ):
        raise InheritanceError(
            "agent profile inputs must use foundation, template..., project order"
        )
    if len({item["repository"].casefold() for item in inputs}) != len(inputs):
        raise InheritanceError("agent profile input repositories must be unique")
    if len({item["path"] for item in inputs}) != len(inputs):
        raise InheritanceError("agent profile input paths must be unique")

    templates = inputs[1:-1]
    foundation_repository = inputs[0]["repository"]
    if parent_repository.casefold() == foundation_repository.casefold():
        if templates:
            raise InheritanceError(
                "agent profile template order must be empty when foundation is the direct parent"
            )
    elif not templates or templates[-1]["repository"].casefold() != parent_repository.casefold():
        raise InheritanceError("agent profile final template input must match the direct parent")


def _validate_agent_input_ownership(inputs, inherited, protected):
    foundation = inputs[0]
    project = inputs[-1]

    if not foundation["path"].startswith(".ai/contracts/foundation/"):
        raise InheritanceError("foundation agent profile input must use .ai/contracts/foundation/")
    if not project["path"].startswith(".ai/project/"):
        raise InheritanceError("project agent profile input must use .ai/project/")

    for item in inputs[:-1]:
        if not _owned_by(item["path"], inherited):
            raise InheritanceError(f"agent profile {item['layer']} input must be inherited")
        if item["layer"] == "template":
            owner, repository = item["repository"].casefold().split("/", 1)
            expected_root = f".ai/contracts/templates/{owner}/{repository}/"
            if not item["path"].startswith(expected_root):
                raise InheritanceError(
                    f"template agent profile input must use owner-qualified root {expected_root}"
                )
    if not _owned_by(project["path"], protected):
        raise InheritanceError("agent profile project input must be protected")


def _validate_agent_profile(root, parent_repository, inherited, protected):
    if not _owned_by(AGENT_PROFILE_PATH, protected):
        raise InheritanceError(f"manifest.protected_paths must protect {AGENT_PROFILE_PATH}")
    profile = _read_json(root, AGENT_PROFILE_PATH)
    _object(
        profile,
        {"schema_version", "authority_policy", "inputs"},
        "agent profile",
    )
    if (
        type(profile["schema_version"]) is not int
        or profile["schema_version"] != AGENT_PROFILE_SCHEMA_VERSION
    ):
        raise InheritanceError(
            f"agent profile.schema_version must be {AGENT_PROFILE_SCHEMA_VERSION}"
        )
    if profile["authority_policy"] != "strengthen-only":
        raise InheritanceError("agent profile.authority_policy must be strengthen-only")
    inputs = _agent_profile_inputs(root, profile["inputs"])
    _validate_agent_input_order(inputs, parent_repository)
    _validate_agent_input_ownership(inputs, inherited, protected)

    return {
        "profile_file": AGENT_PROFILE_PATH,
        "authority_policy": "strengthen-only",
        "inputs": inputs,
    }


def _validate_template_sync_ignore(root, protected):
    positive, exceptions = _read_template_sync_ignore(root)
    required = sorted(set(protected) | REQUIRED_TEMPLATE_SYNC_IGNORES)
    missing = sorted(
        path for path in required if not any(_covers(entry, path) for entry in positive)
    )
    if missing:
        raise InheritanceError(f"template sync ignore is missing protected paths: {missing}")
    unsafe_exceptions = sorted(
        exception
        for exception in exceptions
        if any(_overlaps(exception, protected_root) for protected_root in required)
    )
    if unsafe_exceptions:
        raise InheritanceError(
            f"template sync exception re-includes protected paths: {unsafe_exceptions}"
        )
    return {
        "ignore_file": TEMPLATE_SYNC_IGNORE_PATH,
        "required": required,
    }


def validate_inheritance(root):
    """Validate manifest, lock, and exclusive path ownership without external I/O."""
    try:
        repository_root = Path(root).resolve(strict=True)
    except OSError as error:
        raise InheritanceError("repository root must exist") from error
    if not repository_root.is_dir():
        raise InheritanceError("repository root must be a directory")

    manifest = _read_json(repository_root, MANIFEST_PATH)
    _object(
        manifest,
        {"schema_version", "parent", "lock_file", "inherited_paths", "protected_paths"},
        "manifest",
    )
    manifest_version = manifest["schema_version"]
    if (
        type(manifest_version) is not int
        or manifest_version not in SUPPORTED_MANIFEST_SCHEMA_VERSIONS
    ):
        supported = ", ".join(
            str(version) for version in sorted(SUPPORTED_MANIFEST_SCHEMA_VERSIONS)
        )
        raise InheritanceError(f"manifest.schema_version must be one of: {supported}")
    _object(manifest["parent"], {"repository", "branch"}, "manifest.parent")
    parent_repository = _repository(manifest["parent"]["repository"], "manifest.parent.repository")
    parent_branch = _branch(manifest["parent"]["branch"], "manifest.parent.branch")
    lock_file = _ownership_root(manifest["lock_file"], "manifest.lock_file", file_only=True)
    inherited = _ownership_roots(manifest["inherited_paths"], "manifest.inherited_paths")
    protected = _ownership_roots(manifest["protected_paths"], "manifest.protected_paths")

    _reject_overlaps(inherited, "manifest.inherited_paths")
    _reject_overlaps(protected, "manifest.protected_paths")
    for inherited_root in inherited:
        for protected_root in protected:
            if _overlaps(inherited_root, protected_root):
                raise InheritanceError(
                    "inherited and protected ownership roots overlap: "
                    f"{inherited_root}, {protected_root}"
                )

    required = REQUIRED_PROTECTED_PATHS | {lock_file}
    if manifest_version == 2:
        required.add(AGENT_PROFILE_PATH)
    missing = sorted(
        path for path in required if not any(_overlaps(root, path) for root in protected)
    )
    if missing:
        raise InheritanceError(f"manifest is missing required protected paths: {missing}")

    template_sync = _validate_template_sync_ignore(repository_root, protected)

    lock = _read_json(repository_root, lock_file)
    _object(lock, {"schema_version", "parent"}, "lock")
    if type(lock["schema_version"]) is not int or lock["schema_version"] != SCHEMA_VERSION:
        raise InheritanceError(f"lock.schema_version must be {SCHEMA_VERSION}")
    _object(lock["parent"], {"repository", "commit"}, "lock.parent")
    locked_repository = _repository(lock["parent"]["repository"], "lock.parent.repository")
    commit = lock["parent"]["commit"]
    if locked_repository != parent_repository:
        raise InheritanceError("lock.parent.repository must match manifest.parent.repository")
    if type(commit) is not str or not COMMIT_ID.fullmatch(commit) or commit == "0" * 40:
        raise InheritanceError("lock.parent.commit must be a full non-zero lowercase commit ID")

    result = {
        "schema_version": manifest_version,
        "parent": {"repository": parent_repository, "branch": parent_branch, "commit": commit},
        "lock_file": lock_file,
        "ownership": {"inherited": sorted(inherited), "protected": sorted(protected)},
        "template_sync": template_sync,
    }
    if manifest_version == 2:
        result["agent_contract"] = _validate_agent_profile(
            repository_root,
            parent_repository,
            inherited,
            protected,
        )
    return result


def _git(root, arguments, operation):
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *arguments],
            capture_output=True,
            check=False,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise InheritanceError(f"parent Git {operation} could not run") from error
    if result.returncode != 0:
        raise InheritanceError(f"parent Git {operation} failed; refresh the local parent checkout")
    return result.stdout


def _github_repository(remote_url):
    for prefix in ("https://github.com/", "git@github.com:", "ssh://git@github.com/"):
        if remote_url.startswith(prefix):
            repository = remote_url[len(prefix) :]
            if repository.endswith(".git"):
                repository = repository[:-4]
            if REPOSITORY_TARGET.fullmatch(repository):
                return repository
    raise InheritanceError("parent origin must be a credential-free GitHub repository URL")


def _parent_root(parent_root):
    try:
        root = Path(parent_root).resolve(strict=True)
    except OSError as error:
        raise InheritanceError("parent root must exist") from error
    if not root.is_dir():
        raise InheritanceError("parent root must be a directory")
    top_level = Path(
        _git(root, ["rev-parse", "--show-toplevel"], "root discovery").strip()
    ).resolve()
    if top_level != root:
        raise InheritanceError("parent root must be the Git worktree top level")
    return root


def _next_parent_commit(parent_root, contract):
    remote = _git(parent_root, ["remote", "get-url", "origin"], "origin discovery").strip()
    if _github_repository(remote).casefold() != contract["parent"]["repository"].casefold():
        raise InheritanceError("parent origin does not match manifest.parent.repository")
    branch = contract["parent"]["branch"]
    target = _git(
        parent_root,
        ["rev-parse", "--verify", f"refs/remotes/origin/{branch}^{{commit}}"],
        "remote branch resolution",
    ).strip()
    if not COMMIT_ID.fullmatch(target):
        raise InheritanceError("parent remote branch did not resolve to a full commit ID")
    history = _git(
        parent_root,
        ["rev-list", "--first-parent", f"--max-count={MAX_FIRST_PARENT_COMMITS + 1}", target],
        "first-parent history read",
    ).splitlines()
    locked = contract["parent"]["commit"]
    if locked not in history:
        suffix = (
            " within the supported history window"
            if len(history) > MAX_FIRST_PARENT_COMMITS
            else ""
        )
        raise InheritanceError(
            f"locked commit is not on the remote branch first-parent history{suffix}"
        )
    index = history.index(locked)
    return target, None if index == 0 else history[index - 1]


def _changed_paths(parent_root, locked, candidate):
    output = _git(
        parent_root,
        [
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            "-z",
            "--no-renames",
            locked,
            candidate,
        ],
        "candidate diff read",
    )
    paths = sorted(path for path in output.split("\0") if path)
    if len(paths) > MAX_CHANGED_PATHS:
        raise InheritanceError(f"candidate commit changes more than {MAX_CHANGED_PATHS} paths")
    for index, path in enumerate(paths):
        _ownership_root(path, f"parent changed path[{index}]", file_only=True)
    return paths


def _path_owner(path, ownership):
    for owner in ("inherited", "protected"):
        if any(
            root == path or (root.endswith("/") and path.startswith(root))
            for root in ownership[owner]
        ):
            return owner
    return "unowned"


def _parent_entry(parent_root, candidate, path):
    output = _git(parent_root, ["ls-tree", "-z", candidate, "--", path], "candidate tree read")
    if not output:
        return None
    try:
        metadata, actual_path = output.rstrip("\0").split("\t", 1)
        mode, object_type, object_id = metadata.split(" ")
    except ValueError as error:
        raise InheritanceError(f"parent path has an invalid tree entry: {path}") from error
    if actual_path != path or object_type != "blob" or mode not in {"100644", "100755"}:
        raise InheritanceError(f"parent path must be a regular file: {path}")
    return object_id, mode == "100755"


def _child_entry(child_root, parent_root, path):
    current = child_root
    for part in path.split("/"):
        current /= part
        if current.is_symlink():
            raise InheritanceError(f"inherited child path must not use a symlink: {path}")
        if not current.exists():
            return None
    if not current.is_file():
        raise InheritanceError(f"inherited child path must be a regular file: {path}")
    object_id = _git(
        parent_root, ["hash-object", "--no-filters", "--", str(current)], "child hash"
    ).strip()
    return object_id, bool(current.stat().st_mode & 0o111)


def _parent_inherited_entries(parent_root, revision, ownership_roots):
    output = _git(
        parent_root,
        ["ls-tree", "-r", "-z", revision, "--", *ownership_roots],
        "inherited tree read",
    )
    entries = {}
    for index, raw_entry in enumerate(entry for entry in output.split("\0") if entry):
        try:
            metadata, path = raw_entry.split("\t", 1)
            mode, object_type, object_id = metadata.split(" ")
        except ValueError as error:
            raise InheritanceError("parent inherited tree has an invalid entry") from error
        _ownership_root(path, f"parent inherited path[{index}]", file_only=True)
        if (
            not _owned_by(path, ownership_roots)
            or object_type != "blob"
            or mode not in {"100644", "100755"}
        ):
            raise InheritanceError(f"parent inherited path must be a regular file: {path}")
        if path in entries:
            raise InheritanceError(f"parent inherited tree contains a duplicate path: {path}")
        entries[path] = (object_id, mode == "100755")
        if len(entries) > MAX_AUDITED_INHERITED_FILES:
            raise InheritanceError(f"inherited audit exceeds {MAX_AUDITED_INHERITED_FILES} files")
    return entries


def _child_inherited_entries(child_root, parent_root, ownership_roots):
    output = _git(
        child_root,
        [
            "ls-files",
            "-z",
            "--cached",
            "--others",
            "--exclude-standard",
            "--",
            *ownership_roots,
        ],
        "child inherited paths read",
    )
    files = []
    for index, path in enumerate(path for path in output.split("\0") if path):
        _ownership_root(path, f"inherited child path[{index}]", file_only=True)
        if not _owned_by(path, ownership_roots):
            raise InheritanceError(f"child inherited path is outside ownership: {path}")
        current = child_root
        missing = False
        for part in path.split("/"):
            current /= part
            if current.is_symlink():
                raise InheritanceError(f"inherited child path must not use a symlink: {path}")
            if not current.exists():
                missing = True
                break
        if missing:
            continue
        if not current.is_file():
            raise InheritanceError(f"inherited child path must be a regular file: {path}")
        files.append((path, current, bool(current.stat().st_mode & 0o111)))
        if len(files) > MAX_AUDITED_INHERITED_FILES:
            raise InheritanceError(f"inherited audit exceeds {MAX_AUDITED_INHERITED_FILES} files")

    entries = {}
    for start in range(0, len(files), HASH_BATCH_SIZE):
        batch = files[start : start + HASH_BATCH_SIZE]
        hashes = _git(
            parent_root,
            ["hash-object", "--no-filters", "--", *(str(item[1]) for item in batch)],
            "child hash batch",
        ).splitlines()
        if len(hashes) != len(batch):
            raise InheritanceError("child inherited file hashing returned an invalid result")
        for (path, _current, executable), object_id in zip(batch, hashes, strict=True):
            entries[path] = (object_id, executable)
    return entries


def plan_inheritance(root, parent_root):
    """Plan one first-parent commit without modifying either worktree."""
    contract = validate_inheritance(root)
    child_root = Path(root).resolve(strict=True)
    parent_root = _parent_root(parent_root)
    target, candidate = _next_parent_commit(parent_root, contract)
    changes = {name: [] for name in ("add", "modify", "candidate_delete", "already_current")}
    skipped = {name: [] for name in ("protected", "unowned")}
    if candidate:
        for path in _changed_paths(parent_root, contract["parent"]["commit"], candidate):
            owner = _path_owner(path, contract["ownership"])
            if owner != "inherited":
                skipped[owner].append(path)
                continue
            parent_entry = _parent_entry(parent_root, candidate, path)
            child_entry = _child_entry(child_root, parent_root, path)
            if parent_entry is None:
                operation = "candidate_delete" if child_entry else "already_current"
            elif child_entry is None:
                operation = "add"
            else:
                operation = "already_current" if child_entry == parent_entry else "modify"
            changes[operation].append(path)
    counts = {name: len(paths) for name, paths in {**changes, **skipped}.items()}
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "changes" if candidate else "up_to_date",
        "parent": {
            "repository": contract["parent"]["repository"],
            "branch": contract["parent"]["branch"],
            "locked_commit": contract["parent"]["commit"],
            "target_commit": target,
            "candidate_commit": candidate,
        },
        "changes": changes,
        "skipped": skipped,
        "summary": {**counts, "total": sum(counts.values())},
    }


def _manual_boundary_reason(path):
    if path.startswith(".github/workflows/"):
        return "workflow-security-boundary"
    if path == AGENT_PROFILE_PATH or path.startswith(".ai/project/"):
        return "agent-project-boundary"
    if path.startswith(".github/inheritance/") or path == TEMPLATE_SYNC_IGNORE_PATH:
        return "inheritance-ownership-boundary"
    return "repository-owned-boundary"


def _template_sync_excludes(path, excluded, exceptions):
    return _owned_by(path, excluded) and not _owned_by(path, exceptions)


def _child_default_ref(child_root):
    return _git(
        child_root,
        ["symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"],
        "child default branch read",
    ).strip()


def _child_finalization_worktree(root):
    child_root = Path(root).resolve(strict=True)
    top_level = Path(
        _git(child_root, ["rev-parse", "--show-toplevel"], "child root discovery").strip()
    ).resolve()
    if top_level != child_root:
        raise InheritanceError("child root must be the Git worktree top level")
    if _git(child_root, ["status", "--porcelain=v1"], "child status read"):
        raise InheritanceError("child worktree must be clean before finalization")
    branch = _git(
        child_root,
        ["symbolic-ref", "--quiet", "--short", "HEAD"],
        "child branch read",
    ).strip()
    default_ref = _child_default_ref(child_root)
    if branch == default_ref.removeprefix("origin/"):
        raise InheritanceError("finalization must not run on the default branch")
    remote = _git(child_root, ["remote", "get-url", "origin"], "child origin read").strip()
    return child_root, _github_repository(remote), branch


def _finalization_context(root, parent_root, source_commit):
    contract = validate_inheritance(root)
    child_root, child_repository, branch = _child_finalization_worktree(root)
    parent_root = _parent_root(parent_root)
    if type(source_commit) is not str or not COMMIT_ID.fullmatch(source_commit):
        raise InheritanceError("source commit must be a full lowercase commit ID")
    target, _candidate = _next_parent_commit(parent_root, contract)
    accepted_range = _git(
        parent_root,
        [
            "rev-list",
            "--first-parent",
            f"{contract['parent']['commit']}..{target}",
        ],
        "accepted source range read",
    ).splitlines()
    if source_commit != contract["parent"]["commit"] and source_commit not in accepted_range:
        raise InheritanceError("source commit must be in the accepted first-parent range")
    return child_root, parent_root, contract, child_repository, branch


def _finalization_review(child_root, parent_root, contract, source_commit):
    inherited = contract["ownership"]["inherited"]
    excluded, exceptions = _read_template_sync_ignore(child_root)
    parent_entries = _parent_inherited_entries(parent_root, source_commit, inherited)
    child_entries = _child_inherited_entries(child_root, parent_root, inherited)
    review = {
        name: []
        for name in (
            "synchronized",
            "pending_sync",
            "pending_manual_port",
            "manually_ported",
            "protected_review",
            "ownership_review",
            "deletion_review",
        )
    }
    for path in sorted(set(parent_entries) | set(child_entries)):
        parent_entry = parent_entries.get(path)
        child_entry = child_entries.get(path)
        is_manual = _template_sync_excludes(path, excluded, exceptions)
        if parent_entry is None:
            review["deletion_review"].append(path)
        elif child_entry == parent_entry:
            review["manually_ported" if is_manual else "synchronized"].append(path)
        elif is_manual:
            review["pending_manual_port"].append(path)
        else:
            review["pending_sync"].append(path)

    if source_commit != contract["parent"]["commit"]:
        for path in _changed_paths(
            parent_root,
            contract["parent"]["commit"],
            source_commit,
        ):
            if _path_owner(path, contract["ownership"]) != "unowned":
                continue
            if (
                _parent_entry(parent_root, source_commit, path) is not None
                or _child_entry(child_root, parent_root, path) is not None
            ):
                review["ownership_review"].append(path)

    default_ref = _child_default_ref(child_root)
    for path in _changed_paths(child_root, default_ref, "HEAD"):
        owner = _path_owner(path, contract["ownership"])
        if owner == "protected" and path != contract["lock_file"]:
            review["protected_review"].append(path)
        elif owner == "unowned":
            review["ownership_review"].append(path)
    for name in review:
        review[name] = sorted(set(review[name]))
    return review


def _finalization_report(contract, repository, branch, source_commit, review):
    blocked = any(
        review[name]
        for name in (
            "pending_sync",
            "pending_manual_port",
            "protected_review",
            "ownership_review",
            "deletion_review",
        )
    )
    needs_lock = contract["parent"]["commit"] != source_commit
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "blocked"
        if blocked
        else "ready_to_finalize"
        if needs_lock
        else "already_finalized",
        "repository": repository,
        "branch": branch,
        "parent": {
            "repository": contract["parent"]["repository"],
            "locked_commit": contract["parent"]["commit"],
            "source_commit": source_commit,
        },
        **review,
    }


def plan_finalization(root, parent_root, source_commit):
    """Audit exact-source convergence without modifying either worktree."""
    child_root, parent_root, contract, repository, branch = _finalization_context(
        root,
        parent_root,
        source_commit,
    )
    review = _finalization_review(child_root, parent_root, contract, source_commit)
    return _finalization_report(contract, repository, branch, source_commit, review)


def _raise_finalization_blocker(review):
    messages = {
        "pending_sync": "pending sync content must be accepted first",
        "pending_manual_port": "unsupported manual port is required",
        "protected_review": "protected review is required",
        "ownership_review": "ownership review is required",
        "deletion_review": "deletion review is required",
    }
    for category, message in messages.items():
        if review[category]:
            raise InheritanceError(f"{message}: {review[category]}")


def _write_lock_commit(child_root, contract, source_commit):
    lock_path = child_root / contract["lock_file"]
    temporary = lock_path.with_name(f".{lock_path.name}.finalize.tmp")
    if temporary.exists() or temporary.is_symlink():
        raise InheritanceError("temporary lock path must be absent before finalization")
    lock = _read_json(child_root, contract["lock_file"])
    lock["parent"]["commit"] = source_commit
    try:
        temporary.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
        temporary.replace(lock_path)
    except OSError as error:
        try:
            temporary.unlink(missing_ok=True)
        except OSError as cleanup_error:
            raise InheritanceError(
                "inheritance lock update and temporary cleanup failed"
            ) from cleanup_error
        raise InheritanceError("inheritance lock update failed before acceptance") from error


def apply_finalization(
    root,
    parent_root,
    source_commit,
    *,
    confirm_repository,
    confirm_source,
):
    """Advance the lock only after complete exact-source convergence."""
    child_root, parent_root, contract, repository, branch = _finalization_context(
        root,
        parent_root,
        source_commit,
    )
    if confirm_repository != repository or confirm_source != source_commit:
        raise InheritanceError("repository and source confirmation must match exactly")
    review = _finalization_review(child_root, parent_root, contract, source_commit)
    _raise_finalization_blocker(review)
    lock_updated = contract["parent"]["commit"] != source_commit
    if lock_updated:
        _write_lock_commit(child_root, contract, source_commit)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "finalized" if lock_updated else "already_finalized",
        "repository": repository,
        "branch": branch,
        "parent": {
            "repository": contract["parent"]["repository"],
            "source_commit": source_commit,
        },
        "changes": {"lock_updated": lock_updated},
        "review": review,
    }


def _fleet_repository(repository, child_root, parent_root):
    child_root = Path(child_root).resolve(strict=True)
    parent_root = _parent_root(parent_root)
    plan = plan_inheritance(child_root, parent_root)
    candidate = plan["parent"]["candidate_commit"]
    target = plan["parent"]["target_commit"]
    synchronized = list(plan["changes"]["already_current"])
    pending_sync = []
    manually_ported = []
    protected_review = []

    if candidate:
        for path in plan["changes"]["add"] + plan["changes"]["modify"]:
            child_entry = _child_entry(child_root, parent_root, path)
            target_entry = _parent_entry(parent_root, target, path)
            destination = synchronized if child_entry == target_entry else pending_sync
            destination.append(path)
        for path in plan["skipped"]["protected"]:
            child_entry = _child_entry(child_root, parent_root, path)
            accepted_entries = {
                _parent_entry(parent_root, revision, path) for revision in {candidate, target}
            }
            if child_entry in accepted_entries:
                manually_ported.append(path)
            else:
                protected_review.append({"path": path, "reason": _manual_boundary_reason(path)})

    return {
        "repository": repository,
        "repository_source": "explicit-argument",
        "parent": plan["parent"],
        "synchronized": sorted(synchronized),
        "pending_sync": sorted(pending_sync),
        "manually_ported": sorted(manually_ported),
        "protected_review": protected_review,
        "ownership_review": [
            {"path": path, "reason": "ownership-decision-required"}
            for path in plan["skipped"]["unowned"]
        ],
        "deletion_review": [
            {"path": path, "reason": "deletion-review-required"}
            for path in plan["changes"]["candidate_delete"]
        ],
    }


def _validated_fleet_entries(repositories):
    if type(repositories) is not list or not 1 <= len(repositories) <= MAX_FLEET_REPOSITORIES:
        raise InheritanceError(
            f"fleet repositories must contain 1 to {MAX_FLEET_REPOSITORIES} entries"
        )

    entries = []
    seen_repositories = set()
    seen_roots = set()
    for index, entry in enumerate(repositories):
        if type(entry) not in {list, tuple} or len(entry) != 3:
            raise InheritanceError(
                f"fleet repositories[{index}] must contain repository, child root, parent root"
            )
        repository = _repository(entry[0], f"fleet repositories[{index}].repository")
        try:
            child_root = Path(entry[1]).resolve(strict=True)
        except OSError as error:
            raise InheritanceError(f"fleet repositories[{index}].child root must exist") from error
        repository_key = repository.casefold()
        if repository_key in seen_repositories or child_root in seen_roots:
            raise InheritanceError("fleet repositories contain a duplicate child")
        seen_repositories.add(repository_key)
        seen_roots.add(child_root)
        entries.append((repository, child_root, entry[2]))
    return sorted(entries, key=lambda item: item[0].casefold())


def _fleet_summary(reports):
    categories = (
        "synchronized",
        "pending_sync",
        "manually_ported",
        "protected_review",
        "ownership_review",
        "deletion_review",
    )
    summary = {
        category: sum(len(report[category]) for report in reports) for category in categories
    }
    summary["repositories"] = len(reports)
    return summary


def fleet_report(repositories):
    """Report bounded local propagation state without modifying any worktree."""
    reports = [
        _fleet_repository(repository, child_root, parent_root)
        for repository, child_root, parent_root in _validated_fleet_entries(repositories)
    ]
    summary = _fleet_summary(reports)
    needs_attention = any(
        summary[category]
        for category in (
            "pending_sync",
            "protected_review",
            "ownership_review",
            "deletion_review",
        )
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "attention" if needs_attention else "ready",
        "repositories": reports,
        "summary": summary,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="validate contract")
    validate.add_argument("--root", type=Path, default=Path("."), help="child repository root")
    plan = commands.add_parser("plan", help="plan the next parent commit")
    plan.add_argument("--root", type=Path, default=Path("."), help="child repository root")
    plan.add_argument("--parent-root", type=Path, required=True, help="local parent Git worktree")
    finalize = commands.add_parser("finalize-sync", help="audit or finalize an exact source")
    finalize.add_argument("--root", type=Path, default=Path("."), help="child repository root")
    finalize.add_argument(
        "--parent-root",
        type=Path,
        required=True,
        help="local parent Git worktree",
    )
    finalize.add_argument("--source-commit", required=True, help="exact parent source commit")
    finalize.add_argument("--apply", action="store_true", help="advance the lock after audit")
    finalize.add_argument("--confirm-repository", help="exact child repository confirmation")
    finalize.add_argument("--confirm-source", help="exact source commit confirmation")
    fleet = commands.add_parser("fleet-report", help="report local propagation boundaries")
    fleet.add_argument(
        "--repository",
        action="append",
        nargs=3,
        required=True,
        metavar=("REPOSITORY", "CHILD_ROOT", "PARENT_ROOT"),
        help="explicit child repository and local child/parent worktrees",
    )
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            report = validate_inheritance(args.root)
        elif args.command == "plan":
            report = plan_inheritance(args.root, args.parent_root)
        elif args.command == "finalize-sync":
            if args.apply:
                report = apply_finalization(
                    args.root,
                    args.parent_root,
                    args.source_commit,
                    confirm_repository=args.confirm_repository,
                    confirm_source=args.confirm_source,
                )
            else:
                report = plan_finalization(
                    args.root,
                    args.parent_root,
                    args.source_commit,
                )
        else:
            report = fleet_report(args.repository)
    except InheritanceError as error:
        print(f"inheritance error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
