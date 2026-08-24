---
id: secure-ga4-bq-docs
title: 文書案内
updated: 2026-08-24
---

# 文書案内

このページは、読者の目的から正しい文書へ移動するための入口です。

## 最初に知りたいこと

| 質問・作業 | 読む文書 | 文書が所有する内容 |
|------------|----------|--------------------|
| 結局、何を点検するのか | [点検ガイド](inspection.md) | 対象、CHK-01〜CHK-13、重大度、成果物、対象外 |
| このシステムは何ができ、どう接続するのか | [システム全体像](architecture/system-overview.md) | 提供機能、外部境界、構築・点検・CIのデータフロー |
| 顧客へ何を聞き、どこへ設定するのか | [顧客要件と実装パラメータ](requirements/customer-inputs.md) | 質問、設定先、承認事項、完了条件 |
| どう導入・実行するのか | [利用ガイド](usage.md) | 案件作成、点検、構築、定期実行の手順 |
| 正式な要求は何か | [要件文書索引](requirements/README.md) | 要件文書と実装設計の所在 |
| 実際のレポート形式を見たい | [合成点検レポート](../examples/reporting/README.md) | 架空データによる5種類の成果物 |
| 現在の開発状況を引き継ぎたい | [開発引き継ぎ](development-handoff.md) | active Issue/PR、blocker、次の作業 |

## 文書テーマとパス

| Path | Ownership | Purpose |
|------|-----------|---------|
| [foundation/](foundation/) | inherited from the direct parent chain | reusable foundation guidance, templates, and foundation ADRs |
| [adr/](adr/) | `secure-ga4-bq-template` | Secure GA4 decisions and local ADR index |
| [requirements/](requirements/) | `secure-ga4-bq-template` | 顧客入力と正式な要件。実装設計3文書は移行待ち |
| [api/](api/) | `secure-ga4-bq-template` | CLI and report contracts |
| [architecture/](architecture/README.md) | `secure-ga4-bq-template` | システム全体像、データフロー、module構成 |
| [deployment/](deployment/) | `secure-ga4-bq-template` | local configuration and deployment notes |
| [runbook/](runbook/) | `secure-ga4-bq-template` | local operational procedures |
| [troubleshooting/](troubleshooting/) | `secure-ga4-bq-template` | local failure modes and governance adaptations |
| [verification/](verification/) | `secure-ga4-bq-template` | dated live-execution evidence for acceptance criteria |
| [usage.md](usage.md) | `secure-ga4-bq-template` | 日本語の導入・点検・構築手順と安全境界 |
| [inspection.md](inspection.md) | `secure-ga4-bq-template` | 日本語の点検項目、効果、レポート例、制約 |
| [development-handoff.md](development-handoff.md) | `secure-ga4-bq-template` | current state, source index, decisions, and resume sequence |
| [glossary.md](glossary.md) | `secure-ga4-bq-template` | project ubiquitous language |
| [roadmap.md](roadmap.md) | `secure-ga4-bq-template` | project direction and planned milestones |

プロジェクト固有文書は`docs/`、親テンプレートから継承する文書は`docs/foundation/`が所有します。
同じ事実を複数文書へコピーせず、この表の所有文書へリンクしてください。

Use [`docs/foundation/guides/project-documentation.md`](foundation/guides/project-documentation.md)
for the reusable documentation structure and update-trigger guidance.
