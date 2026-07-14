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
| Default branch | `main` at merge `7e88642`; public-GA4 isolation support is merged through PR #59 | [PR #59](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/pull/59) |
| Implementation queue | No open implementation issue; issue #60 tracks this handoff refresh | GitHub issue list checked 2026-07-14 |
| Repository visibility | Public after repository-history sanitization and a full gitleaks scan | [PR #53](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/pull/53) |
| Post-merge checks | CI, Security, CodeQL, IaC Scan, and Scorecard passed on `7e88642` | [CI](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/actions/runs/29342790990), [Security](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/actions/runs/29342791095), [CodeQL](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/actions/runs/29342791308), [IaC Scan](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/actions/runs/29342793037), and [Scorecard](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/actions/runs/29342795108) |
| Acceptance B | Complete: 11/11 checks proven deterministically and 8/11 live | [B evidence](verification/2026-07-12-inspection-engine-b-evidence.md) |
| AI narrative report | Implemented and live-verified with synthetic input | [AI evidence](verification/2026-07-12-ai-report-live-evidence.md) |
| Remediation draft | Implemented as deterministic, non-applying Markdown | [ADR-0005](adr/0005-render-remediation-drafts-from-recipes.md) |
| Reusable inspection workflow | Wired by PR #43 and disabled until engagement variables are set | [Runtime configuration](deployment/configuration.md) |
| BigQuery cost gate | WIF boundary, caller, and credential-free Dataform compile path are merged | [ADR-0006](adr/0006-bind-cost-gate-wif-to-trusted-workflow.md) |
| Live cost-gate proof | Complete for the zero-byte infrastructure smoke path; the caller remains opt-in | [Live evidence](verification/2026-07-14-bq-cost-gate-live-evidence.md) |
| Public GA4 source | Approved for development: `bigquery-public-data.ga4_obfuscated_sample_ecommerce` in `US`; Terraform must not manage its IAM | [Dataform profile](../profiles/dataform-bigquery/README.md#public-ga4-verification-in-a-shared-project) |
| Public-source dry run | Dataform exported three SQL files; staging validated at `1,604,088,078` bytes with no execution or persistent resource | [Public GA4 evidence](verification/2026-07-14-public-ga4-dry-run-evidence.md) |
| Acceptance A | Public-source technical proof is ready for a temporary managed-layer run; materialization, 100% inspection, same-scope remediation/AI report, and human acceptance remain | [Main requirements section 8](requirements/requirements-secure-asset.md) |
| Acceptance S | Not started; requires two engagements or department-standard adoption | [Main requirements section 8](requirements/requirements-secure-asset.md) |
| Cloud baseline | No resource was created for PR #59. BigQuery remains enabled; Data Catalog and Vertex AI APIs are disabled; candidate state bucket `adr-main-application-secure-ga4-tfstate-20260714-58` does not exist | Read-only GCP checks on 2026-07-14; [prior teardown](verification/2026-07-14-bq-cost-gate-live-evidence.md#teardown-and-residual-state) |

`gcp-cicd-workflows` v2 is the external reusable-workflow dependency. The cost-gate
caller and its WIF condition are pinned together to the fixed `v2.0.2` release.

## Next work

Pause before cloud mutation. The public source and source-facing dry run are complete,
but the temporary apply and teardown plan below has not received explicit approval.

After approval, run the acceptance-A technical candidate in this order:

1. Record the enabled-API baseline; temporarily enable Data Catalog and Vertex AI only.
2. Create the new state bucket and apply the namespaced Terraform environment in `US`.
3. Replace the example policy-tag paths with Terraform outputs and materialize the
   staging view and mart from the public source.
4. Enforce the proposed byte limits, run the dedicated WIF cost gate, and stop on any
   estimate above the approved ceiling.
5. Run 100% inspection, deterministic remediation draft, and one opt-in AI narrative
   report against the same managed scope.
6. Capture dated evidence, then destroy all managed resources, delete the state and
   bucket, remove temporary GitHub variables, and restore the API baseline.

Do not add the temporary cost-gate check to branch protection; its variables will be
removed during teardown.

## Proposed temporary cloud scope — not approved yet

| Category | Proposed value | Teardown requirement |
|----------|----------------|----------------------|
| GCP project | `adr-main-application` (shared with unrelated workloads) | Never delete or modify unrelated resources |
| State bucket | `adr-main-application-secure-ga4-tfstate-20260714-58` | Delete all object versions and the bucket |
| Managed datasets | `ga4v58_staging`, `ga4v58_intermediate`, `ga4v58_marts` in `US` | Terraform destroy |
| Taxonomy | `ga4-verify-58` plus high/medium/low policy tags in `US` | Terraform destroy |
| WIF | Pool `github-ga4v58`; providers `github-oidc` and `ga4v58-cost-gate` | Terraform destroy; expect a provider soft-delete tombstone |
| Service accounts | `github-deployer`, `ga4v58-inspector`, `ga4v58-cost` | Terraform destroy |
| Custom role | `bqInspector` bound only to the temporary inspector | Terraform destroy |
| Temporary APIs | `datacatalog.googleapis.com`, `aiplatform.googleapis.com` | Disable only if this run enabled them; do not force-disable BigQuery |
| GitHub variables | WIF, service-account, compile, SQL-glob, project, budget, and enable flags | Delete after evidence capture |

The existing `github-actions-pool`, `github-actions-deployer` service account, and all
other shared-project resources are unrelated and MUST NOT be changed.

## Proposed budgets — not approved yet

| Limit | Proposed value | Stop condition |
|-------|----------------|----------------|
| Per compiled SQL file | `2,000,000,000` bytes | Any dry-run estimate above the limit |
| Total actual BigQuery processing | `4,000,000,000` bytes | Do not materialize additional actions after the limit |
| AI generation | One report request; no automatic retry | Any retry requires human approval |

The per-file proposal is based on the observed staging estimate of `1,604,088,078`
bytes. It is a safety ceiling, not an approved spend.

The current sequence and intentionally deferred work are maintained in
[the roadmap](roadmap.md).

## Decisions required before cloud changes

| Decision | Why it blocks execution | Recommended default |
|----------|-------------------------|---------------------|
| Create-and-teardown approval | Shared-project mutations and later destructive commands require explicit approval | Approve the named scope above; require a new check before each destructive command |
| Budget approval | The observed estimate does not authorize materialization | Approve or reduce the proposed 2 GB/file and 4 GB total limits |
| Human acceptance owner | A public sample proves technical production equivalence, not a customer engagement | Repository owner decides whether completed evidence satisfies Acceptance A |
| Terraform state owner | Temporary state must not become an unowned retained system | Repository owner approves; agent operates and deletes it in the same run |
| Source boundary | Public source IAM cannot and must not be managed by this project | Keep the exact Dataform source reference; leave `cost_gate_source_datasets` empty |
| API restoration | Data Catalog and Vertex AI are currently disabled | Record before/after lists and restore only APIs changed by this run |

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
| 12 | [`verification/`](verification/) | Dated evidence; distinguishes implemented claims from live-proven claims | B, AI-report, zero-byte cost-gate, and public-GA4 dry-run evidence present |

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
> tracked changes. PR #59 is merged and the public GA4 staging SQL has a successful
> `1,604,088,078`-byte dry run. No temporary persistent GCP resource exists. Continue
> from "Next work", but do not mutate the shared project until the named resource scope,
> byte limits, and teardown operations receive explicit human approval. Never modify the
> existing `github-actions-pool` or `github-actions-deployer` resources.
