---
id: design-inspection-engine
title: 点検エンジンの実装設計（FR-4、FR-9、FR-10の決定論チェック）
status: implemented-v1.3-promotion-source
updated: 2026-07-28
---

# 実装設計: 点検エンジン

- FR-5 CSV拡張の状態: **Issue #228で実装済み**（2026-07-23）。正準JSON成果物、Markdown要約、
  収集動作、クエリ費用を変更せず、決定論的なfinding一覧のフラットな投影を追加した。
- CHK-12拡張の状態: **Issue #70で実装済み**（2026-07-15）。実装済みFR-4セキュリティ集合と
  過去のAcceptance B分母を変更せず、汎用的なマートのテーブル・列description完全性を追加した。
  デリバリーは§10のとおり分割した。
- CHK-13拡張の状態: **Issue #235で実装済み**（2026-07-26）。producerより先にreporting consumerを
  導入した後、現在は観測した昇格leaf列をエンジンが評価し、標準サービスプロファイルにも追加
  チェックを含めている（§11）。
- 基準実装の状態: **v1.0実装済み**（2026-07-12）。§8のPR
  #13/#14/#15/#19/#22/#23/#24/#25/#26/#27/#28で、11チェックとregistry、収集アダプター、
  YAML設定、ユースケース、`make inspect` CLI、JSON・Markdownレポートをmainへ導入した。
  CLIはconsole scriptではなく`make inspect` / `python -m`として提供する。非パッケージ型リポジトリ
  ではmakeが正準エントリーポイントである。実環境証跡は
  [Acceptance B証跡](../verification/2026-07-12-inspection-engine-b-evidence.md)と
  [技術的Acceptance A証跡](../verification/2026-07-15-public-ga4-acceptance-a-evidence.md)に記録済み。
- 要件: [requirements-secure-asset.md](requirements-secure-asset.md)のFR-4（11のセキュリティ
  チェック）、FR-9（追加のマートdescriptionチェック）、FR-10（追加の構造化された昇格元チェック）、
  FR-5（レポート出力のうち機械可読部分）、FR-6、
  [design-modules-wif-wiring.md](design-modules-wif-wiring.md) A-5（点検用最小権限ロール）、
  FR-7（案件パラメータ）、§4.2（カバレッジ分母）、§6（冪等・読み取り専用・低スキャン費用）。
- 本設計の範囲: **Bレベルエンジンと追加のCHK-12・CHK-13**。収集し、決定論チェックを評価し、
  機械可読findingとプレーンなMarkdown要約を生成する。AI生成の説明レポートと是正ドラフト
  （Aレベル。本エンジンのJSONを消費）、PII値検査（A+）、`bq-inspect.yml` CIワークフローは
  対象外とする。ワークフローはgcp-cicd-workflowsに置き、そのCLI契約だけを本書で定義する。

## 1. 配置と構成

`src/modules/inspection/`にPythonのbounded contextを配置する。ARC-001/002に従うClean
Architectureであり、判断と代替案はADR-0003に記録している。

```
src/modules/inspection/
  MODULE.md
  domain/
    snapshot.py        # ProjectSnapshotと下位モデル（frozen dataclass、標準ライブラリのみ）
    catalog.py         # 機密度カタログモデルとeffective level解決（FR-1.2）
    params.py          # InspectionParams（検証済み案件パラメータ、FR-7）
    finding.py         # FindingとSeverity
    report.py          # Reportとカバレッジカウンター
    checks/            # チェックカテゴリごとに1つの純粋関数
      iam.py           # CHK-01..03
      column_security.py  # CHK-04..05
      audit_logging.py    # CHK-06..07
      cost.py             # CHK-08..10
      dataset_hygiene.py  # CHK-11
      metadata_documentation.py  # CHK-12..13
  application/
    ports.py           # 収集・出力port（§3）とClock port
    collect_snapshot.py   # port経由でProjectSnapshotを組み立てるユースケース
    run_inspection.py     # snapshot → チェック実行 → Report
  infrastructure/
    gcp/               # Google APIごとのアダプター。HTTP clientをラップする（COD-041）
      bigquery_metadata.py   # datasets.list/get, tables.list/get
      resource_manager.py    # projects.getIamPolicy (policy v3, incl. auditConfigs)
      data_catalog.py        # taxonomies.list, policyTags.list
      logging_config.py      # sinks.list, exclusions.list
    yaml_catalog_repository.py   # catalog/ga4-sensitivity.ymlを読み込む
    yaml_params_repository.py    # 案件パラメータファイルを読み込む
    json_report_writer.py        # findings.json（正準の完全成果物）
    csv_report_writer.py         # findings.csv（安定したフラットfinding投影）
    markdown_report_writer.py    # 決定論的なsummary.md描画
  interface/
    cli.py             # argparseエントリーポイントと境界検証（COD-011）
tests/modules/inspection/        # 実装ツリーと対応（TST-001）
  unit/                          # snapshot builderを使う純粋チェック。I/Oなし
  integration/                   # 記録済み・実環境レスポンスに対するアダプター（flag付き）
```

設計不変条件はリポジトリ全体の原則と同じである。**決定論エンジンが判定し、AIは
`findings.json`のフレーム内で文章だけを書く。** 本モジュールからLLMを呼び出さない。

## 2. データモデル

### 2.1 ProjectSnapshot（domain）

チェックに必要な情報を1回だけ収集し、以後は不変とする。チェックは
`(snapshot, params, catalog) -> list[Finding]`の純粋関数であり、決定論とdomainカバレッジ80%以上
（TST-003）を直接検証できる。

| モデル | 主なフィールド | 収集元 |
|--------|----------------|--------|
| `ProjectIam` | `bindings[{role, members[]}]`、`audit_configs[{service, log_configs[]}]` | `cloudresourcemanager.projects.getIamPolicy`（requestedPolicyVersion=3） |
| `DatasetMeta` | `dataset_id, location, default_table_expiration_ms, default_partition_expiration_ms, cmek_key, access[{role, member}], labels` | `bigquery.datasets.get` |
| `TableMeta` | `table_id, table_type, description, num_bytes, creation_time, expiration_time, time_partitioning_field, range_partitioning_field, require_partition_filter, clustering_fields, schema_fields[{path, field_type, description, policy_tag_ids[]}]` | `bigquery.tables.get`。schemaはdescriptionと`policyTags`を含み、nested fieldをドット区切りのleaf pathへ平坦化する |
| `Taxonomy` | `name, location, policy_tags[{name, display_name}]` | `datacatalog.taxonomies.list`と`policyTags.list` |
| `LoggingConfig` | `sinks[{name, destination, filter, disabled}]`、`exclusions[{name, filter, disabled}]` | `logging.sinks.list`、`logging.exclusions.list` |
| `ProjectSnapshot`メタデータ | `project_id, captured_at, skipped[{resource, reason}]` | 注入したClockと収集時の記録 |

**BigQueryクエリジョブは発行しない。** すべてのチェックはRESTメタデータだけで判定できる。
`datasets.get` / `tables.get`は、パーティション、クラスタリング、期限、`numBytes`、列ごとの
`policyTags`を返す。この結果、次の性質を持つ。

- 点検のスキャン費用は **課金バイト0** であり、NFRの「INFORMATION_SCHEMAを優先」（§6）より
  強い境界となる。
- B経路に`bigquery.jobs.create`は **不要** であり、B環境の点検ロールから明示的に除外する。
  共有A-5モジュールは、将来のA+ consumer向けにINFORMATION_SCHEMA対応の既定値を保持する。
  そのconsumerには別途権限レビューが必要である（design-modules-wif-wiring §D-3）。
- トレードオフとして、データセットごとに1回の`INFORMATION_SCHEMA`クエリを実行する代わりに、
  テーブルごとに1回の`tables.get`を呼ぶ。数百テーブルのICP規模では許容する。将来数千テーブルの
  案件が現れた場合は、同じportの背後へINFORMATION_SCHEMAアダプターを追加し、domainは変更しない。

### 2.2 案件パラメータ（FR-7）

案件ごとに1つのYAMLファイル（既定`inspection-params.yml`）を使い、CLI境界で検証する。
テンプレートは既定値を提供し、案件はコードではなくファイルをoverrideする。
`catalog/ga4-sensitivity.yml`と同じ方針である。

```yaml
version: 1
project_id: my-project            # 必須
expected_location: asia-northeast1  # CHK-11の基準
datasets:
  mart_patterns: ["mart_*", "stg_*"]     # 完全な列レベル点検（カバレッジ分母）
  raw_patterns: ["analytics_*"]          # 封じ込めのみ: IAM点検、列点検なし
  exclude: []                            # 明示的な対象外。レポートへ記録
audit:
  high_sensitivity_datasets: []          # FR-3: Data Accessログの唯一の対象
  retention_max_days: 365                # CHK-07シンク出力先の保持上限
thresholds:
  large_table_bytes: 10737418240         # 10 GiB — CHK-08
  long_lived_days: 90                    # CHK-10
  require_cmek: false                    # CHK-11: falseならCMEKなしはINFO、trueならHIGH
catalog_path: catalog/ga4-sensitivity.yml
```

### 2.3 Finding

```
Finding:
  check_id: "CHK-04"          # 安定ID。FR-4の行番号と1対1対応
  severity: HIGH | MEDIUM | LOW | INFO
  resource: "projects/p/datasets/d/tables/t/columns/user_id"   # 正準パス
  observed: "no policy tag"                                    # 観測事実
  expected: "policy tag level=high (catalog: user_id -> high)" # 期待ルール
  rule_ref: "FR-4 #4"
  remediation_hint: "attach policy_tags in the model config"   # 1行の決定論的ヒント
```

出力前にfindingを`(check_id, resource)`で並べ替える。同一スナップショット・パラメータ・
カタログからはバイト単位で同一のレポートを生成する（冪等性、§6）。

## 3. Port（application layer）

| Port | メソッド | 実装 |
|------|----------|------|
| `BigQueryMetadataPort` | `list_datasets`, `get_dataset`, `list_tables`, `get_table` | `infrastructure/gcp/bigquery_metadata.py` |
| `IamPolicyPort` | `get_project_iam_policy` | `resource_manager.py` |
| `TaxonomyPort` | `list_taxonomies(location)` | `data_catalog.py` |
| `LoggingConfigPort` | `list_sinks`, `list_exclusions` | `logging_config.py` |
| `CatalogRepository` | `load() -> SensitivityCatalog` | `yaml_catalog_repository.py` |
| `ParamsRepository` | `load(path) -> InspectionParams` | `yaml_params_repository.py` |
| `ReportWriter` | `write(report, out_dir)` | JSON、CSV、Markdown writer |
| `Clock` | `now() -> datetime` | 実Clock、テストでは固定Clock（TST-010） |

単体テストはbuilderで収集portを偽装する。GCPやネットワークを使わず、決定論的に実行する。

## 4. Deterministic rules

Scope note: "in-scope datasets" = matched by `mart_patterns`; `raw_patterns` datasets
get **containment checks only** (CHK-01/02/03 at dataset grain — per §4.2 they are in
the coverage denominator only for closure confirmation); `exclude` datasets are skipped
and listed with reasons.

| ID | Requirement | Flag when (deterministic rule) | Severity | Inputs |
|----|-------------|--------------------------------|----------|--------|
| CHK-01 | 1 | `roles/owner` or `roles/editor` in project bindings or dataset `access`; `roles/viewer` likewise | HIGH (owner/editor), MEDIUM (viewer) | ProjectIam, DatasetMeta.access |
| CHK-02 | 2 | any member `allUsers` / `allAuthenticatedUsers` in project bindings or dataset access | HIGH | same |
| CHK-03 | 3 | BigQuery data roles (`roles/bigquery.dataViewer/dataEditor/dataOwner/admin`) bound at **project** level (should be dataset/table grain) | MEDIUM | ProjectIam |
| CHK-04 | 4 | column in an in-scope table whose **effective catalog level** (columns ∪ promoted_columns ∪ overrides, FR-1.2) is high/medium and the schema field has no `policyTags` | HIGH (high-level col), MEDIUM (medium) | TableMeta.schema, catalog |
| CHK-05 | 5 | (a) a column references a policy-tag ID not present in any collected taxonomy (dangling); (b) taxonomy location ≠ dataset location of tagged columns (breaks CLS — design doc cross-cutting constraint); (c) taxonomy defines a tag no column uses (orphan) | HIGH (a,b), INFO (c) | schema, Taxonomy |
| CHK-06 | 6 | `audit_configs` enable `DATA_READ`/`DATA_WRITE` for `allServices`, or for `bigquery.googleapis.com` while `audit.high_sensitivity_datasets` is empty; any sink filter ingesting BigQuery data-access entries without restricting to the declared high-sensitivity datasets | MEDIUM | ProjectIam.audit_configs, sinks, params |
| CHK-07 | 7 | (a) no enabled sink whose filter matches BigQuery audit logs (sink未設定); (b) sink destination is a BQ dataset whose `default_table_expiration_ms` is unset or exceeds `retention_max_days` (保持過大); (c) zero enabled exclusions project-wide (除外フィルタ不在) | MEDIUM (a,b), LOW (c) | sinks, exclusions, DatasetMeta |
| CHK-08 | 8 | `num_bytes ≥ large_table_bytes` and neither time nor range partitioning (missing clustering on such tables → INFO) | MEDIUM | TableMeta, thresholds |
| CHK-09 | 9 | partitioned table with `require_partition_filter` false/unset | LOW | TableMeta |
| CHK-10 | 10 | table age (Clock − creation_time) > `long_lived_days` **and** table `expiration_time` unset **and** dataset default expiration unset | LOW | TableMeta, DatasetMeta, Clock |
| CHK-11 | 11 | (a) dataset location ≠ `expected_location`; (b) `default_table_expiration_ms` unset; (c) CMEK unset — severity per `require_cmek` | MEDIUM (a), LOW (b), INFO/HIGH (c) | DatasetMeta, params |
| CHK-12 | FR-9 | table/view description or flattened leaf-column description is missing or whitespace-only in a MART or conservative UNMATCHED dataset | LOW | TableMeta.description, TableMeta.schema |
| CHK-13 | FR-10 | an observed promoted leaf column in a MART or conservative UNMATCHED dataset has a missing or blank catalog `source.field_path` or `source.key` | LOW | TableMeta.schema, catalog promoted_columns |

CHK-01..CHK-11 remain the closed FR-4 security set used by Acceptance B. CHK-12 and
CHK-13 are additive governance checks: they appear in the same deterministic report and
remediation flow but are not counted in the historical 10-of-11 threshold.

### 4.1 Description boundary

- BigQuery table and field descriptions are preserved exactly at the adapter boundary;
  CHK-12 uses `strip()` only to decide whether text is empty.
- Tables and views are evaluated. Nested schemas are evaluated at flattened leaf paths,
  matching the existing column coverage denominator.
- RAW and EXCLUDED datasets are not evaluated. UNMATCHED remains full-inspection scope
  because the existing safe default treats it as MART.
- The check does not grade prose, evaluate source lineage, or inspect row values.
- CHK-13 uses the separate, structured, source-agnostic FR-10 contract; CHK-12 never
  parses free-text descriptions.

### 4.2 Promotion-source boundary

- Only table/view leaf columns observed in the existing REST snapshot are evaluated.
- Catalog `promoted_columns` entries identify candidate target columns. A finding is
  emitted only when that target exists in a MART or conservative UNMATCHED dataset and
  either `source.field_path` or `source.key` is missing or blank.
- RAW and EXCLUDED datasets and catalog entries with no observed target column are
  skipped. This avoids treating reusable catalog declarations as deployed resources.
- The check is source-agnostic and reads no rows, SQL, or description text. A complete
  declaration records intent; it does not prove the transformation's SQL lineage.

Known limitation (recorded, not silently dropped): CHK-07(b) retention is only
verifiable for **BigQuery** sink destinations; GCS bucket lifecycle would need
`storage.buckets.get`, which the A-5 role deliberately does not include. GCS
destinations are reported as `INFO: retention not verifiable with inspector role`.

## 5. Output (FR-5, machine-readable part)

`inspect` produces into `--out-dir` (default `reports/<project>/<timestamp>/`):

- `findings.json` — `{meta: SnapshotMeta+params digest, coverage: {datasets, tables,
  columns, skipped[]}, findings[]}`. Stable key order and finding sort. This is the
  **frame** the A-level AI report generator will consume.
- `findings.csv` — the finding list only, using the fixed serialized field order
  `check_id,severity,resource,observed,expected,rule_ref,remediation_hint`. CSV quoting
  preserves commas, quotes, newlines, and non-ASCII text; UTF-8 bytes and LF endings are
  deterministic. A clean report contains the header and no data rows. JSON remains the
  complete authoritative artifact; parameters, coverage, and skipped details are not
  duplicated into CSV.
- `summary.md` — deterministic template rendering: coverage table, findings grouped by
  check, severity counts. No LLM involved.

Coverage counters implement §4.2's 100%-coverage denominator: every in-scope dataset,
table, and column is either evaluated or listed in `skipped[]` with a reason.

## 6. CLI contract (consumed by bq-inspect.yml later)

```
uv run ga4-bq-inspect --params inspection-params.yml [--out-dir reports/] [--fail-on HIGH]
```

- Exit 0 = ran to completion (findings themselves do not fail the run); `--fail-on`
  optionally gates CI on a severity floor.
- Read-only by construction: the module contains no mutating API call (FR-6 / GR-030).
- Auth: Application Default Credentials — works with `gcloud auth` locally and WIF in
  CI unchanged.

## 7. Toolchain integration

- Root gains `pyproject.toml` managed with **uv** (python-uv profile), dependencies per
  ADR-0003.
- Root Makefile merges python-uv targets with the existing terraform ones:
  `format` = terraform fmt + ruff format; `lint` = terraform fmt-check/tflint + ruff
  check + mypy; `test-unit` = pytest unit tier + terraform fmt-check; `test-integration`
  = terraform test + pytest integration tier; `coverage` = pytest --cov (ratchet,
  TST-003). Contract semantics (profiles/README.md) unchanged.
- New extension target: `make inspect PARAMS=<file>`.

## 8. Delivery plan (GR-020-sized slices)

| PR | Content | ~size |
|----|---------|-------|
| 1 | ADR-0003 + this design + index updates | docs only |
| 2 | pyproject/uv + Makefile python wiring + module skeleton + MODULE.md | small |
| 3 | domain models (snapshot/params/catalog/finding) + builders + unit tests | medium |
| 4 | CHK-01..05 (IAM + column security) + tests | medium |
| 5 | CHK-06..11 (audit + cost + hygiene) + tests | medium |
| 6 | collection adapters + integration tests | medium |
| 7 | use cases + CLI + report writers + E2E against FR-8 verification env | medium |

Each PR lands green and releasable; effort tracks requirements §9.2 (点検エンジン
8–12 person-days: collection 3–4, checks 3–5, report 2–3).

## 9. Open points carried into implementation

1. CHK-06 sink-filter matching: exact BigQuery data-access filter grammar to recognize
   (start with the two house patterns from FR-3 layer 2/3; extend by evidence).
2. ~~`roles/viewer` severity~~ **Settled 2026-07-11 (owner)**: viewer IS detected,
   at MEDIUM; owner/editor stay HIGH (LOG-0014).
3. ~~Placeholder `src/modules/catalog/` deletion~~ **Settled 2026-07-11 (owner)**:
   delete as soon as it is no longer needed — i.e. in the PR that lands the real
   inspection module skeleton (LOG-0014).

## 10. CHK-12 delivery slices

Issue #70 is split to remain within GR-020:

| Slice | Contract |
|-------|----------|
| Specification | FR-9, CHK-12 behavior, Acceptance B preservation, and content/lineage non-scope |
| Reporting compatibility | Accept CHK-12 artifacts and add deterministic AI guidance and a non-applying remediation recipe before the producer emits it |
| Inspection implementation | Collect descriptions, emit CHK-12, and cover adapters/domain boundaries with tests |

Each slice is independently releasable. No GCP resource, API enablement, IAM change, or
new dependency is required. The check reuses existing `tables.get` calls, so fixed
infrastructure cost and incremental BigQuery query-processing cost are both zero.

## 11. CHK-13 delivery slices

Issue #235 is split to remain within GR-020 and to update consumers before producers:

| Slice | Contract |
|-------|----------|
| Specification | FR-10, source-agnostic CHK-13 behavior, Acceptance B preservation, and non-verification boundary |
| Reporting compatibility | Accept CHK-13 artifacts and add deterministic AI guidance and a manual, non-applying remediation recipe before the producer emits it |
| Inspection implementation | Evaluate observed promoted leaf columns, emit CHK-13, and cover the domain and registry boundaries with tests |

Each slice is independently releasable. CHK-13 reuses the catalog and table schema
already loaded by the inspector. It requires no GCP resource, API enablement, IAM
change, query job, row access, or new dependency.
