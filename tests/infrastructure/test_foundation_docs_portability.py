from pathlib import Path

REPOSITORY_ROOT = Path(__file__).parents[2]
PROJECT_DOCUMENTATION_GUIDE = (
    REPOSITORY_ROOT / "docs" / "foundation" / "guides" / "project-documentation.md"
)


def test_doc_014_links_to_its_current_authority():
    guide = PROJECT_DOCUMENTATION_GUIDE.read_text(encoding="utf-8")

    assert (
        "[DOC-014](../../../.ai/project-document-maintenance.md#doc-014-root-readme-ownership)"
    ) in guide
    assert "[DOC-014](../../../.ai/documentation.md#doc-014-root-readme-ownership)" not in guide
