---
id: troubleshooting-github-governance
title: GitHub governance troubleshooting
---

# GitHub governance troubleshooting

## `audit` exits with status 1

**Affects:** GET-only governance audit.

**Cause:** At least one control is `drift` or `unknown`. Missing required branch-head
checks, including child-required `iac-scan`, are drift; inaccessible admin-only state is
unknown.

**Fix:** Inspect the redacted JSON `controls` entries. Correct the GitHub setting through
an independently reviewed admin procedure, or allow the missing required workflow to run
on the target branch, then rerun `audit`. This command has no `apply` mode.

**Prevention:** Run `plan` before changing governance and use `audit` as CI's compliance
gate. Unrelated observed checks are ignored.

**Refs:** #140, GR-012, SEC-002.

## Apply-action planning stops closed

The internal planner emits request-shaped data but never executes it and is not a CLI
command. It rejects unknown state, missing branch-head checks, unsafe targets, legacy
protection, and existing managed-Ruleset updates; resolve those conditions through a
separately reviewed admin procedure before planning again.

**Refs:** #146, GR-010, GR-011, GR-012, SEC-002.
