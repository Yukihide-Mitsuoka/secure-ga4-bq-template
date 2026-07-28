---
id: design-ai-report-generator
title: AレベルAI点検レポート生成の実装設計
status: implemented-live-v1-language-extension-designed
updated: 2026-07-28
---

# 実装設計: AレベルAI点検レポート生成

- 状態: スライス1〜7を実装済み。スライス5の実環境証跡は
  [Vertex AI実環境証跡](../verification/2026-07-12-ai-report-live-evidence.md)を参照。
- 言語拡張の状態: Issue #253で設計済み、未実装。本書§10の実装PRがmergeされるまでは
  `REPORT_LANGUAGE`を利用できない。
- 公開エントリーポイント: `make report-ai FINDINGS=<findings.json> [OUT=<directory>]
  [REPORT_LANGUAGE=en|ja]`と
  `make remediation-draft FINDINGS=<findings.json> [OUT=<directory>]`。
- 要件: `requirements-secure-asset.md`のFR-5、§4.2、§7.1、§8のAcceptance A。
- アーキテクチャゲート: [ADR-0004](../adr/0004-isolate-ai-report-generation.md)と
  [ADR-0005](../adr/0005-render-remediation-drafts-from-recipes.md)。
- 入力: Bレベル点検エンジンが決定論で生成した`findings.json`。
- 出力: 顧客が読めるAI説明文と、別ファイルの決定論的・非適用の是正ドラフト。機械可読な
  是正アクションは引き続き対象外とする。

## 1. 受け入れ基準

1. ローカルCLIは1つの`findings.json`を受け取り、1つの`ai-report.md`を書き出す。
2. プロバイダー呼び出し前に入力を検証する。未知のスキーマバージョン、不正なfinding、未対応の
   check IDまたは重大度、上限超過サイズ、不完全なカバレッジは、機密情報を含まないエラーと
   終了コード2で失敗する。
3. プロバイダーへ渡すのは、検証済みレポートフレームだけである。環境ファイル、認証情報、
   テーブル行、GA4の生値、無関係なファイルをプロンプトへ読み込まない。
4. プロバイダーは、仮名化したfinding参照をキーに持つ構造化JSONを返す。生成内容によるfindingの
   追加・削除・重大度変更・解決済み判定を認めない。決定論バリデーターがフレーム外の出力を拒否し、
   ローカルコードがMarkdownを描画する。
5. 出力には、人によるレビューが必要なAI生成ドラフトであることを明記し、対象範囲、カバレッジ、
   エグゼクティブサマリー、findingごとの説明、次のアクションを含める。実行可能な是正処理は含めない。
6. 認証、タイムアウト、レート制限、不正レスポンス、拒否の失敗を明示する。失敗しても決定論的な
   成果物を変更せず、不完全なレポートを残さない。
7. 認証情報はADCまたはWIFの標準認証チェーンから取得し、CLI引数として受け取らず、永続化・ログ出力
   しない。プロンプト本文とレスポンス本文も既定ではログへ出さない。
8. 単体テストは偽プロバイダーを使い、ネットワークへ接続しない。敵対的メタデータ、プロンプト
   インジェクション文字列、出力パス、秘密情報の非開示をセキュリティテストで確認する。
9. AIレポート言語は`en`または`ja`から選択する。既定値は後方互換のため`en`とし、任意文字列を
   言語指示として受け取らない。選択言語はAI生成文とローカル描画する固定見出しの両方へ適用する。

## 2. スコープ

スライス1で実装した範囲:

- 既存`findings.json`形式のバージョン付き入力検証。
- 検証済みフィールドから作る、上限付き・仮名化済みプロンプト。
- プロバイダー非依存のapplication portと、`google-genai`を使うVertex AIアダプター。
- Markdown出力検証、アトミック書き込み、ローカルCLI、テスト、モジュール文書。

後続スライスで実装した範囲:

- 決定論的・非適用の是正ドラフト。
- `gcp-cicd-workflows@v1`とopt-inの`bq-inspect.yml`による再利用ワークフロー統合と成果物アップロード。

Issue #253の言語拡張で実装する範囲:

- AI生成文と`ai-report.md`の固定見出しに対する英語・日本語の選択。
- 既定の英語経路と既存のframe検証を維持した、CLI・Makefileの追加パラメータ。

対象外:

- 機械可読な是正アクション。
- 点検finding、重大度、カバレッジの変更。
- 是正の適用またはPull Requestの作成。
- PII値検査とCloud Run定期実行（A+）。
- BigQueryの行またはGA4イベントの生値をLLMへ送信すること。

## 3. モジュール境界

```text
src/modules/reporting/
  MODULE.md
  domain/
    model.py
    remediation.py
  application/
    ports.py
    generate_ai_report.py
    generate_remediation_draft.py
  infrastructure/
    json_artifact_reader.py
    vertex_ai_generator.py
    markdown_report_writer.py
    markdown_remediation_writer.py
  interface/
    cli.py
    remediation_cli.py
```

このモジュールは`src.modules.inspection`内部へ依存せず、シリアライズ済みの公開成果物を
受け取る。この境界により、プロセスやリポジトリをまたいで契約を利用でき、点検モジュールの
非公開オブジェクトとの結合を防ぐ。

## 4. データとセキュリティの境界

完全な点検成果物はSEC-011の **Internal** として扱う。

- AI生成はopt-inとする。
- 上限を超えるファイルは、解析前に拒否する。
- すべての文字列を命令ではなくデータとして扱い、レコードを構造で区切る。
- 言語は固定enumから選び、利用者が指定した自由記述をプロンプト命令へ追加しない。
- 送信前にプロジェクトIDとリソースIDを決定論的な別名へ置換する。
- 観測値、`catalog_path`、スキップ時のエラー詳細をプロバイダー入力から除外する。
- 最終Markdownの描画時だけ、ローカルで正確な識別子を再結合する。
- 選択した出力ディレクトリ配下の固定ファイル名へアトミックに書き込む。
- 明示的な上書き方針が承認されない限り、既存出力があれば失敗する。
- ログへ残すのは、イベント名、件数、プロバイダー・モデル識別子、所要時間だけとする。
- TLSを検証し、タイムアウトを制限する。現在の実装は自動リトライを行わない。

## 5. プロバイダーport

```text
TextGenerator.generate(payload) -> ProviderText
```

`payload`は、検証済みフレーム、プロンプトテンプレートのバージョン、固定enumから解決した
出力言語コード・言語名を含む。結果は構造化JSON、プロバイダー名、モデル名、取得できる場合は
request IDを含む。プロンプト本文とレスポンス本文は最終レポート以外へ保存しない。

最初のアダプターは、公式`google-genai` SDK、安定版API `v1`、ADC/WIFを通じてVertex AI上の
Geminiを利用する。制限付きタイムアウトとJSONレスポンススキーマを設定し、toolを渡さず、
生成後にSDKクライアントを閉じる。

## 6. 出力と終了コードの契約

`ai-report.md`は、ドラフト注意書き、決定論的な対象範囲・カバレッジ、エグゼクティブサマリー、
変更されていないID・重大度を持つfinding、AIが生成した説明と次のアクション、点検エンジンの
決定論的な是正ヒント、生成メタデータを含む。すべての入力finding参照は正確に1回ずつ現れ、
未知のIDは拒否する。`findings.json`と`summary.md`が監査上の正準である。

| 終了コード | 意味                                                           |
| ---------- | -------------------------------------------------------------- |
| 0          | レポートを生成し、アトミックに書き込んだ                       |
| 1          | プロバイダーまたは生成出力の失敗。決定論的成果物は引き続き有効 |
| 2          | CLI・設定・パスが不正、または入力が不正・未対応                |

## 7. デリバリースライス

| スライス | 内容                                                            | ゲート                                                                          |
| -------- | --------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| 1        | ADR-0004、本設計、索引                                          | 所有者がADRとプロバイダーを承認                                                 |
| 2        | スケルトン、入力domain・スキーマ検証、偽プロバイダー、テスト    | 単体テスト成功                                                                  |
| 3        | ユースケース、プロンプトフレーム、出力バリデーター・writer、CLI | セキュリティテスト成功                                                          |
| 4        | 承認済みプロバイダーアダプターと依存関係                        | lint・test・security scan成功                                                   |
| 5        | 合成findingを使うopt-inの実環境生成                             | 2026-07-12に検証済み                                                            |
| 6        | Terraform・ポリシー是正ドラフトの設計と実装                     | [ADR-0005](../adr/0005-render-remediation-drafts-from-recipes.md)に従い実装済み |
| 7        | 再利用ワークフロー統合                                          | `gcp-cicd-workflows@v1`とopt-inの`bq-inspect.yml` callerで実装済み              |
| 8        | `en` / `ja`のAIレポート言語契約                                 | Issue #253の単体テストと全品質gate                                             |

## 8. 所有者判断

1. 独立した`reporting` bounded context: 承認済み。
2. 初期プロバイダー: `google-genai`とADC/WIFを使うVertex AI上のGemini。
3. プロバイダーへ送るプロジェクト・リソース識別子: 決定論的な仮名。
4. 既存`ai-report.md`: fail closed。上書きオプションを提供しない。
5. 言語: `en`と`ja`だけを許可し、既定値は`en`とする。

## 9. スライス6の是正契約

- 入力: `report-ai`と同じ、完全かつ検証済みの点検成果物。
- 選択: CHK-01〜CHK-13を、それぞれ不変のローカルv1レシピへ対応付ける。
- 信頼するフィールド: レシピ選択には`check_id`だけを使う。レポートにはエスケープ済みのローカル
  リソース識別子とルール識別子を表示する。`observed`、`expected`、`remediation_hint`をコードの
  選択や値設定には使わない。
- 出力: 1つのアトミックかつバイト決定論的な`remediation-draft.md`。既存出力があればfail closed。
  MarkdownなのでTerraformやポリシーツールの自動検出対象にならない。
- 内容: 人によるレビューの注意書き、レシピID・バージョン、必須入力、明示的な`REPLACE_ME_*`値、
  安全に提示できる場合のTerraform・ポリシー例、検証手順。
- 副作用: プロバイダー呼び出し、クラウド変更、Terraform実行、applyコマンド、Pull Request作成を
  行わない。
- CHK-13は承認済みの固定ガイダンスと手動レシピだけを使う。レビュー担当者へ
  `source.field_path`と`source.key`の記入、および変換処理の別途確認を求める。成果物の自由記述から
  SQLリネージを推論または断定しない。

## 10. AIレポート言語契約

| 項目 | `en` | `ja` |
|------|------|------|
| Providerへ渡す固定言語名 | `English` | `Japanese` |
| AI生成対象 | executive summary、explanation、next action | 同左 |
| ローカル描画 | 英語の見出し・注意書き・metadata label | 日本語の見出し・注意書き・metadata label |
| 決定論finding | ID、重大度、resource、rule、是正ヒントを原文のまま保持 | 同左 |

- Makefileは`REPORT_LANGUAGE`をCLIの`--language`へ渡す。
- 未指定時は`en`を使い、既存利用者の呼び出しを維持する。
- CLIは許可値以外をprovider呼び出し前に終了コード2で拒否する。
- 言語指定は、findingの追加・削除・並べ替え・重大度変更を許可しない。
- `remediation-draft.md`は決定論レシピの原文を維持し、本契約の対象外とする。
