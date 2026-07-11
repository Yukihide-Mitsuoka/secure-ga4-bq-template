---
id: design-modules-wif-wiring
title: 実装設計 — 新規モジュールIFとWIF配線
status: draft-v0.1
updated: 2026-07-10
---

# 実装設計（ドラフト）: 新規モジュールのインターフェース ＋ WIF配線

- ステータス: Draft v0.1
- 関連: [requirements-secure-asset.md](requirements-secure-asset.md) / [requirements-dbt-dataform-rail.md](requirements-dbt-dataform-rail.md)
- 準拠規約（terraform-gcp-modules 実査）: 1モジュール=1ディレクトリ（`main/variables/outputs/versions.tf`＋`README.md`）、**provider宣言なし**（consumer所有）、`versions.tf` で `required_version >= 1.5`＋google `>= 5.0, < 8.0`、inputsは`validation`付き、outputsはID/名前のみ、参照は **tag固定 git source** `?ref=vX.Y.Z`。

> 重要な横断制約: **ポリシータグのタクソノミーの location は、対象データセットの location と一致**していないと列レベルセキュリティが効かない。全モジュールで `location` を揃える。

---

## A. terraform-gcp-modules に追加する新規モジュール

### A-1. `bigquery-dataset`
**作るもの**: `google_bigquery_dataset` ＋ データセット単位IAM（`google_bigquery_dataset_iam_member` を `for_each`）。
**主な入力**
| 変数 | 型 | 既定 | validation/備考 |
|---|---|---|---|
| `project_id` | string | — | 必須 |
| `dataset_id` | string | — | `^[a-zA-Z0-9_]+$` |
| `location` | string | — | タクソノミーと一致必須 |
| `description` | string | `null` | |
| `default_table_expiration_ms` | number | `null` | 長期保存の暴発防止（監査ログ保持短縮にも使用） |
| `default_partition_expiration_ms` | number | `null` | |
| `labels` | map(string) | `{}` | |
| `iam_members` | list(object({role=string, member=string})) | `[]` | データセット/テーブル単位の最小権限。basic roles禁止（SEC-021） |
| `delete_contents_on_destroy` | bool | `false` | 安全側 |
**出力**: `dataset_id` / `self_link` / `location`

### A-2. `bigquery-policy-tags`（タクソノミー＋3段タグ）
**作るもの**: `google_data_catalog_taxonomy` ＋ `google_data_catalog_policy_tag`（レベルごと）＋ 任意で `google_data_catalog_policy_tag_iam_member`（fine-grained reader）。
**主な入力**
| 変数 | 型 | 既定 | 備考 |
|---|---|---|---|
| `project_id` | string | — | |
| `location` | string | — | データセットと一致必須 |
| `taxonomy_display_name` | string | — | |
| `activated_policy_types` | list(string) | `["FINE_GRAINED_ACCESS_CONTROL"]` | |
| `levels` | list(object({name=string, description=string})) | `[{high},{medium},{low}]` | 3段デフォルト。カタログ同様**上書き可能パラメータ**（FR-1.2） |
| `fine_grained_readers` | map(list(string)) | `{}` | レベル名→閲覧可能なmember一覧（`roles/datacatalog.categoryFineGrainedReader`） |
**出力**: `taxonomy_id` / **`policy_tag_ids`（map: レベル名→完全リソース名）** ← dbt/Dataform configが参照する肝。

### A-3. `bigquery-data-policy`（列マスキング・任意）
**作るもの**: `google_bigquery_datapolicy_data_policy` ＋ `maskedReader` のIAM。
**主な入力**: `project_id` / `location` / `data_policy_id` / `policy_tag`（A-2の完全リソース名）/ `data_policy_type`(既定 `DATA_MASKING_POLICY`) / `predefined_expression`(例 `SHA256`/`EMAIL_MASK`/`DEFAULT_MASKING_VALUE`) / `masked_readers`(list)。
**出力**: `data_policy_id`

### A-4. `log-router-sink`（監査ログのルーティング＋保持短縮＝FR-3）
**作るもの**: `google_logging_project_sink`（`unique_writer_identity=true`）＋ 宛先へのwriter権限付与 ＋ 任意で `google_logging_project_exclusion`（除外フィルタ）。
**主な入力**
| 変数 | 型 | 既定 | 備考 |
|---|---|---|---|
| `project_id` | string | — | |
| `sink_name` | string | — | |
| `destination_type` | string | — | `bigquery`\|`storage` |
| `destination_id` | string | — | BQ dataset か GCS bucket |
| `filter` | string | `""` | 例: 高感度データのData Accessのみ |
| `exclusions` | list(object({name=string, filter=string})) | `[]` | Cloud Loggingノイズ除外 |
**出力**: `writer_identity` / `sink_id`
**保持短縮**: BQ宛先なら A-1 の `default_table_expiration_ms`、GCS宛先ならバケットlifecycleで実現（宛先側の責務）。

### A-5. `bq-inspector-role`（点検用・最小権限＝FR-6）
**作るもの**: `google_project_iam_custom_role`（最小権限read-onlyロール）＋ 対象SAへのバインド。書き込み権限は付与しない。
**含める権限（案・要精査）**:
- BQメタデータ/スキーマ: `bigquery.tables.get`, `bigquery.tables.list`, `bigquery.datasets.get`
- INFORMATION_SCHEMA実行: `bigquery.jobs.create`（クエリjob実行に必要）
- タクソノミー/タグ: `datacatalog.taxonomies.get`, `datacatalog.taxonomies.list`, `datacatalog.categories.getIamPolicy`
- IAMポリシー閲覧: `resourcemanager.projects.getIamPolicy`（または `roles/iam.securityReviewer`）
- Logging設定閲覧: `logging.sinks.get`, `logging.sinks.list`, `logging.exclusions.list`
**出力**: `role_id` / `inspector_sa_email`
> 注: 一部の読み取り（sink設定等）は綺麗な既定read-onlyロールが無いため、custom roleで束ねるのが最小権限として妥当。「ガバナンスツール自身が過剰権限を持たない」原則の実装。

---

## B. WIF配線（terraform-gcp-template は未配線＝追加作業）

### B-1. 2つのサービスアカウント
| SA | 用途 | 権限 | 使うワークフロー |
|---|---|---|---|
| **deployer SA** | Terraform apply（構築） | dataset/taxonomy/policy tag/sink/IAM作成に必要な範囲（例 `bigquery.admin` 相当は広すぎるので、dataEditor＋datacatalog.admin＋logging.configWriter＋projectIamAdmin を最小構成で検討） | `tf-plan.yml` / `tf-apply.yml` |
| **inspector SA** | 点検（読み取り専用） | A-5 の custom role のみ | `bq-inspect.yml` |

### B-2. 配線手順
1. `terraform-gcp-modules//modules/github-oidc` で WIFプール＋プロバイダ＋**deployer SA**＋project IAMを作成。
2. **inspector SA は追加配線**（github-oidcモジュールはSAを1つしか作らない）: 別途 `google_service_account` ＋ `google_service_account_iam_member`(workloadIdentityUser, 同じプールのrepo属性) ＋ A-5のcustom roleバインド。→ github-oidcモジュールを「複数SA対応」に拡張するか、本アセットテンプレ側で素のリソースとして持つ（要決定）。
3. リポ変数に `WIF_PROVIDER` / `DEPLOYER_SA`（＋`INSPECTOR_SA`）を設定。
4. GitHub environment（required reviewers）を作成＝apply承認ゲート。
5. caller workflow: `ci.yml`→`tf-plan`＋`bq-cost-gate`（PR時）、`cd.yml`→`tf-apply`（environmentゲート）。`bq-inspect` は `workflow_dispatch`/`schedule` を持つ別callerで、`service_account: INSPECTOR_SA` を渡す。
6. `concurrency:` グループをenv単位で設定（state-lock/ジョブ競合回避、troubleshooting.md準拠）。

### B-3. 認証の原則
- キーレス（WIF/OIDC）のみ。SAキーは発行しない（既存資産と一貫）。
- 権限は用途別SAで分離。点検経路に書き込み権限を絶対に載せない（FR-6）。

---

## C. gcp-cicd-workflows に追加する新規ワークフロー（house style）
- `bq-cost-gate.yml`: `workflow_call`＋WIF＋`setup-gcloud`。入力=SQL glob・`max_bytes`。`bq query --dry-run --format=json` の `totalBytesProcessed` が予算超で fail。PRコメントは `tf-plan.yml` のgithub-scriptパターン流用。
- `bq-inspect.yml`: `workflow_call`＋WIF＋`setup-gcloud`。`service_account` にinspector SAを受ける。点検スクリプト実行→レポート/是正ドラフト生成（ローカルCLIと同一ロジック）。`permissions: contents:read, id-token:write`。
- SQL lint（SQLFluff/`dataform format`）は foundation の `make lint` 側（cloud認証不要なため gcp-cicd-workflows には置かない原則）。

---

## D. 未決事項
1. deployer SA の最小権限セット — 暫定実装済み（`infra/envs/dev/wif.tf`: `bigquery.dataOwner`＋`datacatalog.admin`＋`logging.configWriter`、projectIamAdminは含めない）。実機applyでの過不足確認は未実施。
2. ~~inspector SA を github-oidcモジュール拡張で作るか、アセットテンプレ側の素リソースで持つか。~~ **決着（2026-07-11）**: アセットテンプレ側の素リソース（`infra/envs/dev/wif.tf`）。github-oidcモジュールはSAを1つしか作らない前提のため、複数SA対応への拡張は現時点でconsumerが1つ（この2つ目のSA自体）のみで時期尚早（COD-020）。
3. A-5 custom role の権限リスト精査（実機で読み取り経路の過不足を確認）— ロール自体は `bq-inspector-role` モジュール（`terraform-gcp-modules?ref=v0.4.0`）として実装済み。実機精査は未実施。
4. taxonomy/policy tag のTerraformリソース名がDataplex改名に追随して変わる可能性（バージョン固定で対応）。
