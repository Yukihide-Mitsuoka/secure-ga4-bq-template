import json
from pathlib import Path

ROOT = Path(__file__).parents[2]
MANIFEST = ROOT / ".github/inheritance/manifest.json"
PROFILE = ROOT / ".github/inheritance/agent-profile.json"
PROJECT_OVERLAY = ROOT / ".ai/project/agent-overlay.md"


def test_parent_project_profile_is_not_used_as_the_leaf_profile() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert manifest["schema_version"] == 1
    assert ".ai/contracts/foundation/" in manifest["inherited_paths"]
    assert ".github/inheritance/agent-profile.json" in manifest["protected_paths"]
    assert ".ai/project/" in manifest["protected_paths"]
    assert not PROFILE.exists()
    assert not PROJECT_OVERLAY.exists()
