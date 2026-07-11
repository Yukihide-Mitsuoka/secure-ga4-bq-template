"""Unit tests for the CLI boundary (wiring, exit codes, report emission).

The GCP service factory is injected with minimal empty fakes (an empty project
yields only CHK-07 pipeline advice), keeping this offline and deterministic.
"""

from pathlib import Path
from typing import Any

import pytest

from src.modules.inspection.infrastructure.gcp.client import GcpServices
from src.modules.inspection.interface.cli import main


class _Request:
    def __init__(self, response: dict[str, Any]) -> None:
        self._response = response

    def execute(self) -> dict[str, Any]:
        return self._response


class _EmptyBigQuery:
    def datasets(self) -> "_EmptyBigQuery":
        return self

    def list(self, **kwargs: Any) -> _Request:
        return _Request({})


class _EmptyResourceManager:
    def projects(self) -> "_EmptyResourceManager":
        return self

    def getIamPolicy(self, **kwargs: Any) -> _Request:  # noqa: N802
        return _Request({})


class _EmptyDataCatalog:
    def projects(self) -> "_EmptyDataCatalog":
        return self

    def locations(self) -> "_EmptyDataCatalog":
        return self

    def taxonomies(self) -> "_EmptyDataCatalog":
        return self

    def list(self, **kwargs: Any) -> _Request:
        return _Request({})


class _EmptyLogging:
    def sinks(self) -> "_EmptyLogging":
        return self

    def exclusions(self) -> "_EmptyLogging":
        return self

    def list(self, **kwargs: Any) -> _Request:
        return _Request({})


def _empty_services() -> GcpServices:
    return GcpServices(
        bigquery=_EmptyBigQuery(),
        resource_manager=_EmptyResourceManager(),
        data_catalog=_EmptyDataCatalog(),
        logging=_EmptyLogging(),
    )


@pytest.fixture()
def params_file(tmp_path: Path) -> Path:
    path = tmp_path / "params.yml"
    path.write_text(
        "project_id: verify-project\nexpected_location: asia-northeast1\n", encoding="utf-8"
    )
    return path


def test_happy_path_writes_both_reports_and_exits_zero(
    params_file: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(
        ["--params", str(params_file), "--out-dir", str(tmp_path / "out")],
        services_factory=_empty_services,
    )
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "inspected verify-project" in out
    report_dirs = list((tmp_path / "out" / "verify-project").iterdir())
    assert len(report_dirs) == 1
    assert (report_dirs[0] / "findings.json").exists()
    assert (report_dirs[0] / "summary.md").exists()


def test_fail_on_medium_gates_on_the_pipeline_advice(params_file: Path, tmp_path: Path) -> None:
    # An empty project still yields CHK-07 MEDIUM (no audit sink) -> floor breached.
    exit_code = main(
        ["--params", str(params_file), "--out-dir", str(tmp_path / "out"), "--fail-on", "MEDIUM"],
        services_factory=_empty_services,
    )
    assert exit_code == 1


def test_fail_on_high_passes_when_only_medium_and_low_exist(
    params_file: Path, tmp_path: Path
) -> None:
    exit_code = main(
        ["--params", str(params_file), "--out-dir", str(tmp_path / "out"), "--fail-on", "HIGH"],
        services_factory=_empty_services,
    )
    assert exit_code == 0


def test_invalid_params_file_exits_two_with_message(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "bad.yml"
    bad.write_text("expected_location: x\n", encoding="utf-8")  # project_id missing
    exit_code = main(["--params", str(bad)], services_factory=_empty_services)
    assert exit_code == 2
    assert "invalid params" in capsys.readouterr().err


def test_missing_params_file_exits_two(tmp_path: Path) -> None:
    exit_code = main(["--params", str(tmp_path / "nope.yml")], services_factory=_empty_services)
    assert exit_code == 2
