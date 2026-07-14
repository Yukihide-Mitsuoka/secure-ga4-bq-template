from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).parents[2]
CODEQL = ROOT / ".github" / "workflows" / "codeql.yml"
LABELS_SYNC = ROOT / ".github" / "workflows" / "labels-sync.yml"
SCORECARD = ROOT / ".github" / "workflows" / "scorecard.yml"


def _job(path: Path, name: str) -> dict[str, Any]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    return document["jobs"][name]


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
