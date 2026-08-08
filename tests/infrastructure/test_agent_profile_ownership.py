import json
from pathlib import Path

ROOT = Path(__file__).parents[2]
MANIFEST = ROOT / ".github/inheritance/manifest.json"
IGNORE = ROOT / ".templatesyncignore"
BUGFIX_SKILL = ROOT / ".skills/bugfix.skill.md"
PROFILE = ROOT / ".github/inheritance/agent-profile.json"
PROJECT_OVERLAY = ROOT / ".ai/project/agent-overlay.md"
TEMPLATE_OVERLAY = (
    ROOT / ".ai/contracts/templates/yukihide-mitsuoka/terraform-gcp-template/agent-overlay.md"
)
CLAUDE_ADAPTER = ROOT / "CLAUDE.md"

GOVERNANCE_SCRIPT = ROOT / "scripts/github_governance.py"

EXPECTED_INPUTS = [
    {
        "layer": "foundation",
        "repository": "Yukihide-Mitsuoka/ai-dev-foundation",
        "path": ".ai/contracts/foundation/agent-entry.md",
    },
    {
        "layer": "template",
        "repository": "Yukihide-Mitsuoka/terraform-gcp-template",
        "path": ".ai/contracts/templates/yukihide-mitsuoka/terraform-gcp-template/agent-overlay.md",
    },
    {
        "layer": "project",
        "repository": "Yukihide-Mitsuoka/secure-ga4-bq-template",
        "path": ".ai/project/agent-overlay.md",
    },
]


def test_leaf_profile_composes_foundation_template_and_project() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    overlay = PROJECT_OVERLAY.read_text(encoding="utf-8")

    assert manifest["schema_version"] == 2
    assert ".ai/contracts/foundation/" in manifest["inherited_paths"]
    assert (
        ".ai/contracts/templates/yukihide-mitsuoka/terraform-gcp-template/"
        in manifest["inherited_paths"]
    )
    assert ".github/inheritance/agent-profile.json" in manifest["protected_paths"]
    assert ".ai/project/" in manifest["protected_paths"]
    assert profile["inputs"] == EXPECTED_INPUTS
    assert "Yukihide-Mitsuoka/secure-ga4-bq-template" in overlay
    assert "Yukihide-Mitsuoka/terraform-gcp-template" not in overlay


def test_template_overlay_is_portable_and_adapter_is_profile_driven() -> None:
    template_overlay = TEMPLATE_OVERLAY.read_text(encoding="utf-8")
    adapter = CLAUDE_ADAPTER.read_text(encoding="utf-8")

    assert "Terraform on Google Cloud" in template_overlay
    assert "iac-scan" in template_overlay
    assert "immutable release tags" in template_overlay
    assert "Repository: `Yukihide-Mitsuoka/terraform-gcp-template`" not in template_overlay
    assert ".ai/project/" not in template_overlay
    assert len(adapter.splitlines()) <= 50
    assert ".github/inheritance/agent-profile.json" in adapter
    assert "strengthen-only" in adapter
    assert "inputs[].path" in adapter
    assert "Yukihide-Mitsuoka/secure-ga4-bq-template" not in adapter


def test_foundation_bugfix_skill_is_inherited_and_transportable() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ignored = {
        line.strip()
        for line in IGNORE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    skill = BUGFIX_SKILL.read_text(encoding="utf-8")

    assert ".skills/" in manifest["inherited_paths"]
    assert ".skills/bugfix.skill.md" not in manifest["protected_paths"]
    assert ".skills/bugfix.skill.md" not in ignored
    assert "Sweep for siblings" in skill
    assert "Sibling occurrences searched; results reported" in skill
    for trigger in ("バグ修正", "不具合修正", "バグ", "障害"):
        assert trigger in skill


def test_guardrail_adapter_and_governance_tool_share_canonical_rule_source() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    governance = GOVERNANCE_SCRIPT.read_text(encoding="utf-8")

    assert ".ai/guardrails.md" in manifest["inherited_paths"]
    assert ".ai/contracts/foundation/" in manifest["inherited_paths"]
    assert "scripts/actions/" in manifest["inherited_paths"]
    assert "scripts/" not in manifest["protected_paths"]
    assert "scripts/github_governance.py" in manifest["protected_paths"]
    assert "scripts/context_budget.py" in manifest["protected_paths"]
    assert "CANONICAL_GUARDRAILS_PATH" in governance
    assert ".ai/contracts/foundation/guardrails.md" in governance


def test_parent_release_contract_test_is_an_explicit_leaf_boundary() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ignored = {
        line.strip()
        for line in IGNORE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

    assert "scripts/tests/test_local_workflow_actions.py" in manifest["protected_paths"]
    assert "scripts/**" in ignored
    assert not (ROOT / "scripts/tests/test_local_workflow_actions.py").exists()
