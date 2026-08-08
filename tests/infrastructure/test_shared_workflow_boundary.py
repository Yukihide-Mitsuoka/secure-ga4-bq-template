import json
from pathlib import Path

ROOT = Path(__file__).parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"
LOCK = ROOT / ".github" / "inheritance" / "lock.json"
SHARED_CALLERS = {
    "ai-review.yml": "ai-review",
    "container.yml": "container-scan",
    "dast.yml": "dast-baseline",
    "labels-sync.yml": "labels-sync",
}


def test_compatible_workflows_call_synchronized_local_actions() -> None:
    for workflow_name, action_name in SHARED_CALLERS.items():
        workflow = (WORKFLOWS / workflow_name).read_text(encoding="utf-8")

        assert f"uses: ./scripts/actions/{action_name}" in workflow


def test_leaf_specific_release_and_scorecard_remain_direct_boundaries() -> None:
    release = (WORKFLOWS / "release.yml").read_text(encoding="utf-8")
    scorecard = (WORKFLOWS / "scorecard.yml").read_text(encoding="utf-8")

    assert "workflow_dispatch:" in release
    assert "uses: ./scripts/actions/release-please" not in release
    assert "github/codeql-action/upload-sarif@" in scorecard
    assert "# v4.37.0" in scorecard
    assert "uses: ./scripts/actions/scorecard" not in scorecard


def test_direct_parent_lock_matches_reviewed_workflow_checkpoint() -> None:
    lock = json.loads(LOCK.read_text(encoding="utf-8"))

    assert lock["parent"]["commit"] == "169c17a28c631235822993edc8eee92e14343aea"
