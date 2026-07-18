---
id: troubleshooting-github-governance
title: GitHub governance troubleshooting
---

# GitHub governance troubleshooting

## `validate` rejects governance profiles

**Affects:** Offline governance validation and every command that resolves policy.

**Cause:** Files under `.github/governance/profiles/` branch, cycle, contain duplicate or
invalid IDs/checks, do not connect to `ai-dev-foundation`, exceed 32 profiles, or use a
symlink. The resolver rejects the entire policy instead of guessing layer order.

**Fix:** Keep only regular `*.json` files and make each profile's `parent` name the
preceding profile ID; exactly one profile names `ai-dev-foundation`. Give every profile a
unique lowercase kebab-case ID and a non-empty unique `required_checks` list. Rerun
`validate` before any GET-only plan.

**Prevention:** Add one template-family profile at a time and keep repository-only checks
in `.github/governance/repository.json`. Required checks merge monotonically; do not copy
the foundation list into a profile merely to preserve it.

**Refs:** #104, ADR-0008, GR-012.

## `audit` exits with status 1

**Affects:** GET-only governance audit.

**Cause:** At least one control is `drift` or `unknown`. Missing required branch-head
checks, including child-required `iac-scan`, are drift; inaccessible admin-only state is
unknown. Vulnerability alerts are confirmed disabled only when GitHub returns 404 and
the repository response confirms Administration access; otherwise ambiguous access is
`unknown`. Private vulnerability reporting uses GitHub's explicit enabled Boolean.

**Fix:** Inspect the redacted JSON `controls` entries. Allow missing required workflows
to run on the target branch. If policy-backed settings still drift, review `plan` and
use the separately authorized local `apply`, then rerun `audit`.

**Prevention:** Run `plan` before changing governance and use `audit` as CI's compliance
gate. Unrelated observed checks are ignored.

**Refs:** #140, #178, GR-012, SEC-002, SEC-003.

## `apply` exits with status 2

**Affects:** Confirmed local governance application.

**Cause:** Input or confirmation is invalid; policy or GitHub reads are incomplete; the
planner cannot preserve observed stronger controls; or a write, read-back, verification,
or replanning phase failed. The command stops without retry or automatic rollback.

**Fix:** Inspect `failure_phase`, `failed_action`, `attempted_actions`, and
`verified_actions` in the redacted JSON evidence. Run GET-only `plan` and `audit` to
observe current state. Do not blindly rerun: obtain separate authorization before a
recovery run or manual reversal. Missing checks, unknown state, unsafe targets, legacy
protection, additional required checks, and unpreservable managed-Ruleset state must be
resolved without weakening the child policy or its `iac-scan` requirement.

For `security.vulnerability_alerts` or
`security.private_vulnerability_reporting`, an `unknown` state produces no write action.
Restore repository read/Administration access and rerun `plan`; do not interpret an
inaccessible endpoint as proof that the control is disabled.

**Prevention:** Use local interactive `gh` authentication with repository Administration
write access, confirm the exact repository value, and never run `apply` from CI or a
schedule.

**Refs:** #171, #178, ADR-0009, GR-010, GR-011, GR-012, SEC-002, SEC-003.
