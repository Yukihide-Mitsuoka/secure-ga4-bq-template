from __future__ import annotations

import html
import os
import tempfile
from pathlib import Path

from src.modules.service_packaging.domain.menu import MenuProfile

_TEXT_ESCAPES = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
    "\r": "&#13;",
    "\n": "&#10;",
    **{character: f"&#{ord(character)};" for character in "\\`*_{}[]()#+-.!|"},
}


class MarkdownMenuWriter:
    def write(self, profile: MenuProfile, out_dir: Path) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        target = out_dir / "inspection-menu.md"
        if target.exists():
            raise FileExistsError(f"inspection menu already exists: {target}")

        descriptor, temporary_name = tempfile.mkstemp(prefix=".inspection-menu-", dir=out_dir)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(_render(profile))
                stream.flush()
                os.fsync(stream.fileno())
            os.link(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
        return target


def _render(profile: MenuProfile) -> str:
    lines = [
        f"# {_text(profile.display_name)}",
        "",
        "本資料は、版管理された標準プロファイルから生成した点検メニューです。",
        "",
        f"- プロファイルID: {_code(profile.profile_id)}",
        f"- プロファイルスキーマ版: {_code(str(profile.version))}",
        "",
        "## 参考価格",
        "",
        f"- {_text(profile.fee.currency)} {profile.fee.minimum:,}〜{profile.fee.maximum:,}",
        "- 最終価格は個別条件を確認したうえで営業判断により確定します。",
        "",
        "## 標準範囲",
        "",
        "| 対象 | 上限 |",
        "|------|-----:|",
        f"| GCPプロジェクト | {profile.limits.projects:,} |",
        f"| データセット | {profile.limits.datasets:,} |",
        f"| テーブルリソース | {profile.limits.table_resources:,} |",
        f"| フラット化した末端列 | {profile.limits.leaf_columns:,} |",
        "",
        "## 点検項目",
        "",
    ]
    lines.extend(f"- {_code(check_id)}" for check_id in profile.checks)
    lines.extend(["", "## 納品物", ""])
    lines.extend(f"- {_text(item.label)}（{_code(item.item_id)}）" for item in profile.deliverables)
    lines.extend(
        [
            "",
            "## レビュー",
            "",
            f"- レビューセッション: {profile.review_sessions:,}回",
            "",
            "## 別途見積もりとなる条件",
            "",
        ]
    )
    lines.extend(
        f"- {_text(item.label)}（{_code(item.item_id)}）"
        for item in profile.separate_estimate_conditions
    )
    lines.extend(
        [
            "",
            "標準範囲を超える作業は、上記条件に従って別途見積もりです。",
            "",
        ]
    )
    return "\n".join(lines)


def _text(value: str) -> str:
    return "".join(_TEXT_ESCAPES.get(character, character) for character in value)


def _code(value: str) -> str:
    escaped = html.escape(value, quote=True).replace("`", "&#96;")
    escaped = escaped.replace("\r", "&#13;").replace("\n", "&#10;")
    return f"`{escaped}`"
