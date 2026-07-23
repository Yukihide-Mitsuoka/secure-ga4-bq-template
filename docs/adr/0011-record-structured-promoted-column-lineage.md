---
id: adr-0011
title: ADR-0011 — 昇格列の出所を構造化カタログで記録する
status: proposed
updated: 2026-07-23
---

# ADR-0011: 昇格列の出所を構造化カタログで記録する

| Field | Value |
|-------|-------|
| Status | proposed |
| Date | 2026-07-23 |
| Deciders | repository owner |
| Author | Codex (AI agent) |
| Supersedes / Superseded by | — |

## Context

マートでは、GA4の `event_params` のようなネストしたkey-valueから必要な値を
型付き列へ昇格する。現在の感度カタログは昇格後の列名と機密度を記録するが、
昇格前のフィールドパスと元キーを明示的な項目として記録できない。出所が不明な
列は、レビュー時に変換SQLまでたどらなければ意味と保護要件を確認できず、案件を
またいだ再利用時に誤ったキーを同名列へ割り当てるリスクがある。

CHK-12はBigQueryネイティブのtable/view/leaf-column `description` が存在するかだけを
点検し、文章内容を解析または採点しない。この境界はLOG-0020で意図的に定められた。
元キーをdescriptionへ埋め込み機械解析すると、人向け文言の修正が点検結果を変え、
既存契約を破る。

設計は次の制約を満たす必要がある。

1. GA4を最初の利用例としつつ、ドメイン契約は任意の元フィールドパスとキーを扱う。
2. 行データ、顧客識別子、SQL本文を読み取らない。
3. 既存のRESTメタデータ収集だけを使い、BigQuery query jobやGCP書き込みを増やさない。
4. FR-4の11観点とAcceptance Bの分母、およびCHK-12の意味を変更しない。
5. 既存のversion 1感度カタログを直ちに壊さず、段階的に移行できる。
6. 設定変更だけで案件差分を表現し、同じ情報を複数ファイルへ重複させない。

## Options considered

### Option 1: 何もしない

元キーは変換SQLとレビュー担当者の知識から確認する。

- Pros: コード、設定スキーマ、点検項目を増やさず、現在の利用者に影響しない。
- Cons: 出所が機械可読にならず、レビューの再現性がない。同名の昇格列と元キーの
  取り違えを点検できず、案件再利用時の引き継ぎ品質を改善しない。

### Option 2: BigQuery descriptionへ規約文字列を埋め込んで解析する

例えばdescription内の `source_key=page_location` のような文字列をCHK-12または
新しい点検で解析する。

- Pros: BigQuery画面だけで人と点検エンジンが同じ情報を参照でき、追加設定ファイルが
  不要になる。
- Cons: 自由記述と機械契約を混在させ、文言変更、表記揺れ、エスケープで誤検知する。
  CHK-12の「存在だけを確認し内容を解析しない」契約とLOG-0020に反する。BigQuery固有の
  表現へ強く結合し、ロールバック時にdescriptionから規約文字列を除去する作業も生じる。

### Option 3: 独立したlineageファイルを追加する

感度カタログとは別のYAMLに、昇格後の対象列、元フィールドパス、元キーを記録する。

- Pros: 感度とlineageの責務が明確で、既存カタログスキーマを変更しない。将来、
  感度を持たない列の出所にも拡張しやすい。
- Cons: 昇格対象列を2ファイルへ重複記載し、名称変更や追加時にドリフトする。現在の
  forcing problemは感度カタログが既に管理する昇格列に限定され、独立した汎用lineage
  製品を先に設計するのはCOD-051の投機的一般化になる。

### Option 4: 感度カタログの昇格列を構造化する — chosen

version 2感度カタログの `promoted_columns` を、対象列ごとに `level` と構造化された
`source.field_path` / `source.key` を持つ形へ拡張する。値はGA4に限定せず、例えば
`event_params` / `page_location` や任意のネスト元を表現できる。元情報が欠けた
宣言は追加の点検結果として報告する。

- Pros: 機密度と出所を対象列1か所で管理でき、案件パラメータの変更だけで適用できる。
  descriptionを解析せず、純粋関数による決定論的点検を維持する。既存のinspection
  bounded context内に収まり、新しいモジュール、依存関係、クラウドAPIを増やさない。
- Cons: 感度カタログの公開スキーマが変わり、version 1互換読込が必要になる。感度を
  持たない一般lineageは対象外のままである。宣言の完全性は確認できても、変換SQLが
  実際にそのキーを読んだことまでは証明できない。

## Decision

Option 4を採用する。inspection moduleはversion 2感度カタログの
`promoted_columns`について、対象列、機密度、元フィールドパス、元キーを構造化して
扱わなければならない。元フィールドパスと元キーは任意の文字列であり、GA4、
`event_params`、または特定ベンダーをドメイン型の固定値にしてはならない。
対象列キーは既存カタログと同じflattened leaf-column path照合を使う。

```yaml
version: 2
levels: [high, medium, low]
promoted_columns:
  page_location:
    level: high
    source:
      field_path: event_params
      key: page_location
```

この例の値は同梱GA4カタログのデータであり、スキーマの固定値ではない。

新しいCHK-13は、MARTまたは安全側に倒したUNMATCHED scopeで実在する昇格対象の
table/view leaf列について、構造化された元フィールドパスまたは元キーが欠落・空白なら
findingを返さなければならない。description本文、行データ、SQL本文は解析しては
ならない。CHK-13は追加のデータガバナンス観点であり、FR-4のCHK-01..CHK-11と
Acceptance B分母、CHK-12の意味を変更してはならない。

version 1の `promoted_event_params` は互換readerで、元フィールドパスを
`event_params`、元キーを既存のマッピングキーとして決定論的に変換する。version 2を
書き出したり既定カタログを移行した後も、version 1 readerは2.xの全期間で維持する。
削除は最短でも3.0.0の明示的breaking changeとし、既存カタログを暗黙に書き換えない。

点検結果と文書は、CHK-13が「宣言の完全性」を確認するもので、変換SQLや実データの
lineage正当性を証明しないことを明示しなければならない。実変換との一致を検証する機能は
利用者の需要と信頼できる変換manifestが確認されるまで実装しない。

## Consequences

**Positive:**

- 昇格列の元キーがレビュー可能な案件パラメータとして明示される。
- GA4の高需要な利用例を扱いながら、実装は任意のネスト元に再利用できる。
- 点検は既存snapshot上の純粋関数で完結し、追加API、BQ処理bytes、GCPリソース、
  認証権限を必要としない。
- descriptionは人向け文章のまま保たれ、CHK-12の安定性を維持する。

**Negative:**

- カタログにversion 2 schemaと互換readerが増え、少なくとも1 major versionは2形式を
  テストする必要がある。
- CHK-13追加によりinspection registry、service packageの標準チェック一覧、出力例を
  同時に更新する必要がある。
- 宣言自体が誤っていても、BigQuery metadataだけでは検出できない。
- 感度カタログ外の一般的なcolumn lineageは解決しない。

**Migration and rollback:**

1. expand: version 1を維持したままversion 2 domain modelとreaderを追加する。
2. migrate: 既定カタログをversion 2へ移し、GA4例では元キーを明示する。
3. expand: CHK-13、registry、service profile、report/documentationを追加する。
4. contract: version 1 reader削除は利用状況を確認し、最短でも3.0.0でのみ検討する。

実装前へ戻す場合は、既定カタログをversion 1へ戻し、CHK-13とversion 2 readerを
削除する。GCP state、永続データ、descriptionの移行は不要である。

**Follow-ups:**

- repository ownerが本ADRを承認した後、Issue #235を上記のexpand/migrate順で実装する。
- `MODULE.md`、inspection design、service packaging profile、catalog利用手順、report
  契約、roadmap、development handoffを更新する。
- 追加・変更前後で単体テスト、決定論的JSON/CSV/Markdown出力、既存version 1 fixture
  の互換性を検証する。
