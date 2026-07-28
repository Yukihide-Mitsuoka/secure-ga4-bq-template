---
id: synthetic-report-pack
title: 合成点検レポートpack
updated: 2026-07-28
---

# 合成点検レポートpack

このディレクトリは、GCP、ADC、Vertex AI、顧客データを使わずに成果物の具体像を確認するための
公開サンプルです。`sample-project`と配下のresourceはすべて架空であり、Acceptance証跡では
ありません。

| ファイル | 確認できること |
|----------|----------------|
| [`findings.json`](findings.json) | 正準の機械可読結果、実行条件、カバレッジ、finding |
| [`findings.csv`](findings.csv) | 表計算ソフト向けfinding投影 |
| [`summary.md`](summary.md) | 重大度とcheckpoint別の決定論的要約 |
| [`ai-report.md`](ai-report.md) | AI説明文の形式。文章はサンプル用に手動作成しており、AI生成結果ではない |
| [`remediation-draft.md`](remediation-draft.md) | 自動適用しない是正レシピとplaceholder |

サンプルは、列のPolicy Tag不足（CHK-04）、description不足（CHK-12）、昇格元宣言不足
（CHK-13）を示します。実案件では`make inspect`が生成した`findings.json`と`summary.md`が正準です。
AI説明文と是正ドラフトは人が確認する草案であり、合格判定や自動変更には使いません。
