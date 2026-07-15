import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
VERSION_FILE = ROOT / "version.txt"
RELEASE_PLEASE_ACTION = "googleapis/release-please-action@45996ed1f6d02564a971a2fa1b5860e934307cf7"
SBOM_ACTION = "anchore/sbom-action@e22c389904149dbc22b58101806040fa8d37a610"
TRIVY_ACTION = "aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25"
ATTEST_ACTION = "actions/attest-build-provenance@0f67c3f4856b2e3261c31976d6725780e5e4c373"
CHECKOUT_ACTION = "actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0"
TERRAFORM_SETUP_ACTION = "hashicorp/setup-terraform@b9cd54a3c349d3f38e8881555d616ced269862dd"
UV_SETUP_ACTION = "astral-sh/setup-uv@d0cc045d04ccac9d8b7881df0226f9e82c39688e"


def _workflow() -> dict[str, Any]:
    return yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def _is_stable_semver(value: str) -> bool:
    number = r"(?:0|[1-9]\d*)"
    return re.fullmatch(rf"{number}\.{number}\.{number}\n", value) is not None


def test_release_preparation_supports_main_push_and_manual_dispatch() -> None:
    triggers = _workflow()["on"]

    assert triggers["push"]["branches"] == ["main"]
    assert triggers["workflow_dispatch"] == {}
    assert _is_stable_semver(VERSION_FILE.read_text(encoding="utf-8"))


def test_release_preparation_accepts_generated_version(tmp_path: Path, monkeypatch: Any) -> None:
    generated_version = tmp_path / "version.txt"
    generated_version.write_text("1.0.0\n", encoding="utf-8")
    monkeypatch.setattr(sys.modules[__name__], "VERSION_FILE", generated_version)

    test_release_preparation_supports_main_push_and_manual_dispatch()


def test_release_version_rejects_non_stable_semver() -> None:
    invalid_versions = (
        "v1.0.0\n",
        "1.0\n",
        "01.0.0\n",
        "1.0.0",
        "1.0.0-alpha\n",
    )

    assert all(not _is_stable_semver(version) for version in invalid_versions)


def test_release_please_can_prepare_but_not_merge_the_release_pr() -> None:
    release_job = _workflow()["jobs"]["release-please"]
    action_step = next(step for step in release_job["steps"] if "uses" in step)

    assert release_job["permissions"] == {
        "contents": "write",
        "issues": "write",
        "pull-requests": "write",
    }
    assert action_step["uses"] == RELEASE_PLEASE_ACTION
    assert action_step["with"]["release-type"] == "simple"
    assert "gh pr merge" not in WORKFLOW.read_text(encoding="utf-8")


def test_release_gate_generates_both_required_sbom_formats() -> None:
    gate_job = _workflow()["jobs"]["release-gates"]
    sbom_steps = [step for step in gate_job["steps"] if step.get("uses") == SBOM_ACTION]
    action_refs = {step["uses"] for step in gate_job["steps"] if "uses" in step}
    run_steps = {step["run"] for step in gate_job["steps"] if "run" in step}

    assert gate_job["permissions"] == {
        "actions": "read",
        "attestations": "write",
        "contents": "write",
        "id-token": "write",
    }
    assert [step["with"]["format"] for step in sbom_steps] == [
        "spdx-json",
        "cyclonedx-json",
    ]
    assert [step["with"]["output-file"] for step in sbom_steps] == [
        "dist/sbom.spdx.json",
        "dist/sbom.cdx.json",
    ]
    assert {TRIVY_ACTION, ATTEST_ACTION}.issubset(action_refs)
    assert {"make test", "make sbom", "make build"}.issubset(run_steps)


def test_manual_dispatch_preflights_release_gates_without_a_tag() -> None:
    gate_job = _workflow()["jobs"]["release-gates"]
    checkout_step = next(step for step in gate_job["steps"] if step.get("uses") == CHECKOUT_ACTION)

    assert gate_job["if"] == (
        "${{ github.event_name == 'workflow_dispatch' || "
        "needs.release-please.outputs.release_created == 'true' }}"
    )
    assert checkout_step["with"]["ref"] == (
        "${{ needs.release-please.outputs.tag_name || github.sha }}"
    )


def test_release_gate_provisions_toolchains_before_make_setup() -> None:
    steps = _workflow()["jobs"]["release-gates"]["steps"]
    action_refs = [step.get("uses") for step in steps]
    make_setup_index = next(
        index for index, step in enumerate(steps) if step.get("run") == "make setup"
    )

    assert TERRAFORM_SETUP_ACTION in action_refs
    assert UV_SETUP_ACTION in action_refs
    assert action_refs.index(TERRAFORM_SETUP_ACTION) < make_setup_index
    assert action_refs.index(UV_SETUP_ACTION) < make_setup_index

    terraform_step = steps[action_refs.index(TERRAFORM_SETUP_ACTION)]
    assert terraform_step["with"]["terraform_wrapper"] == "false"
