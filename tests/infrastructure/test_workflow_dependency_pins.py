import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHA = re.compile(r"[0-9a-f]{40}")
USES = re.compile(r"\buses:\s*([^\s#]+)")


def test_external_workflow_and_local_action_dependencies_use_commit_shas() -> None:
    unpinned: list[str] = []
    sources = list((ROOT / ".github/workflows").glob("*.y*ml"))
    sources.extend((ROOT / "scripts/actions").glob("*/action.yml"))
    for source in sorted(sources):
        for line_number, line in enumerate(source.read_text().splitlines(), 1):
            match = USES.search(line)
            if not match:
                continue
            target = match.group(1)
            if target.startswith(("./", "docker://")):
                continue
            reference = target.rsplit("@", 1)[-1]
            if not SHA.fullmatch(reference):
                unpinned.append(f"{source.relative_to(ROOT)}:{line_number}: {target}")

    assert unpinned == [], "unpinned workflow dependencies:\n" + "\n".join(unpinned)
