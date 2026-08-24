---
id: architecture-index
title: アーキテクチャ文書索引
updated: 2026-08-24
---

# アーキテクチャ文書索引

このディレクトリは、`secure-ga4-bq-template`のシステム構造とモジュール境界を管理します。
要求は[要件索引](../requirements/README.md)、操作手順は[利用ガイド](../usage.md)を参照してください。

| 文書 | 読者の質問 | 内容 |
|------|------------|------|
| [system-overview.md](system-overview.md) | 何ができ、外部とどう接続するか | 提供機能、システム境界、構築・点検・CIのフロー |
| [modules.md](modules.md) | Python内部をどう分割しているか | inspection、reporting、service packagingの依存関係 |

実装設計3文書は現在`docs/requirements/`にあります。受け入れ済みADRの既存リンクを壊さずに
このディレクトリへ移す作業は[Issue #326](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/326)
の後続PRで扱います。
