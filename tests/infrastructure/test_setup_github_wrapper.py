import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
WRAPPER = ROOT / "scripts/setup-github.sh"


@pytest.fixture
def wrapper_environment(tmp_path):
    arguments_path = tmp_path / "python-arguments"
    python = tmp_path / "python3"
    python.write_text(
        "#!/bin/sh\n"
        'printf \'%s\\n\' "$@" > "$FAKE_PYTHON_ARGUMENTS"\n'
        "printf 'delegated\\n'\n"
        'exit "${FAKE_PYTHON_EXIT:-0}"\n',
        encoding="utf-8",
    )
    python.chmod(0o755)
    return arguments_path, {
        "FAKE_PYTHON_ARGUMENTS": str(arguments_path),
        "HOME": os.environ.get("HOME", "/tmp"),
        "PATH": f"{tmp_path}:/usr/bin:/bin",
    }


def run_wrapper(environment, *arguments, **overrides):
    return subprocess.run(
        ["/bin/bash", str(WRAPPER), *arguments],
        capture_output=True,
        check=False,
        cwd="/",
        env={**environment, **overrides},
        text=True,
        timeout=5,
    )


def delegated_arguments(arguments_path):
    return arguments_path.read_text(encoding="utf-8").splitlines()


def test_explicit_repository_delegates_to_confirmed_apply(wrapper_environment) -> None:
    arguments_path, environment = wrapper_environment

    result = run_wrapper(environment, "acme/demo", "--confirm-repo", "acme/demo")

    assert result.returncode == 0
    assert result.stdout == "delegated\n"
    assert delegated_arguments(arguments_path) == [
        str(ROOT / "scripts/github_governance.py"),
        "apply",
        "--root",
        str(ROOT),
        "--repo",
        "acme/demo",
        "--confirm-repo",
        "acme/demo",
    ]


def test_dry_run_delegates_to_read_only_plan(wrapper_environment) -> None:
    arguments_path, environment = wrapper_environment

    result = run_wrapper(environment, "acme/demo", DRY_RUN="1")

    assert result.returncode == 0
    assert delegated_arguments(arguments_path) == [
        str(ROOT / "scripts/github_governance.py"),
        "plan",
        "--root",
        str(ROOT),
        "--repo",
        "acme/demo",
    ]


@pytest.mark.parametrize(
    "arguments",
    [
        (),
        ("acme/demo",),
        ("acme/demo", "--confirm-repo", "acme/other"),
        ("acme/demo", "--confirm-repo", "acme/demo", "extra"),
    ],
)
def test_invalid_apply_arguments_stop_before_delegation(wrapper_environment, arguments) -> None:
    arguments_path, environment = wrapper_environment

    result = run_wrapper(environment, *arguments)

    assert result.returncode == 2
    assert "Usage:" in result.stderr
    if arguments == ("acme/demo", "--confirm-repo", "acme/other"):
        assert "must exactly match" in result.stderr
    assert not arguments_path.exists()


def test_dry_run_rejects_apply_confirmation_arguments(wrapper_environment) -> None:
    arguments_path, environment = wrapper_environment

    result = run_wrapper(
        environment,
        "acme/demo",
        "--confirm-repo",
        "acme/demo",
        DRY_RUN="1",
    )

    assert result.returncode == 2
    assert not arguments_path.exists()


def test_python_exit_code_is_preserved(wrapper_environment) -> None:
    _, environment = wrapper_environment

    result = run_wrapper(
        environment,
        "acme/demo",
        "--confirm-repo",
        "acme/demo",
        FAKE_PYTHON_EXIT="7",
    )

    assert result.returncode == 7


def test_repository_target_is_passed_as_one_argument(wrapper_environment, tmp_path) -> None:
    arguments_path, environment = wrapper_environment
    marker = tmp_path / "unexpected-command"
    target = f"acme/demo; touch {marker}"

    result = run_wrapper(environment, target, "--confirm-repo", target)

    assert result.returncode == 0
    assert not marker.exists()
    assert delegated_arguments(arguments_path)[-4:] == [
        "--repo",
        target,
        "--confirm-repo",
        target,
    ]
