---
id: secure-ga4-bq-usage
title: secure-ga4-bq-template 利用ガイド
updated: 2026-08-10
---

# secure-ga4-bq-template 利用ガイド

この文書は、このテンプレートから案件リポジトリを作り、BigQuery 上のデータマートを
安全に構築または点検するための入口です。個々の設定値や契約は正準文書へのリンクを参照し、
ここでは「何を、どの順番で行うか」を説明します。

新しい PC の準備、GitHub ガバナンス、テンプレート継承そのものについては、共通基盤の
[日本語セットアップ手順](foundation/guides/usage.ja.md)を参照してください。

初めに、[全体像・要件索引](requirements/README.md)で、提供範囲、アーキテクチャ、顧客への
確認事項をどの設定・実装へ反映するかを確認してください。

## 最初に利用目的を選ぶ

| 目的                             | 利用する機能                                              | 主な入口                                                  |
| -------------------------------- | --------------------------------------------------------- | --------------------------------------------------------- |
| 既存マートを点検する             | 読み取り専用の CHK-01〜CHK-13、是正案、任意の AI レポート | ルートの `Makefile`                                       |
| セキュアなマートを構築する       | Terraform と dbt または Dataform                          | [`profiles/`](../profiles/)                               |
| 点検サービスの対象範囲を確認する | メニュー生成、匿名スコープの適合判定                      | ルートの `Makefile`                                       |
| このテンプレート自体を保守する   | コード、テスト、文書、リリース                            | [`AGENTS.md`](../AGENTS.md) / [`CLAUDE.md`](../CLAUDE.md) |

構築では dbt と Dataform のどちらか一方を選びます。点検は GA4 の生エクスポートだけを
評価するものではなく、主に利用者が参照するマート層の IAM、列保護、コスト設定、
description、昇格列の由来宣言などを評価します。正式な要件は
[要件索引](requirements/README.md)にあります。

点検項目ごとの検出条件、得られる効果、レポートの具体例は
[BigQueryセキュリティ点検の内容・効果・レポート](inspection-capabilities.md)を参照してください。
成果物一式をクラウド認証なしで確認する場合は、架空データだけを使う
[合成点検レポートpack](../examples/reporting/README.md)を開いてください。

## 1. 案件リポジトリを作る

このリポジトリを直接案件用に変更せず、GitHub の **Use this template** から案件ごとの
リポジトリを作成します。

1. GitHub で `secure-ga4-bq-template` を開き、**Use this template** を選ぶ。
2. 案件用リポジトリを作成して clone する。
3. `.github/workflows/template-sync.yml` の `source_repo_path` を
   `Yukihide-Mitsuoka/secure-ga4-bq-template` に変更する。
4. `{{...}}` のプレースホルダーを検索し、案件の値に置き換える。
5. ローカルゲートを導入し、クラウド認証なしで初期状態を検証する。

```bash
grep -rn "{{" . --exclude-dir=.git
make setup
make doctor
make build
make test
```

Template Sync を利用する場合は、リポジトリ変数 `TEMPLATE_SYNC_ENABLED=true` を設定します。
GitHub の保護設定は、共通基盤の手順に従い、まず読み取り専用の `plan` で差分を確認してから
個別に承認した `apply` を実行してください。

## 2. 既存マートを点検する

### 前提

- 点検単体には Python 3.12 以上、`uv`、`make`、Google Cloud CLI が必要です。
- リポジトリ全体の `make build` / `make test` と構築モードでは Terraform も必要です。
- ローカル実行では Application Default Credentials（ADC）を使用します。サービス
  アカウントキーの JSON ファイルは作成しません。
- 点検対象には、BigQuery メタデータを読むための最小権限を付与します。
- 実データを含む案件では、対象範囲、実行主体、費用上限、成果物の保管先を先に承認します。

認証、WIF、リポジトリ変数の詳細は
[実行時設定](deployment/configuration.md)を参照してください。

### パラメータを準備する

例をコピーし、案件の値を編集します。

```bash
cp inspection-params.example.yml inspection-params.yml
```

最低限、次を確認します。

- `project_id`: 点検対象の GCP プロジェクト
- `expected_location`: 想定する BigQuery ロケーション
- `datasets.mart_patterns`: 点検するマートのデータセット名
- `datasets.raw_patterns`: 封じ込めだけを確認する raw データセット名
- `datasets.exclude`: 明示的に対象外とするデータセット
- `catalog_path`: 案件で使用する機密度カタログ
- `thresholds`: 大規模テーブル、保持期間、CMEK の判定基準

機密度と昇格列の由来は、コードに埋め込まず
[カタログ](../catalog/README.md)で宣言します。案件固有の機密度変更は既定値を書き換えず、
`overrides` に記録してください。

### 点検を実行する

```bash
make inspect PARAMS=inspection-params.yml OUT=reports
```

必要な場合だけ、指定した重大度以上の指摘で終了コードを失敗にできます。

```bash
make inspect PARAMS=inspection-params.yml OUT=reports FAIL_ON=HIGH
```

主な成果物は次のとおりです。

| 成果物                 | 用途                       |
| ---------------------- | -------------------------- |
| `findings.json`        | 正準の機械可読結果         |
| `findings.csv`         | 表計算ソフト向けの一覧     |
| `summary.md`           | 人が確認する決定的サマリー |
| `remediation-draft.md` | 自動適用しない是正案       |
| `ai-report.md`         | 任意の AI による説明草案   |

ゼロ件という結果は、実際に評価できた範囲だけに適用されます。`skipped` に記録された対象を
合格として扱ってはいけません。

### 是正案と AI レポートを作る

クラウド認証や AI を使わず、決定的な是正案を生成できます。

```bash
make remediation-draft \
  FINDINGS=reports/example-project/20260726T000000Z/findings.json
```

AI レポートは任意です。ADC、`GOOGLE_CLOUD_PROJECT`、
`GOOGLE_CLOUD_LOCATION` を設定し、案件として外部 AI 利用を承認した場合にだけ実行します。

```bash
make report-ai \
  FINDINGS=reports/example-project/20260726T000000Z/findings.json \
  REPORT_LANGUAGE=ja
```

`REPORT_LANGUAGE`は`en`または`ja`だけを受け付け、未指定時は`en`です。AI生成文と固定見出しを
選択言語で出力しますが、finding ID、重大度、resource、rule、決定論的な是正ヒントは変更しません。
`ai-report.md`はレビュー用の草案です。判定の正準は`findings.json`と`summary.md`です。
詳細な入出力と終了コードは
[AI レポート CLI 契約](api/report-ai-cli.md)を参照してください。

### GitHub Actions で定期実行する

1. レビュー済みの `inspection-params.yml` を案件リポジトリに用意する。
2. リポジトリ変数 `WIF_PROVIDER` と `INSPECTOR_SA` を設定する。
3. **BQ Inspect** を手動実行し、対象範囲と成果物を確認する。
4. 成功確認後にだけ `BQ_INSPECT_ENABLED=true` を設定し、週次実行を有効にする。

点検用 ID は読み取り専用です。デプロイ用 ID を代用しません。ワークフローは是正を自動適用
しません。

## 3. セキュアなマートを構築する

案件リポジトリで、変換エンジンを一つ選びます。

- [dbt + BigQuery の有効化手順](../profiles/dbt-bigquery/README.md)
- [Dataform + BigQuery の有効化手順](../profiles/dataform-bigquery/README.md)

各プロファイルの `Makefile` と `skeleton` をコピーすると、構築レール向けのコマンドが有効に
なります。`Makefile` は置換されるため、選択したモードと変更差分をレビューしてください。

共通の流れは次のとおりです。

1. Terraform のプロジェクト、リージョン、データセット名、IAM メンバーを案件用に設定する。
2. dbt または Dataform のプロファイルを有効にする。
3. `catalog/ga4-sensitivity.yml` の既定値と案件固有の override をレビューする。
4. Terraform が作る Policy Tag の出力を変換エンジンの変数へ渡す。
5. `make setup && make build` で、認証不要の構文・依存関係・コンパイル検証を行う。
6. 認証後に `make plan ENV=dev` を実行し、作成・変更・削除と費用影響をレビューする。
7. 別途承認されたデプロイ経路でのみ適用する。
8. 実行後にマートのデータテスト、点検、費用ゲートを確認する。

Terraform の構成と任意の列マスキングは
[`infra/README.md`](../infra/README.md)、WIF とコストゲートは
[実行時設定](deployment/configuration.md)を参照してください。共有プロジェクトで一時リソースを
使う検証は、専用 prefix、費用上限、削除手順、残存確認を事前に定めます。

## 4. 点検サービスの範囲を確認する

GCP、顧客データ、AI を使わずに標準メニューを生成できます。

```bash
make render-inspection-menu
make qualify-inspection-scope
```

案件では `engagement-scope.example.yml` をコピーし、匿名化した件数と作業条件だけを記入します。

```bash
make qualify-inspection-scope \
  SCOPE=engagement-scope.yml \
  MENU_PROFILE=service-packages/inspection-standard.yml
```

この判定は提案前の適合確認であり、最終価格、作業承認、クラウドアクセス許可ではありません。
商品内容を変更するときは、生成プログラムではなく、レビュー対象の
`service-packages/inspection-standard.yml` を変更します。

## 5. 安全に利用するための原則

- 完全な点検成果物は **Internal** です。公開リポジトリへ commit しません。
- 認証は ADC または WIF を使い、サービスアカウントキーを作成・保存しません。
- `make inspect` は読み取り専用です。是正案は自動適用されません。
- Terraform の `plan` は適用ではありません。適用と削除は、対象を確認して個別に承認します。
- 顧客データや新しいクラウドリソースを使う前に、所有者、対象範囲、費用上限、削除条件を決めます。
- 一時リソースは検証直後に削除し、名前空間と課金対象に残存がないことを確認します。
- AI レポートを使わなくても、決定的な点検・要約・是正案は利用できます。

公開範囲のルールは [README の Visibility](../README.md#visibility)、データ境界は
[実行時設定](deployment/configuration.md)を参照してください。

## 6. このテンプレート自体を保守する場合

案件を作るのではなく、このリポジトリ自体を変更する場合だけ clone して開発します。作業前に
[`AGENTS.md`](../AGENTS.md) または [`CLAUDE.md`](../CLAUDE.md) を読み、変更後は正準ターゲットを
実行します。

```bash
make format
make lint
make test
make build
make doctor
make security-scan
```

機能、設計、セキュリティ境界を変える場合は、対応する要件、ADR、運用文書も同じ PR で更新します。
現在の方向性と Acceptance S の条件は [ロードマップ](roadmap.md)にあります。

## 関連文書

| 知りたいこと                          | 文書                                                                                            |
| ------------------------------------- | ----------------------------------------------------------------------------------------------- |
| 共通基盤、新しい PC、GitHub 設定      | [共通基盤の日本語セットアップ手順](foundation/guides/usage.ja.md)                               |
| この資産が満たす要件                  | [要件索引](requirements/README.md)                                                              |
| できること、全体構成、顧客ヒアリング、実装パラメータ | [全体像・要件索引](requirements/README.md)                                        |
| 点検パラメータ、WIF、AI、コストゲート | [実行時設定](deployment/configuration.md)                                                       |
| 点検内容、効果、レポート例            | [点検内容・効果・レポート](inspection-capabilities.md)                                         |
| 機密度と昇格列の由来                  | [カタログガイド](../catalog/README.md)                                                          |
| Terraform と列マスキング              | [Terraform 構成](../infra/README.md)                                                            |
| dbt / Dataform の選択                 | [dbt](../profiles/dbt-bigquery/README.md) / [Dataform](../profiles/dataform-bigquery/README.md) |
| CLI の正式な契約                      | [API 文書](api/README.md)                                                                       |
| 現在の状態と今後                      | [ロードマップ](roadmap.md)                                                                      |
