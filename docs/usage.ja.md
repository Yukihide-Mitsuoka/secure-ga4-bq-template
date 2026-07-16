---
id: usage-ja
title: 使い方（日本語）— 新しいPC / 別アカウント / 新規プロジェクト
updated: 2026-07-17
---

# 使い方（日本語セットアップ手順書）

> English: [usage.md](usage.md) ／ このファイルは人間向けの日本語手順書です（ADR-0002：
> ルール本体は英語、人間向けドキュメントは日本語版を併設可）。内容が英語版と食い違った場合は
> **英語版が正**です。

新しいPCや別のGitHubアカウントで基盤を使うときの手順。**まず2つのシナリオのどちらかを判断**
してください。手順が変わります。

| シナリオ | やりたいこと | 使うもの |
|----------|--------------|----------|
| A | この基盤の上で**新規プロジェクトを作る** | GitHub の **「Use this template」**（`git clone` ではない）|
| B | **この基盤リポジトリ自体**を別マシンで開発継続する | `git clone` |

`git clone` が正解なのはシナリオBだけです。シナリオAでcloneすると、新規プロジェクトにこの基盤の
履歴とプレースホルダが混入します。テンプレート機能を使ってください。

---

## シナリオA — テンプレートから新規プロジェクトを作る

テンプレートリポジトリ化フラグは有効済みなので、1アクション＋短いセットアップで済みます。

### 1. テンプレートから新リポジトリを作成

Web: テンプレートリポジトリを開く → **Use this template** → **Create a new repository**。

CLI（同等）:
```bash
gh repo create <あなたのアカウント>/<新プロジェクト> \
  --template Yukihide-Mitsuoka/ai-dev-foundation \
  --private --clone
cd <新プロジェクト>
```
これで**クリーンな履歴**の新リポジトリがあなたのアカウント配下にできます。

### 2. テンプレートのプレースホルダを置換

カスタマイズ対象はすべて `{{...}}` トークンです。全部洗い出す:
```bash
grep -rn "{{" . --exclude-dir=.git
```
最低限置換するもの: `.ai/mission.md` と `CLAUDE.md` の `{{PROJECT_NAME}}` `{{STACK}}` 等、
`.github/CODEOWNERS` ・`.github/ISSUE_TEMPLATE/config.yml`・
`.github/workflows/template-sync.yml` の `{{ORG}}`、pythonプロファイルを使うなら `{{PACKAGE}}`。

### 3. CODEOWNERS をアカウント種別に合わせて修正

`.github/CODEOWNERS` は既定で**チーム記法**（`@{{ORG}}/maintainers`）です。チームは
**GitHub Organization にしか存在しません**。**個人アカウント**ではユーザー名に置換してください:
```
*   @your-username
```
個人リポジトリにチーム記法を残すと、CODEOWNERS が**黙って無効化**されます
（`scripts/setup-github.sh` は個人アカウントでこの記法を検出すると警告します）。

### 4. Makefile プロファイルを選ぶ

最も近いリファレンス実装をルートにコピーしてスタックに合わせます:
```bash
cp profiles/python-uv/Makefile ./Makefile      # または typescript-node / terraform-gcp
```
正準ターゲット契約は [profiles/README.md](../profiles/README.md) を参照。

### 5. GitHub ガバナンスを点検

```bash
uv run python scripts/github_governance.py validate
uv run python scripts/github_governance.py plan --repo OWNER/REPOSITORY
uv run python scripts/github_governance.py audit --repo OWNER/REPOSITORY
```

`validate` はオフラインです。`plan` と `audit` は認証済みGitHubへ30秒上限のGETだけを行い、
同じ秘匿化済み比較結果を出力します。GitHub設定は変更しません。`plan` は比較完了時、差異や
unknownがあっても0、`audit` は準拠時0・差異/unknown時1・入力/ポリシー/読取エラー時2です。
[GitHubガバナンスのトラブルシューティング](troubleshooting/github-governance.md)も参照。

従来の `scripts/setup-github.sh` は固定内容の初期設定として残っていますが、階層ポリシーの
反映機能ではありません。書込内容を確認して意図的に使ってください。ポリシー駆動の `apply`
は未提供です。

### 6. ローカルゲート導入 → エージェントに向ける

```bash
make setup                             # 依存導入 + pre-commit フック
```
Claude Code でリポジトリを開けば `CLAUDE.md` を自動で読みます。他のエージェントには
`AGENTS.md` を読ませてください。あとは issue を割り当てるだけ。

コードを追加するときは `src/modules/` 配下の既存モジュールの形を真似てください（COD-050）。
かつて同梱していた例モジュール（`src/modules/catalog/`）は実コード着手に伴い削除済みです —
参照が必要なら git 履歴を見てください。いつでも `make doctor` でテンプレートの自己チェック
（frontmatter 整合性 + guard フックのテスト）ができます。

---

## シナリオB — 基盤リポジトリ自体を別マシンにclone

```bash
git clone https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template.git
cd secure-ga4-bq-template
make setup
make doctor
make format
make lint
make test
make build
```
ルートはTerraform＋Pythonの有効なプロファイルです。全正準ターゲットを通す前に、各マシンで
下記の**前提ツール**と**認証**を一度設定してください。

---

## マシンごとの前提ツール（両シナリオ共通）

新しいマシンで一度だけ導入:

| ツール | 用途 | 備考 |
|--------|------|------|
| `git`, `make` | 全般 | — |
| `gh`（GitHub CLI）| GET専用ガバナンス点検・認証 | `gh auth login` |
| `pre-commit` | ローカルコミットゲート | `make setup`（プロファイル導入後）または `pre-commit install` |
| スタックのツールチェーン | build/test | uv(python) / pnpm+node(ts) / terraform(iac) |
| `gitleaks`, `trivy`, `syft` | ローカルの `make security-scan` / `sbom` | ローカルは任意。**CIは常時強制** |

スキャナはローカル任意です。GitHub Actions が全PRで実行するので、未導入でも「ローカルで結果が
見えない」だけです。

---

## 落とし穴（ぶつかる前に読む）

### push には `workflow` OAuth スコープが必要
`.github/workflows/` 配下を含む push はトークンの `workflow` スコープが必要です。
*"refusing to allow an OAuth App to create or update workflow ... without workflow scope"*
と拒否されたら:
```bash
gh auth refresh -h github.com -s workflow
```
これは**アカウント／マシンごと**の設定です。新環境ごとに一度実施する想定でいてください。

### ソロ開発 × 従来の初期設定 ＝ 自分のPRをマージできない
固定の `scripts/setup-github.sh` はレビュー1件をadminにも強制します。階層ポリシーの既定値は、
PR・ステータスチェック・force push禁止を維持しつつ、ソロ開発向けに承認0件です。
従来の初期設定を適用済みなら、どちらか選択:

- **推奨（ガードレール維持）:** 共同開発者/レビュアーを1人追加、または AI レビュアー
  （[ai-review.yml](../.github/workflows/ai-review.yml)）を有効化。ただしAIのレビューコメントは
  GitHub上の *approval* にはならないため、真の自己マージには下の方法が必要。
- **ソロ実用:** PR＋ステータスチェックは維持したままレビュー必須数を0に:
  ```bash
  gh api -X PATCH repos/<owner>/<repo>/branches/main/protection/required_pull_request_reviews \
    -F required_approving_review_count=0
  ```
  これでも「ブランチ＋PR＋CI緑」（GR-010, GR-021）は保たれ、マージだけ自分で行えます。

### 改行コード
`.gitattributes` がリポジトリ全体を LF 強制するので、Windows チェックアウトでもシェルフックと
Makefile は壊れません。グローバル `core.autocrlf=true` でこれと戦わないこと（`.gitattributes` が
対象ファイルでは勝ちますが、Git既定は素直にしておく）。

---

## 質問への回答

### Q. 別アカウントから「Use this template」してよい？ → **可能。1台のPCで完結できます**

テンプレートリポジトリにそのアカウントがアクセスできれば、どのアカウントからでも生成できます。

| テンプレートの公開設定 | 「Use this template」できるアカウント |
|------------------------|----------------------------------------|
| public | 誰でも（あなたの別アカウント含む）|
| private | 読み取り権限を持つアカウント（コラボレーター）／同じ Organization のメンバーのみ |

- 生成先のアカウント／Org はテンプレートのドロップダウンで選べます（テンプレート所有者と別でOK）。
- **結論:** このPC 1台で完結します。アカウントを切り替えて（または同一アカウントで）テンプレート
  → 新リポ生成 → clone → 開発、の流れで複数PCは不要です。
- 秘密情報を含まない基盤なので、再利用が多いなら **public** が最も手軽。厳密に管理したいなら
  **Organization + private** が綺麗です。

### Q. 全リポジトリを束ねる作業ディレクトリへの「グローバル指示」は仕組みとして想定されている？ → **はい（Claude Code の公式機能）**

Claude Code は起動時にディレクトリツリーを遡って `CLAUDE.md` を読み込みます。したがって階層で
グローバル指示を効かせられます（2026-07 時点の公式仕様で確認）:

| スコープ | 場所 | 適用範囲 |
|----------|------|----------|
| 組織管理ポリシー | Linux/WSL: `/etc/claude-code/CLAUDE.md` | マシン上の全セッション・全リポジトリ（個人設定で除外不可）|
| ユーザー | `~/.claude/CLAUDE.md` | あなたの全プロジェクト |
| **束ねる親ディレクトリ** | 例 `~/projects/CLAUDE.md` | **その配下の全リポジトリ**（cwd から親を遡って読む）|
| プロジェクト | `<repo>/CLAUDE.md` ＋ `.ai/` | そのリポジトリのみ（この基盤が提供）|

読み込み順は root 側 → cwd 側で、**cwd に近いものが後に読まれ優先**されやすい。すべて連結して
コンテキストに入ります（上書きではない）。

**推奨する構成:**
- 全リポ共通の「ハウスルール」→ `~/projects/CLAUDE.md`（例: 常に日本語で応答、あなたの名前・役割、
  優先ライブラリ、コミット文体）。**200行以内**に保つ。
- 真に全環境共通 → `~/.claude/CLAUDE.md`。
- 各リポの `.ai/` は**自己完結の正準ルール**のまま（100リポにコピーしても単独で機能し、
  ChatGPT/Gemini でも全ルールが読める）。

**重要な注意:**
- これは **Claude Code 固有**の仕組みです。ChatGPT/Gemini は親/グローバル `CLAUDE.md` を自動では
  読みません。ベンダー中立性のため、**ハードなガードレールは各リポの `.ai/` と PreToolUse フック**
  （この基盤の `guard-bash.sh` がまさにそれ）に置き、グローバル層は「競合しない補助的な好み」に
  留めてください。ハードルールをグローバル層“だけ”に置くと、他所へcloneした/他エージェントが読む
  リポジトリでそのルールが失われます。
- `CLAUDE.md` は「コンテキストであって強制設定ではない」（公式明記）。確実に**ブロック**したい操作は
  PreToolUse フックで実装します。

複数リポで共有したいルール断片は `.claude/rules/` にシンボリックリンクを張る方法も公式サポート
されています（例: `ln -s ~/shared-claude-rules .claude/rules/shared`）。

---

## クイックリファレンス:「別アカウントで clone だけで足りる？」

- **基盤を開発する**（シナリオB）: はい。`git clone` ＋ `make setup` ＋（そのマシンで一度）
  `gh auth refresh -s workflow`。
- **新規プロジェクトを作る**（シナリオA）: いいえ。「Use this template」→ 上の6ステップ。
  cloneでは新規プロジェクトにこの基盤の履歴とプレースホルダが混入します。
