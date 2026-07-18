---
id: usage
title: Usage — New Machine, New Account, New Project
updated: 2026-07-18
---

# Usage

> 日本語版: [usage.ja.md](usage.ja.md)（人間向けセットアップ手順書）

This guide covers using the foundation from a different machine or a different GitHub
account. **First decide which of two scenarios you are in — the steps differ.**

| Scenario | You want to... | Use |
|----------|----------------|-----|
| A | Start a **new project** built on this foundation | GitHub **"Use this template"** (not `git clone`) |
| B | Continue developing **this foundation itself** on another machine | `git clone` |

`git clone` alone is only the right answer for Scenario B. For Scenario A, cloning would
drag this repo's history and identity into your new project; use the template flow.

---

## Scenario A — start a new project from the template

The template repository flag is enabled, so this is one action plus a short setup.

### 1. Create the new repo from the template

Web: open the template repo → **Use this template** → **Create a new repository**.

CLI (equivalent):
```bash
gh repo create <your-account>/<new-project> \
  --template Yukihide-Mitsuoka/ai-dev-foundation \
  --private --clone
cd <new-project>
```
This gives you a **fresh repo with clean history** under your account.

### 2. Replace template placeholders

Every customizable value is a `{{...}}` token. Find them all:
```bash
grep -rn "{{" . --exclude-dir=.git
```
Replace at minimum: `{{PROJECT_NAME}}`, `{{STACK}}` and the other `{{...}}` in
`.ai/mission.md` and `CLAUDE.md`; `{{ORG}}` in `.github/CODEOWNERS`,
`.github/ISSUE_TEMPLATE/config.yml`, and `.github/workflows/template-sync.yml`;
`{{PACKAGE}}` if you use the python profile.

### 3. Fix CODEOWNERS for your account type

`.github/CODEOWNERS` ships with **team** references (`@{{ORG}}/maintainers`). Teams only
exist under **GitHub Organizations**. On a **personal account**, replace them with your
username:
```
*   @your-username
```
Leaving team syntax on a personal repo makes CODEOWNERS silently ineffective. Fix the
file before applying governance; account-type inference is outside the compatibility
wrapper.

### 4. Pick a Makefile profile

Copy the closest reference implementation to the repo root and wire it to your stack:
```bash
cp profiles/python-uv/Makefile ./Makefile      # or typescript-node / terraform-gcp
```
See [profiles/README.md](../profiles/README.md) for the canonical target contract.

### 5. Review and optionally apply GitHub governance

```bash
uv run python scripts/github_governance.py validate
uv run python scripts/github_governance.py plan --repo OWNER/REPOSITORY
uv run python scripts/github_governance.py audit --repo OWNER/REPOSITORY

# Compatibility entry point for the same plan/apply paths:
DRY_RUN=1 bash scripts/setup-github.sh OWNER/REPOSITORY
bash scripts/setup-github.sh OWNER/REPOSITORY --confirm-repo OWNER/REPOSITORY
```

`validate` is offline. `plan` and `audit` make authenticated, 30-second-bounded GitHub
GET requests and print the same redacted comparison; neither changes GitHub. `plan`
returns 0 after a complete comparison even for drift or unknown state. `audit` returns 0
only when compliant, 1 for drift/unknown, and 2 for input, policy, or read errors. See
[GitHub governance troubleshooting](troubleshooting/github-governance.md).

`apply` is an authenticated local administration command. Before each run, use an
interactive `gh auth login` session with repository Administration write access, run
the GET-only `plan`, review its target and drift, and authorize that exact target and
run. Then repeat the repository value verbatim:

```bash
uv run python scripts/github_governance.py apply \
  --repo OWNER/REPOSITORY \
  --confirm-repo OWNER/REPOSITORY
uv run python scripts/github_governance.py audit --repo OWNER/REPOSITORY
```

Missing or unequal confirmation stops before GitHub discovery. A valid run refreshes
state before writing and verifies one action at a time. It can change repository
security settings, create alerts or pull requests, and change merge eligibility. There
is no automatic retry or rollback: inspect any partial evidence and rerun GET-only
`plan` before separately authorizing recovery. Never run `apply` in CI or on a schedule,
and never store a repository Administration credential in GitHub Actions. Merging the
implementation does not authorize a live run. The authoritative input, output,
exit-code, and failure contract is
[GitHub governance CLI](api/README.md#github-governance-cli).

`scripts/setup-github.sh` is a no-policy compatibility wrapper. A non-empty `DRY_RUN`
delegates to `plan`; normal execution requires the exact target twice and delegates to
`apply`. It makes no direct `gh` call and preserves the reconciler exit code. The former
no-argument form and inline onboarding reminders are removed; use this guide as the
onboarding checklist.

### 6. Install local gates and point your agent at it

```bash
make setup                             # installs deps + pre-commit hooks
```
Open the repo with Claude Code (reads `CLAUDE.md` automatically) or tell any other agent
to read `AGENTS.md`. Assign it an issue and go.

Imitate the shape of the existing modules under `src/modules/` when adding code
(COD-050); the original worked example (`src/modules/catalog/`) was deleted when real
code landed — see git history for the reference shape. Run `make doctor` anytime to
self-check the template (frontmatter integrity + guard-hook tests).

---

## Scenario B — clone the foundation itself onto another machine

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
The repository root is an active Terraform + Python profile. Each new machine needs the
one-time **prerequisites** and **auth** below before all canonical targets can pass.

---

## Per-machine prerequisites (both scenarios)

Install once on each new machine:

| Tool | Needed for | Notes |
|------|-----------|-------|
| `git`, `make` | everything | — |
| `gh` (GitHub CLI) | Governance review and separately authorized local application | `gh auth login` |
| `pre-commit` | local commit gates | `make setup` (once a profile is wired) or `pre-commit install` |
| Stack toolchain | build/test | uv (python), pnpm+node (ts), terraform (iac) — per your profile |
| `gitleaks`, `trivy`, `syft` | local `make security-scan` / `sbom` | optional locally; **CI enforces them regardless** |

The scanners are optional on your laptop — the GitHub Actions workflows run them on every
PR, so a missing local tool only means you don't see findings until CI.

---

## Gotchas (read before you hit them)

### `workflow` OAuth scope is required to push
Pushing any change under `.github/workflows/` needs the token's `workflow` scope. If
`git push` is rejected with *"refusing to allow an OAuth App to create or update
workflow ... without workflow scope"*:
```bash
gh auth refresh -h github.com -s workflow
```
This is a **per-account / per-machine** setting — expect to do it once on each new setup.

### Solo developer + previously applied legacy bootstrap = you can't merge your own PRs
The former fixed bootstrap required one approval and enforced it for admins. The current
`scripts/setup-github.sh` delegates to the layered policy and does not carry that fixed
setting.
The layered policy defaults to zero approvals for solo development while retaining PRs,
status checks, and no-force-push controls. If the legacy bootstrap was already applied:

- **Recommended (keeps the guardrail):** add a second collaborator/reviewer, or enable
  the AI reviewer ([ai-review.yml](../.github/workflows/ai-review.yml)) — note an AI
  review comment does not count as a GitHub *approval*, so for true self-merge you still
  need option below.
- **Solo pragmatic:** relax to zero required reviews while keeping PR + status checks:
  ```bash
  gh api -X PATCH repos/<owner>/<repo>/branches/main/protection/required_pull_request_reviews \
    -F required_approving_review_count=0
  ```
  You still branch + PR + green CI (GR-010, GR-021); you just merge it yourself.

### Line endings
`.gitattributes` enforces LF repo-wide, so shell hooks and Makefiles stay valid on
Windows. Don't override with a global `core.autocrlf=true` that fights it — the
`.gitattributes` wins for matched files, but keep your Git default sane.

### Placeholders that break automation if left unreplaced
`{{ORG}}` in `template-sync.yml` and `CODEOWNERS`, and the issue-config URLs, are the
ones that cause silent failures (ineffective CODEOWNERS, a sync job that can't find its
source). The template-sync job is gated off by default (`TEMPLATE_SYNC_ENABLED`), so it
stays inert until you deliberately enable it.

---

## Quick answer: "is `git clone` enough on a different account?"

- **To develop this foundation** (Scenario B): yes — `git clone` + `make setup` +
  `gh auth refresh -s workflow` on that machine.
- **To start a new project** (Scenario A): no — use "Use this template", then the
  6 setup steps above. Cloning would give the new project this repo's history and
  placeholders instead of a clean start.
