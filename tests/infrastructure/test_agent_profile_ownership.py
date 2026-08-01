import json
from pathlib import Path

ROOT = Path(__file__).parents[2]
MANIFEST = ROOT / ".github/inheritance/manifest.json"
PROFILE = ROOT / ".github/inheritance/agent-profile.json"
PROJECT_OVERLAY = ROOT / ".ai/project/agent-overlay.md"


def test_parent_project_profile_is_not_used_as_the_leaf_profile() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    overlay = PROJECT_OVERLAY.read_text(encoding="utf-8")

    assert manifest["schema_version"] == 1
    assert ".ai/contracts/foundation/" in manifest["inherited_paths"]
    assert ".github/inheritance/agent-profile.json" in manifest["protected_paths"]
    assert ".ai/project/" in manifest["protected_paths"]
    assert profile["inputs"][-1] == {
        "layer": "project",
        "repository": "Yukihide-Mitsuoka/secure-ga4-bq-template",
        "path": ".ai/project/agent-overlay.md",
    }
    assert "Yukihide-Mitsuoka/secure-ga4-bq-template" in overlay
    assert "Yukihide-Mitsuoka/terraform-gcp-template" not in overlay
