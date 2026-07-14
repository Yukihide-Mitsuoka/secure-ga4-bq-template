import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).parents[2]
CODEQL = ROOT / ".github" / "workflows" / "codeql.yml"
LABELS_SYNC = ROOT / ".github" / "workflows" / "labels-sync.yml"
SCORECARD = ROOT / ".github" / "workflows" / "scorecard.yml"
WORKFLOWS = ROOT / ".github" / "workflows"


def _job(path: Path, name: str) -> dict[str, Any]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    return document["jobs"][name]


def _action_refs(action_pattern: str) -> list[tuple[str, str]]:
    pattern = re.compile(rf"uses:\s*{action_pattern}@([^\s#]+)(?:\s+#\s+(v\d+\.\d+\.\d+))?")
    refs: list[tuple[str, str]] = []
    for path in sorted(WORKFLOWS.glob("*.yml")):
        refs.extend(pattern.findall(path.read_text(encoding="utf-8")))
    return refs


def test_scorecard_job_can_read_the_private_repository() -> None:
    permissions = _job(SCORECARD, "analysis")["permissions"]

    assert permissions["contents"] == "read"
    assert permissions["security-events"] == "write"
    assert permissions["id-token"] == "write"


def test_codeql_analyzes_the_repository_primary_language() -> None:
    matrix = _job(CODEQL, "analyze")["strategy"]["matrix"]

    assert matrix["language"] == ["python"]


def test_labels_sync_job_can_read_the_private_repository() -> None:
    permissions = _job(LABELS_SYNC, "sync")["permissions"]

    assert permissions["contents"] == "read"
    assert permissions["issues"] == "write"


def test_workflows_use_supported_github_action_runtimes() -> None:
    checkout_refs = _action_refs("actions/checkout")
    codeql_refs = _action_refs(r"github/codeql-action/[^@\s]+")

    assert checkout_refs
    assert all(re.fullmatch(r"[0-9a-f]{40}", ref) for ref, _ in checkout_refs)
    assert {version.split(".")[0] for _, version in checkout_refs} == {"v7"}
    assert codeql_refs
    assert all(re.fullmatch(r"[0-9a-f]{40}", ref) for ref, _ in codeql_refs)
    assert {version.split(".")[0] for _, version in codeql_refs} == {"v4"}
