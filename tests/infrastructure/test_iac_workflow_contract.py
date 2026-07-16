import re
from pathlib import Path

ROOT = Path(__file__).parents[2]
WORKFLOW_PATH = ROOT / ".github/workflows/iac.yml"
CHECKOUT_ACTION = "actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0"


def workflow() -> str:
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def test_iac_scan_context_runs_for_every_pull_request_and_main_push() -> None:
    contents = workflow()

    assert re.search(r"(?m)^on:\n  pull_request:\n  push:\n    branches: \[main\]$", contents)
    assert "  iac-scan:\n    name: iac-scan\n" in contents
    assert "paths:" not in contents


def test_changed_iac_detection_is_fail_closed() -> None:
    contents = workflow()

    for contract in (
        "fetch-depth: 0",
        "BASE_SHA:",
        "HEAD_SHA:",
        'git cat-file -e "$BASE_SHA^{commit}"',
        'git cat-file -e "$HEAD_SHA^{commit}"',
        'changed_files="$(git diff --name-only "$BASE_SHA" "$HEAD_SHA" --)"',
        r"(^|/)[^/]+\.tf(vars)?$|^infra/|^k8s/|^helm/",
    ):
        assert contract in contents
    assert contents.count('echo "iac=true" >> "$GITHUB_OUTPUT"') == 2
    assert contents.count('echo "iac=false" >> "$GITHUB_OUTPUT"') == 1


def test_scanners_remain_strict_and_run_only_for_iac_changes() -> None:
    contents = workflow()

    assert contents.count("if: steps.changes.outputs.iac == 'true'") == 2
    assert "severity: MEDIUM,HIGH,CRITICAL" in contents
    assert 'exit-code: "1"' in contents
    assert "soft_fail: false" in contents
    assert "continue-on-error" not in contents


def test_job_keeps_supply_chain_and_least_privilege_controls() -> None:
    contents = workflow()
    permissions = re.search(r"(?ms)^permissions:\n(.*?)\n\njobs:", contents)

    assert permissions is not None
    assert permissions.group(1) == "  contents: read"
    assert CHECKOUT_ACTION in contents
    assert "if: steps.changes.outputs.iac == 'false'" in contents
    assert "No IaC changes detected" in contents
