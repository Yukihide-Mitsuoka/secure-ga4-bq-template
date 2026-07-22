import importlib.util
import json
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).parents[2]
MODULE_PATH = REPOSITORY_ROOT / "scripts/template_inheritance.py"
SPEC = importlib.util.spec_from_file_location("template_inheritance", MODULE_PATH)
inheritance = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inheritance)

PARENT, COMMIT = "acme/parent-template", "a" * 40


def valid_manifest():
    return {
        "schema_version": 1,
        "parent": {"repository": PARENT, "branch": "main"},
        "lock_file": ".github/inheritance/lock.json",
        "inherited_paths": [".ai/", "scripts/template_inheritance.py"],
        "protected_paths": [
            ".gitignore",
            ".github/governance/repository.json",
            ".github/inheritance/lock.json",
            ".github/inheritance/manifest.json",
            ".github/workflows/template-sync.yml",
            ".templatesyncignore",
        ],
    }


def valid_lock():
    return {"schema_version": 1, "parent": {"repository": PARENT, "commit": COMMIT}}


def write_contract(root, manifest=None, lock=None):
    manifest_value = manifest or valid_manifest()
    directory = root / ".github/inheritance"
    directory.mkdir(parents=True)
    (directory / "manifest.json").write_text(json.dumps(manifest_value), encoding="utf-8")
    (directory / "lock.json").write_text(json.dumps(lock or valid_lock()), encoding="utf-8")
    write_ignore(root, [*manifest_value["protected_paths"], ".github/workflows/**"])
    return directory


def write_ignore(root, entries):
    (root / ".templatesyncignore").write_text("\n".join(entries) + "\n", encoding="utf-8")


def test_valid_contract_returns_deterministic_ownership(tmp_path):
    write_contract(tmp_path)
    result = inheritance.validate_inheritance(tmp_path)

    assert result["parent"] == {"repository": PARENT, "branch": "main", "commit": COMMIT}
    assert result["ownership"] == {
        "inherited": sorted(valid_manifest()["inherited_paths"]),
        "protected": sorted(valid_manifest()["protected_paths"]),
    }


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.update(schema_version=2),
        lambda value: value["parent"].update(repository="not-a-target"),
        lambda value: value["parent"].update(branch="../main"),
        lambda value: value.update(inherited_paths=[]),
        lambda value: value.update(inherited_paths=[f"file-{index}" for index in range(1_001)]),
        lambda value: value.update(unknown=True),
        lambda value: value.update(inherited_paths=["docs/", "docs/api/"]),
        lambda value: value["protected_paths"].append(".ai/mission.md"),
        lambda value: value["protected_paths"].remove(".gitignore"),
        lambda value: value["protected_paths"].remove(".github/inheritance/lock.json"),
        *[
            lambda value, path=path: value.update(inherited_paths=[path])
            for path in ("../secret", "/absolute", "docs//file", "docs/**", ".git/config")
        ],
    ],
)
def test_manifest_rejects_unknown_or_invalid_boundary_values(tmp_path, mutate):
    manifest = valid_manifest()
    mutate(manifest)
    write_contract(tmp_path, manifest=manifest)
    with pytest.raises(inheritance.InheritanceError):
        inheritance.validate_inheritance(tmp_path)


def test_every_protected_root_must_be_covered_by_template_sync_ignore(tmp_path):
    manifest = valid_manifest()
    write_contract(tmp_path, manifest=manifest)
    write_ignore(
        tmp_path,
        [
            *[path for path in manifest["protected_paths"] if path != ".gitignore"],
            ".github/workflows/**",
        ],
    )

    with pytest.raises(inheritance.InheritanceError, match=r"template sync ignore.*\.gitignore"):
        inheritance.validate_inheritance(tmp_path)


def test_template_sync_must_exclude_every_workflow(tmp_path):
    manifest = valid_manifest()
    write_contract(tmp_path, manifest=manifest)
    write_ignore(tmp_path, manifest["protected_paths"])

    with pytest.raises(
        inheritance.InheritanceError,
        match=r"template sync ignore.*\.github/workflows/",
    ):
        inheritance.validate_inheritance(tmp_path)


def test_template_sync_exception_cannot_reinclude_protected_workflow(tmp_path):
    manifest = valid_manifest()
    write_contract(tmp_path, manifest=manifest)
    write_ignore(
        tmp_path,
        [
            *manifest["protected_paths"],
            ".github/workflows/**",
            ":!.github/workflows/security.yml",
        ],
    )

    with pytest.raises(inheritance.InheritanceError, match="template sync exception"):
        inheritance.validate_inheritance(tmp_path)


@pytest.mark.parametrize(
    ("parent", "commit"),
    [("acme/other", COMMIT), (PARENT, "abc123"), (PARENT, "0" * 40)],
)
def test_lock_must_match_parent_and_pin_a_full_commit(tmp_path, parent, commit):
    lock = valid_lock()
    lock["parent"] = {"repository": parent, "commit": commit}
    write_contract(tmp_path, lock=lock)
    with pytest.raises(inheritance.InheritanceError):
        inheritance.validate_inheritance(tmp_path)


@pytest.mark.parametrize(
    ("content", "pattern"),
    [('{"schema_version": 1, "schema_version": 1}', "duplicate key"), (" " * 1_000_001, "exceeds")],
)
def test_malformed_contract_files_are_rejected(tmp_path, content, pattern):
    directory = write_contract(tmp_path)
    (directory / "manifest.json").write_text(content, encoding="utf-8")
    with pytest.raises(inheritance.InheritanceError, match=pattern):
        inheritance.validate_inheritance(tmp_path)


def test_symlink_escape_is_rejected(tmp_path):
    directory = write_contract(tmp_path)
    outside_lock = tmp_path / "outside-lock.json"
    outside_lock.write_text(json.dumps(valid_lock()), encoding="utf-8")
    (directory / "lock.json").unlink()
    (directory / "lock.json").symlink_to(outside_lock)
    with pytest.raises(inheritance.InheritanceError, match="symlink"):
        inheritance.validate_inheritance(tmp_path)


def test_cli_reports_valid_and_invalid_contracts(tmp_path, capsys):
    directory = write_contract(tmp_path)
    assert inheritance.main(["validate", "--root", str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out)["parent"]["commit"] == COMMIT

    manifest = valid_manifest()
    manifest["protected_paths"].remove(".gitignore")
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert inheritance.main(["validate", "--root", str(tmp_path)]) == 2
    assert "inheritance error:" in capsys.readouterr().err


def test_repository_contract_and_legacy_ignore_are_consistent():
    result = inheritance.validate_inheritance(REPOSITORY_ROOT)
    assert result["parent"]["commit"] == "beb5310db975811a3da0b37bbf6ad8837d9e31b7"
    ignored = {
        line.strip()
        for line in (REPOSITORY_ROOT / ".templatesyncignore").read_text().splitlines()
        if line.strip() and not line.startswith("#")
    }

    def covered(path):
        candidate = f"{path}**" if path.endswith("/") else path
        return candidate in ignored or any(
            entry.endswith("/**") and path.startswith(entry[:-3]) for entry in ignored
        )

    assert all(covered(path) for path in result["ownership"]["protected"])
    assert ":!docs/foundation/" in ignored
    assert ":!docs/foundation/**" in ignored
    assert "!docs/foundation/" not in ignored
    assert "!docs/foundation/**" not in ignored
