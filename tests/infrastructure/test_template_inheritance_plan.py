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
        }.items():
            self.write(self.parent, path, content)
        self.locked = self.commit("base")
        for path, content in {
            "inherited/modify.txt": "old\n",
            "inherited/delete.txt": "old\n",
            "inherited/current.txt": "new\n",
            ".gitignore": "child-local\n",
        }.items():
            self.write(self.child, path, content)
        self.contract(self.locked)
        for path, content in {
            "inherited/add.txt": "new\n",
            "inherited/modify.txt": "new\n",
            "inherited/current.txt": "new\n",
            ".gitignore": "parent-new\n",
            "unowned.txt": "new\n",
        }.items():
            self.write(self.parent, path, content)
        (self.parent / "inherited/delete.txt").unlink()
        self.candidate = self.commit("candidate")
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
    assert result["skipped"] == {"protected": [".gitignore"], "unowned": ["unowned.txt"]}
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
