---
id: requirements-dbt-dataform-rail
title: 要件定義 — マート構築レール（dbt / Dataform 使い分け）
status: v1.0
updated: 2026-07-10
---

# 要件定義書: マート構築レール（dbt / Dataform 使い分け対応）

| 項目 | 内容 |
| --- | --- |
| ステータス | **v1.0（面談用清書）** 2026-07-10 |
| 位置づけ | セキュアアセットの **構築モードに吸収される実装レール**（独立プロダクト化はしない） |
| 事業モデル | 本線と同じ **受託×再利用アセット**。単体販売ではなく、構築案件の実装品質・再利用性を上げる部品として提供 |
| 関連文書 | [requirements-secure-asset.md](requirements-secure-asset.md)（本線）／[design-modules-wif-wiring.md](design-modules-wif-wiring.md) |
| 設計思想 | 「AIが一発生成」ではなく **決定論ガード＋規約＋手本＋AIは枠内で書く**。リネージは変換ツールに導出させ、コストは決定論ゲートで守る |

---

## 1. 目的
GA4→BQのマート層を「安全な設定を宣言的に載せた状態」で建てるための再利用レールを用意する。列レベルセキュリティ（`policy_tags`）・partition/cluster・コストガードを、**変換ツールのconfigとして宣言的に**表現し、後付け手作業をなくす。

## 2. Dataform / dbt 使い分け要件（本レールの中核）

### 2.1 要求
案件の事情（GCPネイティブで完結したい / 既存dbt資産がある 等）に応じて **Dataform と dbt を簡単に選べる** こと。

### 2.2 実現方針（過剰設計を避ける）
「1つのメタモデルから両方を生成するコンパイラ」は作らない（＝過剰設計、決定論・単純さの思想に反する）。代わりに **薄い使い分け** を採る。

**共通レイヤ（エンジン非依存・共有資産）**
- レイヤ規約（dbt標準準拠）: データセットを `staging / intermediate / marts` に分離。命名 = `stg_ga4__events`（ソース二重アンダースコア）→ `int_*`（中間ロジック）→ `fct_*`/`dim_*`（マート）。タグ／機密度タクソノミーの参照名も共通化。
- ガバナンス: Terraform で taxonomy / policy tag / dataset / IAM を定義（どちらのエンジンでも同じものを参照）。
- コストガード: CI で `bq query --dry-run` のスキャンバイト予算ゲート ＝ **エンジン非依存**（BQ側の見積りなので dbt/Dataform どちらでも同一ロジック）。

**エンジン別スケルトン（2種）＋選択方式**
- `skeleton-dbt/` と `skeleton-dataform/` を用意。
- **選択方式＝foundationのprofile方式に準拠**（実査で判明: ai-dev-foundationはcookiecutterではなく「テンプレ＋profile-copy」で立ち上げる）。エンジン選択＝`profiles/dbt-bigquery/` / `profiles/dataform-bigquery/` の**該当profileをコピー**する。bespokeな生成器を作らず、既存の起動作法にそのまま乗る（＝保守が軽い）。
- **置き場所＝本アセットの4段目専用テンプレ `secure-ga4-bq-template` の中**（本線 §7.2）。**上流の ai-dev-foundation / terraform-gcp-template には足さない**（データ固有物を万能ベースに入れると全プロジェクトが重くなるため）。
- 一回だけの決定論スキャフォールド（実行時に両方を同期生成し続けるコンパイラではない）。`make` 契約（lint/build/test/run）をエンジン別profileで満たす。
- **選択単位**: プロジェクト（リポジトリ）単位で1エンジン。1リポ内での混在は非対応（非スコープ）。
- 保守対象は「スケルトン2種＋共通レイヤ」。共通レイヤ（規約・Terraform・CIコストゲート）はエンジンに依存しない。

### 2.3 設定マッピング表（同一ガバナンスを両エンジンで表現）
| 観点 | dbt (dbt-bigquery) | Dataform (SQLX / config) |
|---|---|---|
| 参照/依存 | `ref()` / `source()` | `ref()` / `${ref()}` |
| リネージ導出 | `dbt docs` が生成 | BQコンソール/Dataformが導出 |
| パーティション | `partition_by` | `bigquery.partitionBy` |
| クラスタリング | `cluster_by` | `bigquery.clusterBy` |
| フィルタ強制 | `require_partition_filter` | `bigquery.requirePartitionFilter` |
| 列ポリシータグ | `columns[].policy_tags`（schema.yml） | `columns[].bigqueryPolicyTags`（config）※ネイティブ対応・確認済 |
| テスト/検証 | tests（`unique`,`not_null` 等） | assertions |
| マクロ/ロジック | Jinja | JavaScript |

> 分岐が大きいのは「マクロ=Jinja vs JS」「tests vs assertions」。ここは共通化せず、各スケルトンで手本を1本ずつ用意する。

## 3. 機能要件

### FR-1 スケルトン
dbt / Dataform 双方に staging/marts の雛形と規約、手本モデル各1本。

### FR-2 ガバナンス宣言
手本モデルで partition/cluster/require_partition_filter と列 policy_tags を宣言済みにする（コピーして埋める形）。
- 両エンジンとも **Terraform管理タクソノミーの完全リソース名**（`projects/.../taxonomies/.../policyTags/...`）を参照。列あたりタグは**1つ**（BigQuery制約、両エンジン共通）。
- Dataform経路では**実行サービスアカウントに `datacatalog.taxonomies.get` ＋ `bigquery.tables.setCategory`（列レベルアクセス制御ロール）が必要** → FR-5のタクソノミー作成とセットで付与を手当てする。

### FR-3 コストゲート（CI）
変更モデルの dry-run 見積りバイト数が上限を超えたら CI を落とす。エンジン共通スクリプト。**判定方式＝モデル別の絶対上限（既定値＋モデル単位で上書き）。**
- 既定上限（例 100GB、要調整）を同梱し、大きなモデルはモデル設定で上書き（例外を明示的に宣言）。
- カタログ（機密度）と同じ「推奨デフォルト＋案件/モデルで上書き」の思想で統一。ベースライン状態の保存が不要で実装が軽い。
- 上書きは監査可能な形（設定ファイルに理由コメント付き）で残す。

### FR-4 Lint/規約
dbt=SQLFluff、Dataform=組込みフォーマット＋命名規約チェック。置き場所はfoundationの `make lint` 側（cloud認証不要のため gcp-cicd-workflows には置かない原則、本線 §7.2）。

### FR-5 Terraform連携
taxonomy/policy tag/dataset/IAM は Terraform 側で作成、モデルconfigはそのタグ名を参照（ID/リソース名の受け渡し方法を定義）。モジュールIFは [design-modules-wif-wiring.md](design-modules-wif-wiring.md) 参照。

## 4. 非機能要件
- べき等: `build`/`run` の再実行で同一結果。
- 決定論優先: 構造（依存・リネージ・コスト上限）はツール/CIが強制。LLMは初稿SQL・test/assertionスタブの下書きのみ。
- 移植性: エンジン選択以外の規約・CIは共通に保つ。

## 4.1 工数（本線§9に含む）
本レールの工数は本線の見積もりに内包済み（[requirements-secure-asset.md](requirements-secure-asset.md) §9）。該当分の目安:
- 4段目テンプレ内: dbt profile+手本 2〜3人日／dataform profile+手本 2〜3人日／GA4カタログ+unnest例 2〜3人日。
- CIコストゲート（`bq-cost-gate.yml`）: 1.5〜2人日。
- **B相当は dbt 1エンジンで成立**（dataform 2エンジン目はS上振れ）＝本線§9.3のレベル別ロールアップと一致。

## 5. 受け入れ基準
- dbt・Dataform 双方のスケルトンで、手本モデルが `policy_tags` と partition/cluster を宣言した状態でビルドできる。
- CIコストゲートが、予算超過クエリを両エンジンで落とせる。
- 同一のガバナンス（同じタクソノミー/タグ）を、エンジンを切り替えても再現できる。

## 6. 制約・前提
- 対象は BigQuery のみ。
- 1リポジトリ1エンジン（混在非対応）。
- Dataform の列ポリシータグは **`bigqueryPolicyTags` でネイティブ対応（確認済・フォールバック不要）**。実行SAへの権限付与（`datacatalog.taxonomies.get`＋`bigquery.tables.setCategory`）が前提。
- LLMの役割は「既存骨格の枠内でモデル/テストの初稿を書く」に限定。リネージ生成・コスト判断はさせない。
- 知財: スケルトン・共通レイヤは**汎用アセットとして保持**、案件差分（モデル定義・コスト予算の上書き等）は納品側の「案件パラメータ」（本線 §2.5 / FR-7 に準拠）。

## 7. 決定記録・未決事項

### 決定記録
| # | 決定事項 | 内容 | 節 |
| --- | --- | --- | --- |
| 1 | 事業モデル | 受託×再利用アセット（本線に同じ） | 本線 §2.1 |
| 2 | 使い分け方式 | foundationのprofile方式（profile-copy）。実行時コンパイラは非目標 | §2.2 |
| 3 | 置き場所 | 4段目テンプレ `secure-ga4-bq-template` 内（上流ベースには足さない） | §2.2, 本線 §7.2 |
| 4 | 命名規約 | dbt標準準拠（`stg_ga4__* / int_* / fct_*・dim_*`、staging/intermediate/marts 分離） | §2.2 |
| 5 | コストゲート | モデル別の絶対上限（既定値＋上書き） | FR-3 |
| 6 | Dataform対応 | `bigqueryPolicyTags` ネイティブ対応を確認済（フォールバック不要）。完全リソース名参照・列あたり1タグ | §2.3, FR-2 |
| 7 | CI配置 | cost-gateは `gcp-cicd-workflows` に新規 `bq-cost-gate.yml`、SQL lintはfoundationの `make lint` 側 | FR-3〜4, 本線 §7.2 |

### 未決事項
1. 既定上限の初期値（例 100GB）と、モデル別上書きの運用ルール。
