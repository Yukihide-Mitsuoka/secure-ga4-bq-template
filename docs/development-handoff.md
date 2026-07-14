---
id: development-handoff
title: Development Handoff
status: active
updated: 2026-07-14
---

# Development Handoff

This document lets a developer or AI agent resume work on another machine without the
conversation that produced the current repository state. It records only durable project
state; requirements, decisions, and evidence remain authoritative in the linked sources.

## Snapshot

| Item | State on 2026-07-14 | Evidence or source |
|------|---------------------|--------------------|
| Default branch | `main`; live cost-gate proof and subsequent CI security maintenance are merged through PR #55 | [PR #51](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/pull/51), [PR #53](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/pull/53), and [PR #55](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/pull/55) |
| Implementation queue | No open implementation issue; issue #56 tracks this handoff refresh | GitHub issue list checked 2026-07-14 |
| Repository visibility | Public after repository-history sanitization and a full gitleaks scan | [PR #53](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/pull/53) |
| Security workflows | CodeQL, Scorecard, and Sync Labels passed after PR #55 | [CodeQL run](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/actions/runs/29336554245), [Scorecard run](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/actions/runs/29336554092), and [Sync Labels run](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/actions/runs/29336661438) |
| Acceptance B | Complete: 11/11 checks proven deterministically and 8/11 live | [B evidence](verification/2026-07-12-inspection-engine-b-evidence.md) |
| AI narrative report | Implemented and live-verified with synthetic input | [AI evidence](verification/2026-07-12-ai-report-live-evidence.md) |
| Remediation draft | Implemented as deterministic, non-applying Markdown | [ADR-0005](adr/0005-render-remediation-drafts-from-recipes.md) |
| Reusable inspection workflow | Wired by PR #43 and disabled until engagement variables are set | [Runtime configuration](deployment/configuration.md) |
| BigQuery cost gate | WIF boundary, caller, and credential-free Dataform compile path are merged | [ADR-0006](adr/0006-bind-cost-gate-wif-to-trusted-workflow.md) |
| Live cost-gate proof | Complete for the zero-byte infrastructure smoke path; the caller remains opt-in | [Live evidence](verification/2026-07-14-bq-cost-gate-live-evidence.md) |
| Acceptance A | Supporting features exist; execution is blocked until an approved real or production-equivalent GA4 source dataset is available | [Main requirements section 8](requirements/requirements-secure-asset.md) |
| Acceptance S | Not started; requires two engagements or department-standard adoption | [Main requirements section 8](requirements/requirements-secure-asset.md) |
| Cloud residue | All 2026-07-14 managed resources, state, bucket, and temporary variables were removed; BigQuery API remains enabled to avoid force-disabling its active BigQuery Storage dependency | [Cost-gate teardown](verification/2026-07-14-bq-cost-gate-live-evidence.md#teardown-and-residual-state) |

`gcp-cicd-workflows` v2 is the external reusable-workflow dependency. The cost-gate
caller and its WIF condition are pinned together to the fixed `v2.0.2` release.

## Next work

No approved real or production-equivalent GA4 source dataset is currently available.
Do not create cloud resources or begin acceptance-A execution until the decisions in the
next section have named owners and an approved source scope.

After those prerequisites are approved, run the full acceptance-A flow:

1. Supply the engagement's approved GA4 source dataset allow-list and byte budgets.
2. Prove credential-free Dataform compilation and gate the compiled models; the
   zero-byte smoke evidence does not cover this path.
3. Run 100% inspection coverage, deterministic remediation draft, and the opt-in AI
   narrative report against the same approved scope.
4. Add the cost-gate check to branch protection only after the retained environment
   and repository variables have an explicit owner.

The current sequence and intentionally deferred work are maintained in
[the roadmap](roadmap.md).

## Decisions required before cloud changes

| Decision | Why it blocks execution | Recommended default |
|----------|-------------------------|---------------------|
| Terraform state location and owner | Prevents workstation-local state from becoming the only record | GCS backend owned by the target environment |
| Temporary versus retained environment | Determines teardown, evidence, and operating ownership | Temporary for proof unless an engagement owner accepts retention |
| Caller repository numeric ID | ADR-0006 rejects repository-name trust | Read the immutable ID from GitHub metadata |
| Source dataset allow-list | The cost-gate identity has no project-wide data access | Enumerate only datasets referenced by compiled SQL |
| Cost budgets and override owners | Budget exceptions are policy decisions, not compiler defaults | Start with the shared default; require a reason per override |
| Branch-protection timing | A disabled or unproven check must not block all pull requests | Require the check only after the first green manual run |

## Requirements and plan index

| Read order | File | Authority and purpose | Current status |
|------------|------|-----------------------|----------------|
| 1 | [`AGENTS.md`](../AGENTS.md), [`CLAUDE.md`](../CLAUDE.md), [`.ai/README.md`](../.ai/README.md) | Repository operating protocol and rule routing | Binding |
| 2 | [`.ai/guardrails.md`](../.ai/guardrails.md) and [`.ai/security.md`](../.ai/security.md) | Absolute prohibitions and security policy | Binding |
| 3 | [`requirements-secure-asset.md`](requirements/requirements-secure-asset.md) | Product scope, two modes, FR-1..FR-8, and B/A/S acceptance ladder | v1.0 |
| 4 | [`requirements-dbt-dataform-rail.md`](requirements/requirements-dbt-dataform-rail.md) | Build rail, engine-profile choice, governance mapping, and dry-run cost gate | v1.0 |
| 5 | [`requirements-service-packaging.md`](requirements/requirements-service-packaging.md) | Presets, customization axes, packaging, and commercial rationale | v1.0 draft; not the next implementation target |
| 6 | [`design-modules-wif-wiring.md`](requirements/design-modules-wif-wiring.md) | Terraform module interfaces and deployer/inspector WIF baseline | Baseline implemented; cost-gate extension is ADR-0006 |
| 7 | [`design-inspection-engine.md`](requirements/design-inspection-engine.md) | Snapshot model, 11 deterministic checks, CLI/report contract, delivery slices | Implemented v1.0 |
| 8 | [`design-ai-report-generator.md`](requirements/design-ai-report-generator.md) | AI report security boundary, remediation contract, and workflow slices | Implemented and live-verified |
| 9 | [`docs/adr/`](adr/) and [`.ai/decision-log.md`](../.ai/decision-log.md) | Accepted architectural constraints and lightweight decisions | Read newest entries first |
| 10 | [`roadmap.md`](roadmap.md) | Current sequence, next milestones, later work, and rejected scope | Updated 2026-07-14 |
| 11 | [`deployment/configuration.md`](deployment/configuration.md) | Required environment, Terraform, and GitHub variables | Current through Dataform cost compile |
| 12 | [`verification/`](verification/) | Dated evidence; distinguishes implemented claims from live-proven claims | B, AI-report, and zero-byte cost-gate evidence present |

## New-machine resume procedure

Use the repository-specific steps in [Usage](usage.md), then run:

```bash
gh auth status
gcloud auth login
gcloud auth application-default login
make setup
make doctor
make format
make lint
make test
make build
git status --short --branch
```

The two `gcloud` commands create machine-local credentials; never commit their files or
values. Node.js 20-24 and npm are additionally required when activating or validating
the Dataform profile. Optional local scanners may be absent, but CI remains authoritative.

## Resume prompt for the next agent

> Read `AGENTS.md`, `CLAUDE.md`, `.ai/guardrails.md`, `.ai/README.md`, and
> `docs/development-handoff.md`. Confirm `main` is current and the worktree has no
> tracked changes. There is no open implementation issue and no approved GA4 source
> dataset. Continue from "Next work" only after an owner approves a real or
> production-equivalent source scope. Treat the zero-byte cost-gate proof as
> infrastructure evidence only, and stop before cloud changes until ownership, source
> datasets, budgets, state, and teardown are approved.
