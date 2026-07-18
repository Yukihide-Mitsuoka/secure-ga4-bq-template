---
id: adr-0009
title: Expose confirmed local governance apply
status: proposed
date: 2026-07-17
---

# ADR-0009: Expose confirmed local governance apply

| Field                      | Value            |
| -------------------------- | ---------------- |
| Status                     | proposed         |
| Date                       | 2026-07-17       |
| Deciders                   | repository owner |
| Author                     | Codex (AI agent) |
| Supersedes / Superseded by | —                |

## Context

The repository can validate, discover, compare, and audit its inherited GitHub
governance policy through the public `validate`, `plan`, and `audit` commands. It also
contains a tested internal executor that refreshes state before writing, applies one
planned action at a time, reads the affected controls back, verifies them, and replans.
No non-test caller can invoke that executor, so maintainers must reproduce the write
boundary manually to enforce a reviewed policy.

The public CLI shape is Architectural under ARC-020. The decision must support a solo
maintainer without weakening the child repository's stricter planner, including its
additive `iac-scan` requirement. A live application can change merge eligibility,
direct-push behavior, repository security features, and security notifications. It can
also stop after a partial application. The command therefore requires an authenticated,
least-privilege, explicitly confirmed local boundary. This ADR does not authorize any
live GitHub write.

## Options considered

### Option 1: Keep the executor internal-only

This preserves the current public CLI. It has the smallest immediate blast radius and
no new operational command, but leaves policy enforcement manual and makes the tested
executor unavailable to maintainers. Manual API calls would create an unverified write
path and increase configuration drift risk.

### Option 2: Expose a confirmed local `apply` command

Add `apply --repo OWNER/REPOSITORY --confirm-repo OWNER/REPOSITORY` and delegate to the
existing executor only after the two repository values match exactly. This adds one
public entry point while retaining the current planner and verified execution sequence.
It is reversible by removing the entry point, but a failed run can leave a verified,
reported partial application that requires operator review.

### Option 3: Add a separate wrapper or two-step plan token

A wrapper could require a saved plan or generated token before calling the executor.
This adds friction between review and execution, but creates another public contract,
state artifact, and validation lifecycle. Repository state can change after token
creation, so the executor must still refresh and replan; the extra mechanism does not
replace the existing safety boundary.

## Decision

Adopt Option 2. The public CLI MUST require exact `--repo` and `--confirm-repo`
equality before GitHub discovery or writes and MUST reuse the existing child executor
and stricter planner. It MUST authenticate through a local interactive `gh` session
with repository Administration write access, MUST NOT run in CI, and MUST NOT use a
GitHub Actions administration credential. The executor MUST refresh discovery and plan
before its first write, apply one action at a time, read back affected controls, verify
them, and replan. It MUST stop without retry or automatic rollback when any phase fails
and return redacted partial evidence.

Each live target and run requires separate explicit authorization. An AI agent or other
automation MUST present a GET-only plan and obtain human approval before invocation; a
human invoking the command directly provides that authorization. Merging this ADR or
the implementation does not authorize a live run. Scheduled and automatic application
remain out of scope.

## Consequences

**Positive:** Maintainers gain a single reviewed path from inherited policy to immediate
repository enforcement. Exact target confirmation, fresh planning, action-by-action
verification, and redacted evidence limit mistakes without requiring a second reviewer.
The child planner remains authoritative and cannot silently drop `iac-scan` or stronger
observed controls.

**Negative:** The command needs repository Administration write access and can change
repository-wide behavior. Failure can leave a partial but reported state. Operators must
review the evidence and GET-only plan before deciding whether to run again or manually
reverse a change. GitHub API behavior and permissions remain an external dependency.

**Follow-ups:** After human acceptance, implement the CLI and tests in a separate issue
and PR; update user-facing usage and troubleshooting documentation; run no live `apply`
without separate target-specific approval.
