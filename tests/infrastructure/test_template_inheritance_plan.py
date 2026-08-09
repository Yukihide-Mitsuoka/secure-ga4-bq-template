import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[2] / "scripts/template_inheritance.py"
SPEC = importlib.util.spec_from_file_location("template_inheritance_plan", MODULE_PATH)
inheritance = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inheritance)

PARENT = "acme/parent-template"
PROTECTED = [
    ".gitignore",
    ".github/governance/repository.json",
    ".github/inheritance/lock.json",
    ".github/inheritance/manifest.json",
    ".github/workflows/template-sync.yml",
    ".templatesyncignore",
]


class Repositories:
    def __init__(self, root):
        self.parent, self.child = root / "parent", root / "child"
        self.parent.mkdir()
        self.child.mkdir()
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Test User")
        self.git("config", "user.email", "test@example.invalid")
        self.git("remote", "add", "origin", f"https://github.com/{PARENT}.git")
        for path, content in {
            "inherited/modify.txt": "old\n",
            "inherited/delete.txt": "old\n",
            "inherited/current.txt": "old\n",
            ".gitignore": "parent-old\n",
            ".github/workflows/template-sync.yml": "parent-old\n",
        }.items():
            self.write(self.parent, path, content)
        self.locked = self.commit("base")
        for path, content in {
            "inherited/modify.txt": "future\n",
            "inherited/delete.txt": "old\n",
            "inherited/current.txt": "new\n",
            ".gitignore": "child-local\n",
            ".github/workflows/template-sync.yml": "parent-new\n",
        }.items():
            self.write(self.child, path, content)
        self.contract(self.locked)
        for path, content in {
            "inherited/add.txt": "new\n",
            "inherited/modify.txt": "new\n",
            "inherited/current.txt": "new\n",
            ".gitignore": "parent-new\n",
            ".github/workflows/template-sync.yml": "parent-new\n",
            "unowned.txt": "new\n",
        }.items():
            self.write(self.parent, path, content)
        (self.parent / "inherited/delete.txt").unlink()
        self.candidate = self.commit("candidate")
        self.write(self.parent, "inherited/modify.txt", "future\n")
        self.write(self.parent, "inherited/later.txt", "later\n")
        self.target = self.commit("later")
        self.git("update-ref", "refs/remotes/origin/main", self.target)

    def git(self, *arguments):
        result = subprocess.run(
            ["git", "-C", str(self.parent), *arguments],
            capture_output=True,
            check=False,
            text=True,
            timeout=5,
        )
        assert result.returncode == 0, result.stderr
        return result.stdout.strip()

    def commit(self, message):
        self.git("add", "-A")
        self.git("commit", "-m", message)
        return self.git("rev-parse", "HEAD")

    @staticmethod
    def write(root, path, content):
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def contract(self, commit):
        manifest = {
            "schema_version": 1,
            "parent": {"repository": PARENT, "branch": "main"},
            "lock_file": ".github/inheritance/lock.json",
            "inherited_paths": ["inherited/"],
            "protected_paths": PROTECTED,
        }
        lock = {"schema_version": 1, "parent": {"repository": PARENT, "commit": commit}}
        self.write(self.child, ".github/inheritance/manifest.json", json.dumps(manifest))
        self.write(self.child, ".github/inheritance/lock.json", json.dumps(lock))
        self.write(
            self.child,
            ".templatesyncignore",
            "\n".join([*PROTECTED, ".github/workflows/**"]) + "\n",
        )

    def snapshot(self):
        return {
            str(path.relative_to(self.child)): path.read_bytes()
            for path in self.child.rglob("*")
            if path.is_file()
        }


@pytest.fixture
def repos(tmp_path):
    return Repositories(tmp_path)


def test_plan_selects_one_commit_classifies_paths_and_is_read_only(repos):
    before = repos.snapshot()
    result = inheritance.plan_inheritance(repos.child, repos.parent)
    assert result["parent"]["candidate_commit"] == repos.candidate
    assert result["parent"]["target_commit"] == repos.target
    assert result["changes"] == {
        "add": ["inherited/add.txt"],
        "modify": ["inherited/modify.txt"],
        "candidate_delete": ["inherited/delete.txt"],
        "already_current": ["inherited/current.txt"],
    }
    assert result["skipped"] == {
        "protected": [".github/workflows/template-sync.yml", ".gitignore"],
        "unowned": ["unowned.txt"],
    }
    assert "inherited/later.txt" not in json.dumps(result)
    assert repos.snapshot() == before


def test_plan_reports_up_to_date_at_remote_head(repos):
    repos.contract(repos.target)
    result = inheritance.plan_inheritance(repos.child, repos.parent)
    assert result["status"] == "up_to_date"
    assert result["parent"]["candidate_commit"] is None
    assert result["summary"]["total"] == 0


def test_parent_origin_must_match_manifest(repos):
    repos.git("remote", "set-url", "origin", "https://github.com/acme/other.git")
    with pytest.raises(inheritance.InheritanceError, match="origin"):
        inheritance.plan_inheritance(repos.child, repos.parent)


def test_lock_must_be_on_first_parent_history(repos):
    repos.git("switch", "-c", "side", repos.locked)
    repos.write(repos.parent, "side.txt", "side\n")
    side = repos.commit("side")
    repos.git("switch", "main")
    repos.git("merge", "--no-ff", "side", "-m", "merge side")
    repos.git("update-ref", "refs/remotes/origin/main", repos.git("rev-parse", "HEAD"))
    repos.contract(side)
    with pytest.raises(inheritance.InheritanceError, match="first-parent"):
        inheritance.plan_inheritance(repos.child, repos.parent)


def test_inherited_child_symlink_is_rejected(repos, tmp_path):
    target = tmp_path / "outside.txt"
    target.write_text("outside\n", encoding="utf-8")
    path = repos.child / "inherited/modify.txt"
    path.unlink()
    path.symlink_to(target)
    with pytest.raises(inheritance.InheritanceError, match="symlink"):
        inheritance.plan_inheritance(repos.child, repos.parent)


def test_plan_cli_prints_same_candidate(repos, capsys):
    assert (
        inheritance.main(["plan", "--root", str(repos.child), "--parent-root", str(repos.parent)])
        == 0
    )
    assert json.loads(capsys.readouterr().out)["parent"]["candidate_commit"] == repos.candidate


def test_fleet_report_classifies_propagation_boundaries(repos):
    result = inheritance.fleet_report([("acme/child-template", repos.child, repos.parent)])

    repository = result["repositories"][0]
    assert repository["repository"] == "acme/child-template"
    assert repository["repository_source"] == "explicit-argument"
    assert repository["synchronized"] == [
        "inherited/current.txt",
        "inherited/modify.txt",
    ]
    assert repository["pending_sync"] == ["inherited/add.txt"]
    assert repository["manually_ported"] == [".github/workflows/template-sync.yml"]
    assert repository["protected_review"] == [
        {"path": ".gitignore", "reason": "repository-owned-boundary"}
    ]
    assert repository["ownership_review"] == [
        {"path": "unowned.txt", "reason": "ownership-decision-required"}
    ]
    assert repository["deletion_review"] == [
        {"path": "inherited/delete.txt", "reason": "deletion-review-required"}
    ]
    assert result["summary"]["repositories"] == 1
    assert result["status"] == "attention"


def test_fleet_report_aggregates_multiple_explicit_children(repos, tmp_path):
    second_child = tmp_path / "second-child"
    second_child.mkdir()
    for path, content in repos.snapshot().items():
        repos.write(second_child, path, content.decode("utf-8"))

    result = inheritance.fleet_report(
        [
            ("acme/child-two", second_child, repos.parent),
            ("acme/child-one", repos.child, repos.parent),
        ]
    )

    assert [item["repository"] for item in result["repositories"]] == [
        "acme/child-one",
        "acme/child-two",
    ]
    assert result["summary"]["repositories"] == 2
    assert result["summary"]["manually_ported"] == 2
    assert result["summary"]["protected_review"] == 2


def test_fleet_report_rejects_duplicate_children_and_pair_limit(repos):
    with pytest.raises(inheritance.InheritanceError, match="duplicate child"):
        inheritance.fleet_report(
            [
                ("acme/child", repos.child, repos.parent),
                ("acme/child", repos.child, repos.parent),
            ]
        )

    too_many = [
        (f"acme/child-{index}", repos.child / str(index), repos.parent)
        for index in range(inheritance.MAX_FLEET_REPOSITORIES + 1)
    ]
    with pytest.raises(inheritance.InheritanceError, match="fleet repositories"):
        inheritance.fleet_report(too_many)


def test_fleet_report_rejects_protected_child_symlink(repos, tmp_path):
    outside = tmp_path / "outside-ignore"
    outside.write_text("outside\n", encoding="utf-8")
    path = repos.child / ".gitignore"
    path.unlink()
    path.symlink_to(outside)

    with pytest.raises(inheritance.InheritanceError, match="symlink"):
        inheritance.fleet_report([("acme/child-template", repos.child, repos.parent)])


def test_fleet_report_preserves_parent_identity_validation(repos):
    repos.git("remote", "set-url", "origin", "https://github.com/acme/other.git")

    with pytest.raises(inheritance.InheritanceError, match="origin"):
        inheritance.fleet_report([("acme/child-template", repos.child, repos.parent)])


def test_fleet_report_cli_prints_deterministic_json(repos, capsys):
    assert (
        inheritance.main(
            [
                "fleet-report",
                "--repository",
                "acme/child-template",
                str(repos.child),
                str(repos.parent),
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["repositories"][0]["repository"] == (
        "acme/child-template"
    )


class FinalizationRepositories:
    def __init__(self, root):
        self.parent, self.child = root / "parent-finalize", root / "child-finalize"
        self.parent.mkdir()
        self.child.mkdir()
        self.git(self.parent, "init", "-b", "main")
        self.configure(self.parent)
        self.git(
            self.parent,
            "remote",
            "add",
            "origin",
            f"https://github.com/{PARENT}.git",
        )
        self.write(self.parent, "inherited/ordinary.txt", "old\n")
        self.write(self.parent, ".github/workflows/shared.yml", "old\n")
        self.locked = self.commit(self.parent, "base")
        self.write(self.parent, "inherited/ordinary.txt", "new\n")
        self.write(self.parent, ".github/workflows/shared.yml", "new\n")
        self.source = self.commit(self.parent, "source")
        self.git(self.parent, "update-ref", "refs/remotes/origin/main", self.source)

        self.write(self.child, "inherited/ordinary.txt", "new\n")
        self.write(self.child, ".github/workflows/shared.yml", "old\n")
        self.contract(self.locked)
        self.git(self.child, "init", "-b", "main")
        self.configure(self.child)
        self.git(
            self.child,
            "remote",
            "add",
            "origin",
            "https://github.com/acme/child-template.git",
        )
        child_main = self.commit(self.child, "template sync result")
        self.git(self.child, "update-ref", "refs/remotes/origin/main", child_main)
        self.git(
            self.child,
            "symbolic-ref",
            "refs/remotes/origin/HEAD",
            "refs/remotes/origin/main",
        )
        self.git(self.child, "switch", "-c", "chore/template_sync_source")

    @staticmethod
    def git(root, *arguments):
        result = subprocess.run(
            ["git", "-C", str(root), *arguments],
            capture_output=True,
            check=False,
            text=True,
            timeout=5,
        )
        assert result.returncode == 0, result.stderr
        return result.stdout.strip()

    def configure(self, root):
        self.git(root, "config", "user.name", "Test User")
        self.git(root, "config", "user.email", "test@example.invalid")

    def commit(self, root, message):
        self.git(root, "add", "-A")
        self.git(root, "commit", "-m", message)
        return self.git(root, "rev-parse", "HEAD")

    @staticmethod
    def write(root, path, content):
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def contract(self, commit):
        manifest = {
            "schema_version": 1,
            "parent": {"repository": PARENT, "branch": "main"},
            "lock_file": ".github/inheritance/lock.json",
            "inherited_paths": [
                "inherited/",
                ".github/workflows/shared.yml",
            ],
            "protected_paths": PROTECTED,
        }
        lock = {
            "schema_version": 1,
            "parent": {"repository": PARENT, "commit": commit},
        }
        self.write(
            self.child,
            ".github/inheritance/manifest.json",
            json.dumps(manifest),
        )
        self.write(
            self.child,
            ".github/inheritance/lock.json",
            json.dumps(lock),
        )
        self.write(
            self.child,
            ".templatesyncignore",
            "\n".join([*PROTECTED, ".github/workflows/**"]) + "\n",
        )

    def apply(self, source=None):
        source = source or self.source
        return inheritance.apply_finalization(
            self.child,
            self.parent,
            source,
            confirm_repository="acme/child-template",
            confirm_source=source,
        )


@pytest.fixture
def finalization_repos(tmp_path):
    return FinalizationRepositories(tmp_path)


def test_finalization_plan_reports_manual_workflow_port_without_writes(
    finalization_repos,
):
    before = finalization_repos.git(finalization_repos.child, "status", "--porcelain=v1")

    result = inheritance.plan_finalization(
        finalization_repos.child,
        finalization_repos.parent,
        finalization_repos.source,
    )

    assert result["status"] == "ready_to_finalize"
    assert result["pending_sync"] == []
    assert result["pending_manual_port"] == [
        {
            "path": ".github/workflows/shared.yml",
            "reason": "workflow-security-boundary",
        }
    ]
    assert finalization_repos.git(finalization_repos.child, "status", "--porcelain=v1") == before


def test_finalization_apply_ports_workflow_updates_lock_and_is_idempotent(
    finalization_repos,
):
    result = finalization_repos.apply()

    assert result["status"] == "finalized"
    assert result["changes"] == {
        "manual_ported": [".github/workflows/shared.yml"],
        "lock_updated": True,
    }
    assert (finalization_repos.child / ".github/workflows/shared.yml").read_text(
        encoding="utf-8"
    ) == "new\n"
    lock = json.loads(
        (finalization_repos.child / ".github/inheritance/lock.json").read_text(encoding="utf-8")
    )
    assert lock["parent"]["commit"] == finalization_repos.source

    finalization_repos.commit(finalization_repos.child, "finalize")
    assert finalization_repos.apply()["status"] == "already_finalized"


def test_finalization_apply_rejects_pending_sync_before_writing(finalization_repos):
    finalization_repos.write(
        finalization_repos.child,
        "inherited/ordinary.txt",
        "stale\n",
    )
    finalization_repos.commit(finalization_repos.child, "stale inherited content")

    with pytest.raises(inheritance.InheritanceError, match="pending sync"):
        finalization_repos.apply()

    assert (finalization_repos.child / ".github/workflows/shared.yml").read_text(
        encoding="utf-8"
    ) == "old\n"


def test_finalization_apply_rejects_protected_branch_change(finalization_repos):
    finalization_repos.write(finalization_repos.child, ".gitignore", "changed\n")
    finalization_repos.commit(finalization_repos.child, "change protected path")

    with pytest.raises(inheritance.InheritanceError, match="protected review"):
        finalization_repos.apply()


def test_finalization_apply_rejects_inherited_deletion(finalization_repos):
    (finalization_repos.parent / "inherited/ordinary.txt").unlink()
    deletion_source = finalization_repos.commit(
        finalization_repos.parent,
        "delete inherited path",
    )
    finalization_repos.git(
        finalization_repos.parent,
        "update-ref",
        "refs/remotes/origin/main",
        deletion_source,
    )

    with pytest.raises(inheritance.InheritanceError, match="deletion review"):
        finalization_repos.apply(source=deletion_source)
