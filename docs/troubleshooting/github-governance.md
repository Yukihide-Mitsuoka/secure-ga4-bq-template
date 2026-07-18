---
id: troubleshooting-github-governance
title: GitHub governance troubleshooting
---

# GitHub governance troubleshooting

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
