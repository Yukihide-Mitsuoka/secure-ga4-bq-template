---
id: requirements-index
title: 要件文書索引
status: maintained
updated: 2026-08-24
---

# 要件文書索引

このディレクトリは、`secure-ga4-bq-template`が満たす要求と、案件ごとに確定する入力を
管理します。システム構造は[システム全体像](../architecture/system-overview.md)、実行方法は
[利用ガイド](../usage.md)、点検内容は[点検ガイド](../inspection.md)を参照してください。

## 顧客要件を実装へ反映する

[顧客要件と実装パラメータ](customer-inputs.md)は、顧客へ確認する事項を次へ対応付けます。

- `engagement-scope.yml`
- `inspection-params.yml`
- Terraform変数
- dbtまたはDataformの設定・SQL
- 機密度カタログ
- GitHub ActionsとAIレポートの実行条件

案件の要件定義では、この文書から始めてください。

## 正式な要件

| 文書 | 所有するテーマ | 状態 |
|------|----------------|------|
| [requirements-secure-asset.md](requirements-secure-asset.md) | 構築・点検モード、セキュリティ統制、CHK-01〜CHK-13 | v1.0 + CHK-12/CHK-13 |
| [requirements-dbt-dataform-rail.md](requirements-dbt-dataform-rail.md) | dbt/Dataform選択、マート構築レール、dry-run費用gate | v1.0 |
| [requirements-service-packaging.md](requirements-service-packaging.md) | 標準点検メニュー、適合判定、サービスpresetとoption | v1.2草案 |

## 現在の実装設計

| 文書 | 所有するテーマ | 状態 |
|------|----------------|------|
| [design-modules-wif-wiring.md](design-modules-wif-wiring.md) | Terraform module、deployer／inspector WIF、CI接続 | baseline v1実装済み |
| [design-inspection-engine.md](design-inspection-engine.md) | snapshot、CHK-01〜CHK-13、CLIとreport契約 | CHK-13まで実装済み |
| [design-ai-report-generator.md](design-ai-report-generator.md) | AI入力制限、provider境界、英語・日本語の説明草案 | 実環境v1実装済み |

実装設計3文書は、受け入れ済みADRの既存リンクを維持しながら`docs/architecture/`へ移す
必要があります。この移動は[Issue #326](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/326)
の後続PRで扱います。

## 文書の読み方

- 顧客要求の意味は要件文書が所有し、実装都合で変更しません。
- 点検checkpoint、費用gate、適合判定は決定論的な処理が決めます。
- AIは任意の説明草案だけを作り、点検結果や重大度を変更しません。
- 完全な点検成果物はInternalであり、公開リポジトリへcommitしません。
