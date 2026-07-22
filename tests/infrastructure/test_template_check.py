from pathlib import Path

REPOSITORY_ROOT = Path(__file__).parents[2]
TEMPLATE_CHECK = REPOSITORY_ROOT / "scripts" / "template-check.sh"


def test_doctor_validates_the_actual_child_inheritance_contract():
    script = TEMPLATE_CHECK.read_text(encoding="utf-8")

    assert 'if [ -f ".github/inheritance/manifest.json" ]; then' in script
    assert "python3 scripts/template_inheritance.py validate --root ." in script
    assert "Template inheritance and legacy sync protection contract is invalid" in script
