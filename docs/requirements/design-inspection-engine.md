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

## 4. 決定論チェック

本節で「点検対象データセット」とは、`mart_patterns`に一致するデータセットを指す。
`raw_patterns`に一致するデータセットには **封じ込めチェックだけ** を適用する。データセット粒度の
CHK-01〜03を実行し、要件§4.2のカバレッジ分母には封じ込め確認の完了を示す目的でだけ含める。
`exclude`のデータセットは点検を省略し、理由とともに記録する。

| ID | 要件 | findingを出す条件（決定論ルール） | 重大度 | 入力 |
|----|------|-----------------------------------|--------|------|
| CHK-01 | 1 | プロジェクトbindingまたはデータセット`access`に`roles/owner`か`roles/editor`がある。`roles/viewer`も検出する | HIGH（owner/editor）、MEDIUM（viewer） | ProjectIam、DatasetMeta.access |
| CHK-02 | 2 | プロジェクトbindingまたはデータセットaccessに`allUsers` / `allAuthenticatedUsers`がある | HIGH | 同上 |
| CHK-03 | 3 | データセット・テーブル粒度にすべきBigQueryデータロール（`roles/bigquery.dataViewer/dataEditor/dataOwner/admin`）が **プロジェクト** 粒度で付与されている | MEDIUM | ProjectIam |
| CHK-04 | 4 | 点検対象テーブルの列について、**effective catalog level**（columns ∪ promoted_columns ∪ overrides、FR-1.2）がhigh/mediumであり、schema fieldに`policyTags`がない | HIGH（high列）、MEDIUM（medium列） | TableMeta.schema、catalog |
| CHK-05 | 5 | (a) 収集したtaxonomyに存在しないpolicy tag IDを列が参照している（dangling）、(b) taxonomyのlocationとtag付き列のデータセットlocationが異なる（横断的制約であるCLSが機能しない）、(c) taxonomyにどの列からも使われていないtagがある（orphan） | HIGH（a、b）、INFO（c） | schema、Taxonomy |
| CHK-06 | 6 | `audit_configs`が`allServices`の`DATA_READ` / `DATA_WRITE`を有効にしている。または`audit.high_sensitivity_datasets`が空の状態で`bigquery.googleapis.com`について有効にしている。あるいはsink filterが、宣言した高機密データセットに限定せずBigQuery data-access entryを取り込んでいる | MEDIUM | ProjectIam.audit_configs、sinks、params |
| CHK-07 | 7 | (a) BigQuery監査ログに一致する有効なsinkがない、(b) sink転送先がBigQueryデータセットで、その`default_table_expiration_ms`が未設定または`retention_max_days`を超える、(c) プロジェクト全体で有効なexclusionがない | MEDIUM（a、b）、LOW（c） | sinks、exclusions、DatasetMeta |
| CHK-08 | 8 | `num_bytes ≥ large_table_bytes`かつ時間・範囲パーティションのいずれもない。該当テーブルにclusteringもなければINFOも出す | MEDIUM | TableMeta、thresholds |
| CHK-09 | 9 | パーティションテーブルの`require_partition_filter`がfalseまたは未設定 | LOW | TableMeta |
| CHK-10 | 10 | テーブル経過日数（Clock − creation_time）が`long_lived_days`を超え、かつテーブル`expiration_time`とデータセット既定期限がどちらも未設定 | LOW | TableMeta、DatasetMeta、Clock |
| CHK-11 | 11 | (a) データセットlocationが`expected_location`と異なる、(b) `default_table_expiration_ms`が未設定、(c) CMEKが未設定。cの重大度は`require_cmek`に従う | MEDIUM（a）、LOW（b）、INFO/HIGH（c） | DatasetMeta、params |
| CHK-12 | FR-9 | MARTまたは安全側にMARTとして扱うUNMATCHEDデータセットで、テーブル・viewのdescription、または平坦化したleaf列のdescriptionが未設定か空白だけである | LOW | TableMeta.description、TableMeta.schema |
| CHK-13 | FR-10 | MARTまたは安全側にMARTとして扱うUNMATCHEDデータセットで観測した昇格leaf列について、catalogの`source.field_path`か`source.key`が未設定または空白である | LOW | TableMeta.schema、catalog promoted_columns |

CHK-01〜CHK-11は、Acceptance Bで使用する閉じたFR-4セキュリティ集合として維持する。
CHK-12とCHK-13は追加のガバナンスチェックである。同じ決定論レポートと是正フローに含めるが、
過去の「11項目中10項目」の閾値には算入しない。

### 4.1 Descriptionの境界

- BigQueryのテーブル・field descriptionは、アダプター境界で原文のまま保持する。CHK-12は
  空かどうかの判定にだけ`strip()`を使用する。
- テーブルとviewを評価する。nested schemaは既存の列カバレッジ分母と同じく、平坦化したleaf
  pathで評価する。
- RAWとEXCLUDEDデータセットは評価しない。UNMATCHEDは既存の安全側の既定動作でMARTとして
  扱うため、完全な点検対象に残す。
- 文章の品質評価、source lineageの評価、行値の検査は行わない。
- CHK-13は独立した構造化済み・source非依存のFR-10契約を使用する。CHK-12は自由記述の
  descriptionを解析しない。

### 4.2 昇格元情報の境界

- 既存のREST snapshotで観測したテーブル・viewのleaf列だけを評価する。
- Catalogの`promoted_columns` entryから候補となるtarget列を特定する。MARTまたは安全側に扱う
  UNMATCHEDデータセットにtargetが存在し、`source.field_path`か`source.key`が未設定または
  空白の場合だけfindingを出す。
- RAW・EXCLUDEDデータセットと、target列を観測していないcatalog entryは省略する。これにより、
  再利用可能なcatalog宣言をデプロイ済みリソースとして扱うことを避ける。
- このチェックはsource非依存であり、行、SQL、descriptionテキストを読み取らない。完全な宣言は
  意図を記録するが、変換SQLのlineageを証明するものではない。

既知の制約として、CHK-07(b)の保持期間を検証できるのは **BigQuery** sink転送先だけである。
GCSバケットのライフサイクル検証には`storage.buckets.get`が必要だが、A-5ロールは意図的に
この権限を含めていない。GCS転送先は、バケットのライフサイクルを点検ロールで読み取れないことを
INFO findingとして報告する。

## 5. 出力（FR-5の機械可読部分）

`inspect`は`--out-dir`配下（既定値`reports/<project>/<timestamp>/`）に次を生成する。

- `findings.json`: `{meta: {project_id, captured_at, params}, coverage: {datasets, tables,
  columns, skipped[]}, findings[]}`。key順とfinding順は安定している。AレベルのAIレポート生成器が
  消費する **フレーム** である。
- `findings.csv`: finding一覧だけを、固定されたfield順
  `check_id,severity,resource,observed,expected,rule_ref,remediation_hint`で出力する。CSVのquoteにより
  カンマ、引用符、改行、非ASCII文字を保持し、UTF-8 byteとLF改行を決定論的に生成する。
  findingがない場合はheaderだけとなる。完全な正準成果物は引き続きJSONであり、parameter、
  coverage、skippedの詳細はCSVに重複させない。
- `summary.md`: coverage表、check別finding、重大度件数を決定論テンプレートで描画する。
  LLMは使用しない。

カバレッジカウンターは要件§4.2の100%カバレッジ分母を実装する。点検対象のデータセット、テーブル、
列はすべて、評価するか、理由付きで`skipped[]`に記録する。

## 6. CLI契約

正準エントリーポイントは次のとおりである。

```bash
make inspect PARAMS=inspection-params.yml OUT=reports
```

同じCLIを直接呼び出す場合は、次の契約に従う。

```bash
uv run python -m src.modules.inspection.interface.cli \
  --params inspection-params.yml --out-dir reports [--fail-on HIGH]
```

- 完了時の終了コードは0とする。finding自体は実行失敗にしない。`--fail-on`を指定した場合だけ、
  指定した重大度以上のfindingをCI gateとして終了コード1にする。
- 構造上読み取り専用であり、モジュールに変更系API callは含まれない（FR-6 / GR-030）。
- 認証にはApplication Default Credentialsを使う。ローカルの`gcloud auth`とCIのWIFで同じ
  コード経路を使用する。

## 7. ツールチェーン統合

- ルートの`pyproject.toml`は **uv**（python-uv profile）で管理し、依存関係はADR-0003に従う。
- ルートMakefileは既存のTerraform targetとpython-uv targetを統合する。`format`はterraform fmtと
  ruff format、`lint`はterraform fmt-check・tflint・ruff check・mypy、`test-unit`はpytest unit
  tierとterraform fmt-check、`test-integration`はterraform testとpytest integration tier、
  `coverage`はpytest --covによるratchet（TST-003）を実行する。`profiles/README.md`の契約上の
  意味は変更しない。
- 拡張targetとして`make inspect PARAMS=<file>`を提供する。

## 8. デリバリー計画（GR-020に収まる分割）

以下の7つのPRはすべて実装済みである。

| PR | 内容 | 規模 |
|----|------|------|
| 1 | ADR-0003、本設計、index更新 | 文書のみ |
| 2 | pyproject/uv、MakefileのPython接続、module skeleton、MODULE.md | 小 |
| 3 | domain model（snapshot/params/catalog/finding）、builder、単体テスト | 中 |
| 4 | CHK-01〜05（IAM・列セキュリティ）とテスト | 中 |
| 5 | CHK-06〜11（監査・費用・衛生状態）とテスト | 中 |
| 6 | 収集アダプターとintegration test | 中 |
| 7 | ユースケース、CLI、report writer、FR-8検証環境に対するE2E | 中 |

各PRはgreenかつリリース可能な状態で導入した。工数は要件§9.2の点検エンジン8〜12人日に対応する
（収集3〜4、チェック3〜5、レポート2〜3）。

## 9. 実装時の検討事項

1. CHK-06のsink-filter照合: 認識するBigQuery data-access filter文法は、FR-3 layer 2/3の2つの
   標準パターンから開始し、証跡に基づいて拡張する。
2. ~~`roles/viewer`の重大度~~ **2026-07-11にownerが決定済み**: viewerをMEDIUMとして検出する。
   owner/editorはHIGHのままとする（LOG-0014）。
3. ~~placeholder `src/modules/catalog/`の削除~~ **2026-07-11にownerが決定済み**: 実際の
   inspection module skeletonを導入するPRで不要になった時点で削除する（LOG-0014）。

## 10. CHK-12のデリバリー分割

Issue #70はGR-020に収めるため、次のように分割して実装した。

| 分割 | 契約 |
|------|------|
| 仕様 | FR-9、CHK-12の動作、Acceptance Bの維持、内容・lineageを対象外とする境界 |
| レポート互換性 | producerが出力する前にCHK-12成果物を受け入れ、決定論的なAIガイダンスと自動適用しない是正手順を追加する |
| 点検実装 | descriptionを収集してCHK-12を出力し、アダプター・domain境界をテストする |

各分割は独立してリリース可能である。GCPリソース、API有効化、IAM変更、新規依存関係は不要である。
既存の`tables.get` callを再利用するため、固定インフラ費用と追加のBigQueryクエリ処理費用は
いずれも0である。

## 11. CHK-13のデリバリー分割

Issue #235はGR-020に収め、producerより先にconsumerを更新するため、次のように分割して実装した。

| 分割 | 契約 |
|------|------|
| 仕様 | FR-10、source非依存のCHK-13動作、Acceptance Bの維持、検証しない範囲の境界 |
| レポート互換性 | producerが出力する前にCHK-13成果物を受け入れ、決定論的なAIガイダンスと手動・自動適用しない是正手順を追加する |
| 点検実装 | 観測した昇格leaf列を評価してCHK-13を出力し、domain・registry境界をテストする |

各分割は独立してリリース可能である。CHK-13は、点検時に読み込み済みのcatalogとtable schemaを
再利用する。GCPリソース、API有効化、IAM変更、query job、行アクセス、新規依存関係は不要である。
