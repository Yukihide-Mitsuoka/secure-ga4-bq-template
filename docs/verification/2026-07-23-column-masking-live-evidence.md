---
id: verification-column-masking-live
title: 列マスキングのライブ検証証跡
status: executed 2026-07-23
updated: 2026-07-23
---

# 列マスキングのライブ検証証跡

Issue [#232](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/232)
で、条件付きオプションだったBigQuery列マスキングを疑似データで実証した。cleartext、
masked、deniedの3経路が期待どおりに分離され、検証用クラウドリソースと過去検証の
残存物はすべて削除された。

## 承認境界

| 項目 | 承認内容 |
| --- | --- |
| 検証プロジェクト | `adr-tfstate-bf1d` |
| データ | 疑似メール2行のみ。顧客データなし |
| 費用上限 | 1,000円 |
| クエリ上限 | 1 jobあたり10,485,760 bytes |
| 許可リソース | 専用Dataset、Table、Policy Tag、Data Policy、一時SA、最小IAM |
| 禁止サービス | Cloud DLP、Vertex AI |
| 共有プロジェクト | `adr-main-application`は本リポジトリ由来と断定できる残存物だけを削除 |

両プロジェクトは同一Organizationに属する。検証前の`adr-tfstate-bf1d`には通常の
BigQuery Datasetがなく、既存SA 1件とGCSバケット2件が存在した。この3件はTerraform
管理対象へ入れなかった。

## 構築

一時ローカルstateのTerraform planは`20 add / 0 change / 0 destroy`だった。作成物は
次の専用境界だけである。

- `secure_ga4_bq_mask_232` Datasetと`synthetic_customers` Table
- `secure-ga4-bq-mask-232` taxonomyと`high` policy tag
- `EMAIL_MASK` data policy
- clear、masked、deniedの一時reader SA
- Dataset Data Viewer、BigQuery Job User、Policy Tag Fine-Grained Reader、Data Policy
  Masked Reader、SA単位Token Creator

Data Catalog APIは検証のため一時的に有効化した。apply後の再planは差分0だった。

## 実証結果

`synthetic_customers.email`だけに`high` policy tagを付け、`record_id`と`note`を非保護
対照列にした。

| 経路 | Policy権限 | 観測結果 | 判定 |
| --- | --- | --- | --- |
| clear reader | Policy Tag Fine-Grained Reader | `alice@example.test`、`bob@example.test` | PASS |
| masked reader | Data Policy Masked Reader | 2行とも`XXXXX@example.test` | PASS |
| denied reader | なし | Policy Tag付き`email`列でAccess Denied | PASS |

masked jobのBigQuery統計は`dataMaskingApplied=true`だった。clearとmaskedの両経路で
非保護`note`列は同じ値を返したため、Datasetアクセスではなく列Policy境界による差を
確認できた。SA鍵は作成せず、interactive userからの短時間impersonationだけを使った。

## クエリ量と費用境界

| job | processed bytes | billed bytes | 結果 |
| --- | ---: | ---: | --- |
| 疑似2行INSERT | 0 | 0 | 2行作成 |
| interactive clear対照 | 100 | 10,485,760 | 成功 |
| clear reader | 100 | 10,485,760 | 成功 |
| masked reader | 100 | 10,485,760 | 成功 |
| denied reader | 0 | 0 | 期待どおり拒否 |
| **合計** | **300** | **31,457,280** | 上限内 |

INSERT dry runは0 bytesだった。各実行には`maximumBytesBilled=10,485,760`を設定した。
請求額そのものは取得していないが、処理量は承認済み上限を満たす。

## Teardownと残存確認

保存したdestroy planは`0 add / 0 change / 20 destroy`で、作成した専用リソースだけを
対象とした。適用結果は`20 destroyed`、Terraform stateは空、再destroy planは差分0
だった。Data Catalog APIは検証前と同じ無効状態へ戻した。

BigQuery query jobは結果を匿名Datasetへ保存する。`bq ls -a`で今回の4 Datasetを検出
し、所有readerを一時復元する必要があった2件を含めて削除した。その後の確認結果は
次のとおりである。

| 確認対象 | 結果 |
| --- | --- |
| `adr-tfstate-bf1d` BigQuery Dataset（非表示含む） | 0件 |
| 検証用active SA / project IAM / Cloud Asset | 0件 |
| 既存SA | `terraform-org-manager` 1件を維持 |
| 既存GCS | 2バケットを維持 |
| Data Catalog API | 無効へ復元 |
| BigQuery / BigQuery Data Policy API | 検証前から有効のため維持 |

`adr-main-application`では通常一覧に出ない過去検証の匿名Dataset 4件を追加で発見した。
作成時刻、location、所有主体が2026-07-11のsecure mart E2E、2026-07-14のcost gate、
2026-07-15のAcceptance Aと一致したため、本リポジトリ由来と判定して削除した。最終的に
同プロジェクトも非表示を含むBigQuery Dataset、検証用active SA、検証用active IAMが
0件となった。既存アプリのWIF、SA、API、その他リソースは変更していない。

## 制約と受け入れ判定

- 疑似データによる技術実証であり、顧客案件またはAcceptance Sの証跡ではない。
- interactive ADCからのimpersonation経路を使い、GitHub Actions WIFは実行していない。
- `EMAIL_MASK`だけを実証し、他のpredefined expressionはTerraform入力検証の対象に
  とどまる。
- BigQuery job履歴は監査証跡として残る。Dataset、Table、IAM、SAではない。

**列マスキングのオプトイン技術受け入れ: PASS。** 標準プリセットの既定値は無効の
ままとし、案件ごとのデータアクセス・費用承認後にだけ有効化する。
