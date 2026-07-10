#!/usr/bin/env bash
# GitHub repository governance bootstrap — Policy as Code for the settings GitHub
# doesn't read from files. Idempotent; safe to re-run. Requires: gh CLI authenticated
# with admin on the repo (`gh auth status`).
#
# Usage:
#   bash scripts/setup-github.sh              # apply to the repo of the current dir
#   DRY_RUN=1 bash scripts/setup-github.sh    # print what would be done
#
# Configures: branch protection on main (PR + status checks + review), squash-only
# merges, secret scanning + push protection, private vulnerability reporting,
# Dependabot alerts, Discussions. Prints the remaining manual steps at the end.

set -euo pipefail

DRY_RUN="${DRY_RUN:-}"
# Status checks required to merge — must match job names in .github/workflows/ci.yml
# and security.yml. Adjust when adding/renaming jobs.
REQUIRED_CHECKS='["lint", "test", "build", "doctor", "link-check", "secret-scan"]'

repo="$(gh repo view --json nameWithOwner --jq .nameWithOwner)"
owner_type="$(gh repo view --json owner --jq .owner.__typename 2>/dev/null || echo Unknown)"
echo "==> Configuring governance for: $repo (owner type: $owner_type)"

api() {
  if [ -n "$DRY_RUN" ]; then
    echo "[dry-run] gh api $*"
  else
    gh api "$@" >/dev/null
  fi
}

step() { echo "--> $1"; }
warn() { echo "    WARN: $1 (continuing — may need a paid plan / public repo / admin rights)"; }

step "Repository merge & hygiene settings (squash-only, PR-title commits, auto-delete branches)"
api -X PATCH "repos/$repo" \
  -F allow_squash_merge=true \
  -F allow_merge_commit=false \
  -F allow_rebase_merge=false \
  -f squash_merge_commit_title=PR_TITLE \
  -f squash_merge_commit_message=PR_BODY \
  -F delete_branch_on_merge=true \
  -F has_discussions=true \
  || warn "repo settings PATCH failed"

step "Secret scanning + push protection (SEC-002)"
api -X PATCH "repos/$repo" \
  --input - <<'JSON' || warn "secret scanning unavailable (private repo without GHAS?)"
{"security_and_analysis": {"secret_scanning": {"status": "enabled"}, "secret_scanning_push_protection": {"status": "enabled"}}}
JSON

step "Private vulnerability reporting (SECURITY.md flow)"
api -X PUT "repos/$repo/private-vulnerability-reporting" \
  || warn "private vulnerability reporting unavailable"

step "Dependabot alerts + automated security fixes (SEC-030)"
api -X PUT "repos/$repo/vulnerability-alerts" || warn "vulnerability alerts failed"
api -X PUT "repos/$repo/automated-security-fixes" || warn "automated security fixes failed"

step "Branch protection on main (GR-010..012: PR required, checks required, no force push)"
if [ -n "$DRY_RUN" ]; then
  echo "[dry-run] gh api -X PUT repos/$repo/branches/main/protection (checks: $REQUIRED_CHECKS)"
else
  gh api -X PUT "repos/$repo/branches/main/protection" --input - >/dev/null <<JSON || warn "branch protection failed (branch 'main' must exist and have at least one push)"
{
  "required_status_checks": {"strict": true, "contexts": $REQUIRED_CHECKS},
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "require_last_push_approval": true
  },
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": true
}
JSON
fi

step "CODEOWNERS sanity check (personal accounts can't use @org/team syntax)"
if [ "$owner_type" = "User" ] && [ -f .github/CODEOWNERS ] && grep -qE '@[^/[:space:]]+/[^[:space:]]+' .github/CODEOWNERS; then
  owner_login="${repo%%/*}"
  echo "    WARN: this is a personal (User) repo but .github/CODEOWNERS uses @org/team refs,"
  echo "          which are silently ineffective on personal accounts. Replace them, e.g.:"
  echo "          sed -i -E 's#@[^/[:space:]]+/[^[:space:]]+#@${owner_login}#g' .github/CODEOWNERS"
  echo "          then commit on a branch and open a PR."
fi

echo ""
echo "==> Done. Remaining MANUAL steps (cannot be automated via API):"
echo "  1. Install the Renovate GitHub App and grant it this repo (renovate.json is ready)."
echo "  2. Create Discussion categories per .github/discussion-categories.md."
echo "  3. Set CodeQL languages in .github/workflows/codeql.yml (matrix is empty by default)."
echo "  4. Optional — AI PR review: set repo variable ENABLE_AI_REVIEW=true and secret"
echo "     ANTHROPIC_API_KEY (see .github/workflows/ai-review.yml)."
echo "  5. Optional — DAST: set repo variable DAST_TARGET_URL to your staging URL."
echo "  6. If this repo IS the template: Settings -> General -> check 'Template repository'."
echo "  7. Downstream repos wanting template updates: set variable TEMPLATE_SYNC_ENABLED=true"
echo "     and replace {{ORG}} in .github/workflows/template-sync.yml so foundation updates"
echo "     arrive as PRs. (Left unset, the sync workflow stays safely inert.)"
