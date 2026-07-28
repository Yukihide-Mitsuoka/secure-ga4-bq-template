---
id: report-ai-cli
title: AI点検レポートCLI契約
status: implemented
updated: 2026-07-28
---

# AI点検レポートCLI

この文書は、完全な点検成果物から任意のAI説明草案と決定論的な是正ドラフトを生成するCLI契約を
定義します。AI説明文は正準の判定ではなく、人によるレビューが必要です。

## AIレポートコマンド

```bash
make report-ai \
  FINDINGS=reports/project/timestamp/findings.json \
  REPORT_LANGUAGE=ja
```

このコマンドはopt-inであり、ADCまたはWIFを通じてVertex AIを使います。最大1 MiBの完全な
`findings.json`を1つ読み、同じディレクトリまたは`OUT=<directory>`配下へ`ai-report.md`を
書き出します。

### パラメータ

| パラメータ | 必須 | 既定値 | 意味 |
|------------|------|--------|------|
| `FINDINGS` | はい | `findings.json` | 点検成果物のパス |
| `OUT` | いいえ | 入力ファイルのディレクトリ | 出力先 |
| `REPORT_LANGUAGE` | いいえ | `en` | `en`または`ja`。AI生成文と固定見出しの言語 |

許可値以外はprovider呼び出し前に拒否します。利用者が指定した自由記述をプロンプト命令として
渡しません。

### 契約

- 受理するschema: 点検成果物v1。versionなしの既存B成果物は後方互換のためv1として扱う。
- 必須coverage: `coverage.skipped`が空であること。
- Provider入力: 決定論的な別名、finding metadata、固定enumから解決した言語だけ。project・
  resource ID、observed value、行、認証情報、skipped詳細は除外する。
- 出力: 人がレビューする草案。`summary.md`と`findings.json`が正準である。
- 冪等性: 既存の`ai-report.md`を上書きしない。
- 言語によらずfinding ID、重大度、resource、rule、決定論的な是正ヒントを変更しない。

| 終了コード | 意味 | 呼び出し側の対応 |
|------------|------|------------------|
| 0 | レポートを書き込んだ | `summary.md`と照合して草案をレビューする |
| 1 | providerまたは生成出力の失敗 | 決定論成果物を保持し、原因を確認する |
| 2 | 設定、入力、coverage、path、言語、既存出力が不正 | ローカル入力・設定を修正する |

認証には`GOOGLE_CLOUD_PROJECT`、`GOOGLE_CLOUD_LOCATION`、ADC、Vertex AI invoke権限が
必要です。modelの既定値は`gemini-2.5-flash`であり、`GA4_BQ_REPORT_MODEL`で変更できます。

## 決定論的な是正ドラフトコマンド

```bash
make remediation-draft FINDINGS=reports/project/timestamp/findings.json
```

このコマンドはAI providerやクラウド認証を使いません。同じ完全な点検成果物を検証し、入力と同じ
ディレクトリまたは`OUT=<directory>`配下へ`remediation-draft.md`を書き出します。CHK-01〜
CHK-13をversion管理されたローカルレシピへ対応付けます。

出力はバイト決定論的であり、自動適用しません。必須入力、`REPLACE_ME_*` placeholder、安全に
提示できるTerraform・policy例、検証手順を含みます。成果物の自由記述をコード選択や値設定に
使わず、既存出力を上書きしません。

| 終了コード | 意味 | 呼び出し側の対応 |
|------------|------|------------------|
| 0 | 是正ドラフトを書き込んだ | placeholderを埋め、正準findingと照合してレビューする |
| 2 | 入力、coverage、path、既存出力が不正 | ローカル入力または出力先を修正する |

このコマンドはTerraform実行、policy適用、Pull Request作成、Vertex AI呼び出しを行いません。
Markdownをリポジトリのコードへ変換する作業は、案件の通常のレビュー・plan・承認gateに従います。
