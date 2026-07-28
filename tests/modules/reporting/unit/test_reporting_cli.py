from __future__ import annotations

import json

import pytest

from src.modules.reporting.domain.model import ProviderText
from src.modules.reporting.interface.cli import main
from tests.modules.reporting.unit.builders import write_artifact


class FakeGenerator:
    def __init__(self, response: dict | None = None) -> None:
        self.payload = ""
        self.response = response or {
            "executive_summary": "Review one access finding.",
            "findings": [
                {
                    "ref": "F001",
                    "explanation": "Access is broad.",
                    "next_action": "Narrow it.",
                }
            ],
        }

    def generate(self, payload: str) -> ProviderText:
        self.payload = payload
        return ProviderText(json.dumps(self.response), "fake", "model")


def test_cli_generates_report_with_standard_environment(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "global")
    input_path = write_artifact(tmp_path / "findings.json")

    generator = FakeGenerator()
    exit_code = main(
        ["--input", str(input_path)],
        generator_factory=lambda project, location, model: generator,
    )

    assert exit_code == 0
    report = (tmp_path / "ai-report.md").read_text(encoding="utf-8")
    assert report.startswith("# AI-generated inspection report\n")
    assert "## Executive summary" in report
    assert "- Coverage: 1 datasets, 1 tables, 2 columns" in report
    assert json.loads(generator.payload)["output_language"]["code"] == "en"


def test_cli_generates_japanese_report_without_changing_findings(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "global")
    input_path = write_artifact(tmp_path / "findings.json")
    generator = FakeGenerator(
        {
            "executive_summary": "アクセス権限の確認が必要です。",
            "findings": [
                {
                    "ref": "F001",
                    "explanation": "権限が広すぎます。",
                    "next_action": "権限を限定してください。",
                }
            ],
        }
    )

    exit_code = main(
        ["--input", str(input_path), "--language", "ja"],
        generator_factory=lambda project, location, model: generator,
    )

    assert exit_code == 0
    payload = json.loads(generator.payload)
    assert payload["output_language"] == {
        "code": "ja",
        "name": "Japanese",
        "instruction": "Write every narrative string field in Japanese.",
    }
    report = (tmp_path / "ai-report.md").read_text(encoding="utf-8")
    assert report.startswith("# AI生成点検レポート\n")
    assert "> 草案: 人によるレビューが必要です。決定論的なfindingが正準です。" in report
    assert "- プロジェクト: `secret-project`" in report
    assert "- 取得日時: `2026-07-12T00:00:00+00:00`" in report
    assert "- 対象範囲: 1 データセット、1 テーブル、2 カラム" in report
    assert "- 生成元: `fake` / `model`" in report
    assert "## エグゼクティブサマリー" in report
    assert "アクセス権限の確認が必要です。" in report
    assert "- 重大度: **HIGH**" in report
    assert "- リソース: `projects/secret-project/datasets/customer_mart`" in report
    assert "- ルール: `FR-4#3`" in report
    assert (
        "### 説明\n\n権限が広すぎます。\n\n"
        "### 決定論的な是正ヒント\n\n"
        "Replace the broad role with a dataset role\\."
    ) in report
    assert "### 次のアクション" in report
    assert "権限を限定してください。" in report
    assert "## 生成メタデータ" in report
    assert "- リクエストID: `取得不可`" in report


def test_cli_rejects_unknown_language_before_creating_provider(tmp_path) -> None:
    provider_created = False

    def generator_factory(project: str, location: str, model: str) -> FakeGenerator:
        nonlocal provider_created
        provider_created = True
        return FakeGenerator()

    with pytest.raises(SystemExit) as error:
        main(
            ["--input", str(tmp_path / "findings.json"), "--language", "fr"],
            generator_factory=generator_factory,
        )

    assert error.value.code == 2
    assert provider_created is False


def test_cli_rejects_missing_vertex_configuration(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_LOCATION", raising=False)

    assert main(["--input", str(tmp_path / "missing.json")]) == 2
