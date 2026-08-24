---
id: customer-inputs
title: 顧客要件と実装パラメータ
status: maintained
updated: 2026-08-24
---

# 顧客要件と実装パラメータ

この文書は、案件エンジニアが顧客へ確認する事項と、その回答を反映する設定・実装先を
対応付けます。製品の正式な要求は[要件索引](README.md)、システム構造は
[システム全体像](../architecture/system-overview.md)を参照してください。

## 標準実装と案件実装の境界

| 項目 | テンプレートが提供するもの | 案件で決めて実装するもの |
|------|----------------------------|--------------------------|
| GA4 export | export済みBigQuery datasetを入力として扱う契約 | GA4とBigQueryのリンク、出力先 |
| マート | staging・martsモデルと必要時のintermediateモデル、dbt/Dataformレール、テスト枠組み | 指標、粒度、結合、列、更新頻度、SQL、partition/cluster |
| 列保護 | taxonomy、Policy Tag、任意masking、機密度カタログ | 列分類、clear/masked reader、例外 |
| IAM/WIF | identityを分離するTerraformとCI接続 | 実際の主体、repository、承認・運用責任者 |
| 監査ログ | 設定を検査するCHK | sink、保持、除外条件と案件IaC |
| 点検 | CHK-01〜CHK-13、成果物schema、是正レシピ | 対象、除外、閾値、保管先、受け入れ判断 |
| AIレポート | 仮名化とprovider境界、日本語・英語の草案 | AI利用承認、region/model、提出前レビュー |

Row-level security、Cloud DLP、行値のPII検査、BIツール側のアクセス制御、収集時のPII防止、
自動是正、最終的な法令適合判断は標準範囲外です。

## 要件を確定する順序

| 段階 | 顧客と決めること | 記録・設定先 | 完了条件 |
|------|------------------|--------------|----------|
| 1. 事前適合 | 匿名の規模、WIF・query・行値検査の要否 | `engagement-scope.yml` | 標準範囲または別見積り理由が明示される |
| 2. 目的と範囲 | 構築／点検／両方、対象、対象外、成功条件 | 案件要件書、`inspection-params.yml` | 分母、除外理由、受け入れ責任者が承認する |
| 3. データ設計 | engine、入力、粒度、列、更新、ネスト展開、description | dbt/Dataformモデル、catalog | モデルと機密度・由来宣言をレビューできる |
| 4. セキュリティ | IAM主体、機密度、mask、CMEK、監査範囲 | Terraform変数、catalog、案件IaC | データ所有者とセキュリティ責任者が承認する |
| 5. 運用と費用 | WIF、頻度、query予算、保管、AI利用、rollback | GitHub変数、予算、運用手順 | 実行前承認と停止条件が揃う |
| 6. 実装と受け入れ | 設定PR、gate、plan、データテスト、再点検 | PR、plan、点検成果物 | 期待結果と残存リスクを確認する |

顧客名や担当者の連絡先は実装パラメータではありません。案件管理側で保持し、公開
リポジトリや`engagement-scope.yml`へ入れません。

## 提案前の匿名スコープ

顧客名、project ID、dataset名を収集せず、次の件数と作業条件だけを確認します。

| 顧客への質問 | `engagement-scope.yml`のフィールド |
|--------------|--------------------------------------|
| 対象GCP projectはいくつか | `counts.projects` |
| 除外後のdatasetはいくつか | `counts.datasets` |
| 走査対象のtable/viewはいくつか | `counts.table_resources` |
| フラット化したleaf列はいくつか | `counts.leaf_columns` |
| 顧客環境へWIFを新設するか | `special_conditions.customer_wif_setup` |
| dry-run以外のBigQuery queryが必要か | `special_conditions.query_jobs_required` |
| 行データまたは値の検査が必要か | `special_conditions.row_value_inspection_required` |

`make qualify-inspection-scope SCOPE=<file>`は、標準メニューに回答を照合します。最終価格、
クラウドアクセス承認、点検結果を決める処理ではありません。

## 点検パラメータ

| 顧客への質問 | 設定先・実装パラメータ |
|--------------|-------------------------|
| どのproject・locationを点検するか | `inspection-params.yml`: `project_id`、`expected_location` |
| mart/rawの命名規則と対象外は何か | `datasets.mart_patterns`、`datasets.raw_patterns`、`datasets.exclude` |
| Data Access監査を重点化するdatasetはどれか | `audit.high_sensitivity_datasets` |
| 監査ログの許容保持上限は何日か | `audit.retention_max_days` |
| 大規模table・長期保持・CMEKの基準は何か | `thresholds.large_table_bytes`、`long_lived_days`、`require_cmek` |
| 列の機密度と昇格元は何か | catalogの`overrides`、`promoted_columns` |
| どの重大度からCIを失敗させるか | CLI/workflowの`FAIL_ON` / `fail_on` |

未分類datasetはMART相当で完全点検します。対象外は理由とともに`datasets.exclude`へ宣言します。

## 構築パラメータと顧客固有実装

| 顧客への質問 | 設定・実装先 |
|--------------|--------------|
| project、location、dataset名は何か | Terraform: `project_id`、`region`、`layer_dataset_ids` |
| layerごとに誰へ何のroleを付けるか | Terraform: `layer_iam_members` |
| cleartext閲覧者、mask方式、masked readerは誰か | Terraform: `fine_grained_readers`、`data_policies` |
| Actionsを許可する案件repositoryはどれか | Terraform: `github_repository`、`github_repository_id`、SA/WIF ID群 |
| dbtとDataformのどちらを使うか | `profiles/`から一方を選ぶ |
| GA4 exportのproject/datasetは何か | profile: `ga4_export_project`、`ga4_export_dataset` |
| nested keyをどの型・列名へ昇格するか | 変換SQLと`promoted_columns.<column>.source` |
| マートの粒度、指標、列、更新、descriptionは何か | dbt/Dataformモデル |
| 監査ログのsink、保持、除外条件は何か | 案件Terraform |

`deployer_roles`を広げる場合は、必要な操作から権限を導出して個別レビューします。

## CI・費用・レポート

| 顧客への質問 | 設定先・実装パラメータ |
|--------------|-------------------------|
| 点検を週次実行するか | 手動成功後に`BQ_INSPECT_ENABLED=true` |
| dry-run対象SQLと標準byte上限は何か | `BQ_COST_GATE_SQL_GLOB`、`BQ_COST_GATE_DEFAULT_MAX_BYTES` |
| SQL別の例外予算と理由はあるか | version管理YAML、`BQ_COST_GATE_BUDGETS_FILE` |
| Vertex AIで説明草案を生成してよいか | 案件承認、project、location、model |
| レポート言語は何か | `REPORT_LANGUAGE=en|ja` |
| 成果物を誰がどこへ何日保管するか | 案件運用手順。`reports/`はgit管理しない |

WIF provider名とSAメールはTerraform出力からGitHub変数へ接続し、手入力で複製しません。

## 変換例

架空案件で次の回答を得たとします。

- 1 project、3 dataset、30 table/view、300 leaf列で、構築と点検の両方を行う。
- locationは`US`、Dataformを使い、sourceは`example-analytics.analytics_123456789`とする。
- `event_params.customer_email`を`customer_email`へ昇格し、highとしてmaskする。
- 分析者にはmask済み値だけを見せる。
- 週次点検を行い、SQLは1本あたり5,000,000,000 bytesを上限とする。
- Vertex AI利用を承認し、顧客向け草案は日本語にする。

| 反映先 | 主な値・作業 |
|--------|--------------|
| `engagement-scope.yml` | project・dataset・table/view・leaf列の件数 |
| Terraform | project、`region=US`、dataset ID、mask policy、masked reader |
| Dataform | source、location、Terraformが出力するdataset・Policy Tag ID |
| 変換SQLとcatalog | typed列、`source`、`level: high` |
| `inspection-params.yml` | project、location、dataset pattern、catalog、threshold |
| GitHub変数 | WIF出力、週次点検、5,000,000,000 bytesの費用gate |
| AIレポート | `REPORT_LANGUAGE=ja` |

この回答だけではマートの指標・更新SQL、監査ログsink、成果物保管先は決まりません。

## 実行前に別途承認する事項

- 顧客データまたはInternalな点検成果物へアクセスする主体と保管先
- GCPリソースの作成・変更・削除、対象project、prefix、残存確認方法
- BigQuery queryのbyte上限、費用上限、課金project
- IAM付与、WIF設定、既存共有リソースへの影響
- Vertex AIへの送信と、AI草案を顧客成果物へ含めるか
- 本番変更時間、rollback条件、是正後の再点検責任者

設定値の確定は実行許可を意味しません。認証情報、行データ、完全な点検成果物は公開
リポジトリへcommitしません。

## 要件確定の完了条件

- [ ] 構築／点検／両方と、標準範囲または別見積り理由が決まっている
- [ ] 対象・分母・除外理由・locationが承認されている
- [ ] データ所有者、デプロイ担当、点検担当の責任分界がある
- [ ] IAM、機密度、mask、CMEK、監査ログ方針が承認されている
- [ ] マート粒度、列、昇格元、description、partition/cluster方針が決まっている
- [ ] query費用、AI利用、成果物保管、変更・削除の承認条件が決まっている
- [ ] PR、認証不要gate、Terraform plan、データテスト、再点検が受け入れ手順にある
