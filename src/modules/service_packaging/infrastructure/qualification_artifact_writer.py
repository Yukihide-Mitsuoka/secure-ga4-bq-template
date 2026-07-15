from __future__ import annotations

import html
import json
import os
import tempfile
from pathlib import Path

from src.modules.service_packaging.domain.qualification import QualificationResult

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


class QualificationArtifactWriter:
    def write(self, result: QualificationResult, out_dir: Path) -> tuple[Path, Path]:
        out_dir.mkdir(parents=True, exist_ok=True)
        targets = (out_dir / "qualification.json", out_dir / "qualification.md")
        existing = tuple(target for target in targets if os.path.lexists(target))
        if existing:
            raise FileExistsError(f"qualification artifact already exists: {existing[0]}")

        contents = (_json_content(result), _markdown_content(result))
        temporary: list[Path] = []
        created: list[Path] = []
        try:
            for content in contents:
                descriptor, name = tempfile.mkstemp(prefix=".qualification-", dir=out_dir)
                path = Path(name)
                temporary.append(path)
                with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
            for source, target in zip(temporary, targets, strict=True):
                os.link(source, target)
                created.append(target)
        except Exception:
            for target in created:
                target.unlink(missing_ok=True)
            raise
        finally:
            for path in temporary:
                path.unlink(missing_ok=True)
        return targets


def _json_content(result: QualificationResult) -> str:
    scope = result.scope
    payload = {
        "profile": {"id": result.profile_id, "version": result.profile_version},
        "reasons": [
            {
                "actual": reason.actual,
                "condition_id": reason.condition_id,
                "label": reason.label,
                "limit": reason.limit,
            }
            for reason in result.reasons
        ],
        "schema_version": 1,
        "scope": {
            "counts": vars(scope.counts),
            "special_conditions": {
                "customer_wif_setup": scope.customer_wif_setup,
                "query_jobs_required": scope.query_jobs_required,
                "row_value_inspection_required": scope.row_value_inspection_required,
            },
            "version": scope.version,
        },
        "standard_package_eligible": result.standard_package_eligible,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _markdown_content(result: QualificationResult) -> str:
    scope = result.scope
    status = "標準パッケージ適合" if result.standard_package_eligible else "別途見積もり"
    lines = [
        "# 点検メニュー適合判定",
        "",
        f"- 結果: **{status}**",
        f"- プロファイルID: {_code(result.profile_id)}",
        f"- プロファイルスキーマ版: {_code(str(result.profile_version))}",
        "",
        "## 申告スコープ",
        "",
        "| 対象 | 件数 |",
        "|------|-----:|",
        f"| GCPプロジェクト | {scope.counts.projects:,} |",
        f"| データセット | {scope.counts.datasets:,} |",
        f"| テーブルリソース | {scope.counts.table_resources:,} |",
        f"| フラット化した末端列 | {scope.counts.leaf_columns:,} |",
        "",
        "## 特別作業",
        "",
        f"- 顧客WIF設定: {_boolean(scope.customer_wif_setup)}",
        f"- BigQueryクエリ実行: {_boolean(scope.query_jobs_required)}",
        f"- 行データ・値の点検: {_boolean(scope.row_value_inspection_required)}",
        "",
        "## 判定理由",
        "",
    ]
    if not result.reasons:
        lines.append("- なし")
    else:
        for reason in result.reasons:
            limit = "なし" if reason.limit is None else f"{reason.limit:,}"
            actual = (
                _boolean(reason.actual) if isinstance(reason.actual, bool) else f"{reason.actual:,}"
            )
            lines.append(
                f"- {_text(reason.label)}（{_code(reason.condition_id)}）: "
                f"実値={actual}, 上限={limit}"
            )
    lines.extend(["", "本判定は事前申告に基づき、最終価格や点検結果を確定しません。", ""])
    return "\n".join(lines)


def _text(value: str) -> str:
    return "".join(_TEXT_ESCAPES.get(character, character) for character in value)


def _code(value: str) -> str:
    escaped = html.escape(value, quote=True).replace("`", "&#96;")
    return f"`{escaped.replace(chr(13), '&#13;').replace(chr(10), '&#10;')}`"


def _boolean(value: bool) -> str:
    return "true" if value else "false"
