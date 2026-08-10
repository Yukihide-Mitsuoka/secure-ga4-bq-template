---
id: adr-0012
title: ADR-0012 — intermediateレイヤーを明示的に任意化する
status: proposed
updated: 2026-08-10
---

# ADR-0012: intermediateレイヤーを明示的に任意化する

| Field | Value |
|-------|-------|
| Status | proposed |
| Date | 2026-08-10 |
| Deciders | repository owner |
| Author | Codex (AI agent) |
| Supersedes / Superseded by | — |

## Context

現行のTerraformは`staging`、`intermediate`、`marts`の3 Datasetを常に作成する。一方、
同梱するdbt/Dataformサンプルは`staging -> marts`で完結し、`int_*`モデルを持たない。
`intermediate`は、複数マートで共有する計算や複雑な結合を分離するときには有効だが、
単純な変換へ一律に挟むと空のDataset、不要な設定、誤った必須要件を生む。

設計は次の制約を満たす必要がある。

1. `staging`と`marts`は標準の必須境界として維持する。
2. 単純な案件は`staging -> marts`、必要な案件だけ`staging -> intermediate -> marts`とする。
3. 既存利用者がv2更新だけでDataset削除を計画される変更を避ける。
4. Datasetを省略したとき、output、IAM、cost gateにも存在しない層を残さない。
5. 任意名称・任意個数のレイヤー基盤へ一般化せず、現在の検証可能な契約を保つ。

## Options considered

### Option 1: 3 Datasetを常に作成する

- Pros: 現行契約を一切変更せず、Terraform stateへの影響がない。
- Cons: モデルがない案件にも空Datasetを作り、3層必須という誤解と設定負担を残す。

### Option 2: v2のデフォルトからintermediateを削除する

- Pros: 新規利用者の最小構成がそのまま`staging`と`marts`になる。
- Cons: 既定値で利用中の環境では、更新後のplanが既存Dataset削除を提示し得る。データを
  含む可能性のあるresourceをminor updateで削除対象にするため採用できない。

### Option 3: 後方互換を保ってintermediateを任意化する — chosen

`layer_dataset_ids.intermediate`をoptionalにするが、変数全体のv2既定値には従来どおり
`intermediate = "intermediate"`を残す。案件が`staging`と`marts`だけのobjectを明示した
場合に限り、intermediate Datasetと関連IAMを作成しない。

- Pros: 既存環境のplanを変えず、新規・単純案件は明示的に最小構成を選べる。出力と権限を
  実際に作成するDataset集合から導出できる。
- Cons: v2の変数を未指定にした新規環境では、互換性のため引き続き3 Datasetを作る。
  最小構成には明示的な入力が必要になる。

### Option 4: 任意のレイヤーmapへ一般化する

- Pros: 任意個数・任意名称のモデリング規約へ対応できる。
- Cons: 固定した命名、IAM、profile、テストの契約を弱め、現在の要求を超えて誤設定面を
  広げる。実需要のない投機的一般化になるため採用しない。

## Decision

Option 3を採用する。`staging`と`marts`は必須、`intermediate`は任意とする。
`layer_dataset_ids`のobject型では`intermediate`をoptional属性にし、変数全体の既定値は
従来の3 IDを維持する。利用者はobjectから`intermediate`を省くことで明示的に無効化する。

TerraformはnullでないIDから有効レイヤー集合を一度だけ導出し、Dataset module、output、
cost-gate dataset IAMのすべてで同じ集合を使わなければならない。無効なレイヤーの
`layer_iam_members`が指定された場合はvalidationで拒否する。IDの文字種・長さ・一意性は
有効なIDだけを対象に従来どおり検証する。

dbt/Dataform profileは`int_*`モデルを追加できる規約を維持するが、標準サンプルと利用手順は
`staging -> marts`を最小経路として示す。既存のintermediate Datasetを無効化する操作は、
利用者が対象Datasetの内容とTerraform planを確認して明示的に入力を変更する場合に限る。
自動migrationや既存resourceの削除は行わない。

## Consequences

**Positive:**

- 単純な案件は不要なDatasetとIAMを作らず、構成を理解しやすくできる。
- 複雑な案件は従来の3層構成を維持できる。
- v2の既定値を使う既存環境にはresource差分を発生させない。
- outputとcost-gate権限が作成済みDataset集合と一致する。

**Negative:**

- 「既定値は3層、推奨最小入力は2層」という移行期間中の説明が必要になる。
- object属性のnull除外とIAM整合validationがTerraformに加わる。
- 既存Datasetを省略へ切り替える利用者は、削除前にデータとplanを確認する必要がある。

**Migration and rollback:**

1. expand: optional属性と有効レイヤー集合を追加し、既定の3 Datasetを維持する。
2. migrate: 新規案件の例を2 Datasetへ更新し、必要な案件だけintermediateを追加する。
3. contract: v2では既定値からintermediateを削除しない。将来変更する場合はmajor releaseの
   別ADRで、state migrationと削除防止策を決める。

実装を戻す場合は属性をrequiredへ戻して3 Dataset固定契約を復元する。既定値利用者には
resource差分がなく、2 Dataset入力を採用した利用者だけがintermediateを再度指定する。

**Follow-ups:**

- repository ownerが本ADRを承認した後、Issue #318を別PRで実装する。
- Terraform contract test、変数例、dbt/Dataform利用手順、system overview、handoffを更新する。
- 静的な`terraform validate`とunit testで2層・3層の契約を検証し、GCP resourceは作らない。
