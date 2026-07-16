#!/usr/bin/env python3
"""Validate the local template inheritance contract defined by ADR-0008."""

import argparse
import json
import re
import sys
from pathlib import Path

SCHEMA_VERSION = 1
MANIFEST_PATH = ".github/inheritance/manifest.json"
MAX_CONTRACT_BYTES = 1_000_000
MAX_OWNERSHIP_ROOTS = 1_000
REPOSITORY_TARGET = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
COMMIT_ID = re.compile(r"^[0-9a-f]{40}$")
REQUIRED_PROTECTED_PATHS = {
    ".gitignore",
    ".github/governance/repository.json",
    ".github/inheritance/manifest.json",
    ".github/workflows/template-sync.yml",
    ".templatesyncignore",
}


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
    if type(manifest["schema_version"]) is not int or manifest["schema_version"] != SCHEMA_VERSION:
        raise InheritanceError(f"manifest.schema_version must be {SCHEMA_VERSION}")
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
    missing = sorted(
        path for path in required if not any(_overlaps(root, path) for root in protected)
    )
    if missing:
        raise InheritanceError(f"manifest is missing required protected paths: {missing}")

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

    return {
        "schema_version": SCHEMA_VERSION,
        "parent": {"repository": parent_repository, "branch": parent_branch, "commit": commit},
        "lock_file": lock_file,
        "ownership": {"inherited": sorted(inherited), "protected": sorted(protected)},
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    validate = parser.add_subparsers(required=True).add_parser("validate", help="validate contract")
    validate.add_argument("--root", type=Path, default=Path("."), help="child repository root")
    args = parser.parse_args(argv)
    try:
        report = validate_inheritance(args.root)
    except InheritanceError as error:
        print(f"inheritance error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
