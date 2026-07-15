from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path

import pytest

from src.modules.service_packaging.application.render_menu import RenderInspectionMenu
from src.modules.service_packaging.infrastructure.markdown_menu_writer import (
    MarkdownMenuWriter,
)
from src.modules.service_packaging.infrastructure.yaml_profile_repository import (
    YamlMenuProfileRepository,
)
from src.modules.service_packaging.interface.render_menu_cli import main

PROFILE_PATH = Path("service-packages/inspection-standard.yml")


def _profile():
    return YamlMenuProfileRepository().load(PROFILE_PATH)


def test_use_case_loads_then_writes(tmp_path) -> None:
    profile = _profile()

    class Reader:
        def load(self, path: Path):
            assert path == PROFILE_PATH
            return profile

    class Writer:
        def write(self, actual, out_dir: Path) -> Path:
            assert actual is profile
            return out_dir / "inspection-menu.md"

    target = RenderInspectionMenu(reader=Reader(), writer=Writer()).handle(PROFILE_PATH, tmp_path)

    assert target == tmp_path / "inspection-menu.md"


def test_writer_renders_all_approved_profile_values_deterministically(tmp_path) -> None:
    profile = _profile()
    first = MarkdownMenuWriter().write(profile, tmp_path / "first").read_text(encoding="utf-8")
    second = MarkdownMenuWriter().write(profile, tmp_path / "second").read_text(encoding="utf-8")

    assert first == second
    assert profile.display_name in first
    assert profile.profile_id in first
    assert "JPY 300,000〜500,000" in first
    assert "| データセット | 10 |" in first
    assert "| テーブルリソース | 200 |" in first
    assert "| フラット化した末端列 | 2,000 |" in first
    assert all(check_id in first for check_id in profile.checks)
    assert all(item.label in first for item in profile.deliverables)
    assert all(item.label in first for item in profile.separate_estimate_conditions)
    assert "レビューセッション: 1回" in first


def test_profile_change_changes_output_without_writer_change(tmp_path) -> None:
    profile = _profile()
    changed = replace(profile, limits=replace(profile.limits, datasets=7))

    rendered = MarkdownMenuWriter().write(changed, tmp_path).read_text(encoding="utf-8")

    assert "| データセット | 7 |" in rendered
    assert "| データセット | 10 |" not in rendered


def test_writer_escapes_markdown_control_characters(tmp_path) -> None:
    profile = replace(_profile(), display_name="点検\n## [injected](target) | `value`")

    rendered = MarkdownMenuWriter().write(profile, tmp_path).read_text(encoding="utf-8")

    assert "\n## injected" not in rendered
    assert "[injected](target)" not in rendered
    assert "点検&#10;&#35;&#35; &#91;injected&#93;&#40;target&#41;" in rendered


def test_writer_refuses_to_overwrite_existing_output(tmp_path) -> None:
    target = tmp_path / "inspection-menu.md"
    target.write_text("keep", encoding="utf-8")

    with pytest.raises(FileExistsError, match="already exists"):
        MarkdownMenuWriter().write(_profile(), tmp_path)

    assert target.read_text(encoding="utf-8") == "keep"


def test_writer_cleans_temporary_file_when_publish_fails(monkeypatch, tmp_path) -> None:
    def fail_link(source, target) -> None:
        raise OSError("publish failed")

    monkeypatch.setattr(os, "link", fail_link)

    with pytest.raises(OSError, match="publish failed"):
        MarkdownMenuWriter().write(_profile(), tmp_path)

    assert list(tmp_path.iterdir()) == []


def test_cli_renders_without_cloud_configuration(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)

    assert main(["--profile", str(PROFILE_PATH), "--out-dir", str(tmp_path)]) == 0
    assert (tmp_path / "inspection-menu.md").is_file()


def test_cli_rejects_missing_profile(tmp_path) -> None:
    assert main(["--profile", str(tmp_path / "missing.yml")]) == 2
