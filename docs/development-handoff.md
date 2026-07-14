---
id: development-handoff
title: Development Handoff
status: active
updated: 2026-07-15
---

# Development Handoff

This document records the durable repository state needed to resume work without the
conversation that produced it. Requirements, decisions, and dated evidence remain
authoritative in their linked documents.

## Snapshot

| Item | State on 2026-07-15 | Evidence or source |
|------|---------------------|--------------------|
| Default branch | `main` at `3210cb2`, including the public-GA4 isolation and live-found location/assertion fixes through PR #68 | [PR #68](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/pull/68) |
| Active work | Draft PR #69 records Issue #62; its temporary Dataform activation has been removed | [PR #69](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/pull/69) |
| Repository visibility | Public; project/resource IDs are not treated as secrets, but raw inspection artifacts remain Internal | [Security guidance](../.ai/security.md) |
| Acceptance B | Complete: 11/11 checks proven deterministically and 8/11 live | [B evidence](verification/2026-07-12-inspection-engine-b-evidence.md) |
| Acceptance A technical candidate | PASS: public-source materialization, WIF cost gate, 100% inspection, remediation draft, one AI report, and teardown completed | [A candidate evidence](verification/2026-07-15-public-ga4-acceptance-a-evidence.md) |
| Human Acceptance A decision | Pending repository-owner confirmation; the source is public sample data, not a customer engagement | [Evidence limitations](verification/2026-07-15-public-ga4-acceptance-a-evidence.md#limitations-and-human-decision) |
| Acceptance S | Not started; requires a second engagement or department-standard adoption | [Main requirements section 8](requirements/requirements-secure-asset.md) |
| Cloud baseline | Restored: no namespaced datasets/SAs/active IAM/state bucket/temporary variables; BigQuery enabled; Data Catalog and Vertex AI disabled | [Teardown evidence](verification/2026-07-15-public-ga4-acceptance-a-evidence.md#teardown-and-residual-state) |
| Unrelated shared assets | `github-actions-pool` ACTIVE, `github-actions-deployer` enabled, and `TEMPLATE_SYNC_ENABLED=true` unchanged | Same teardown evidence |

`gcp-cicd-workflows` v2 remains the external reusable-workflow dependency. The cost-gate
caller and WIF condition are pinned together to `v2.0.2`.

## Next work

No cloud action is required for Issue #62. Continue in this order:

1. Review draft PR #69 and the dated evidence.
2. Record whether the public-sample technical proof satisfies human Acceptance A.
3. Mark PR #69 ready, merge it after checks pass, and close Issue #62.
4. Continue with the service-packaging baseline or a second engagement; do not recreate
   the deleted verification environment unless a new issue and approvals require it.

The `github-ga4v58` WIF pool ID remains reserved as a harmless DELETED tombstone during
Google's undelete window. Do not reuse that ID during the window.

## Durable results

| Result | Value |
|--------|-------|
| Public source | `bigquery-public-data.ga4_obfuscated_sample_ecommerce` in `US` |
| Actual BigQuery processing | 1,604,088,078 bytes; billed 1,604,321,280 bytes |
| Dedicated WIF cost gate | Three SQL files passed the 2,000,000,000-byte per-file ceiling |
| Inspection coverage | 3 datasets, 3 tables/views, 19 columns, 0 skipped |
| Reporting | Deterministic summary/remediation plus one non-authoritative AI draft |
| Teardown | 25 Terraform resources plus three Dataform objects, all state versions, bucket, variables, and two temporary APIs removed |

Artifact hashes and exact run links live only in the dated evidence to avoid duplicate
sources of truth.

## Requirements and plan index

| Read order | File | Purpose |
|------------|------|---------|
| 1 | [`AGENTS.md`](../AGENTS.md), [`CLAUDE.md`](../CLAUDE.md), [`.ai/README.md`](../.ai/README.md) | Binding operating protocol and task routing |
| 2 | [`.ai/guardrails.md`](../.ai/guardrails.md), [`.ai/security.md`](../.ai/security.md) | Absolute prohibitions and security policy |
| 3 | [`requirements-secure-asset.md`](requirements/requirements-secure-asset.md) | Product scope and B/A/S acceptance ladder |
| 4 | [`requirements-dbt-dataform-rail.md`](requirements/requirements-dbt-dataform-rail.md) | Build rail and cost-gate contract |
| 5 | [`requirements-service-packaging.md`](requirements/requirements-service-packaging.md) | Next productization baseline |
| 6 | [`design-modules-wif-wiring.md`](requirements/design-modules-wif-wiring.md) | Terraform and WIF wiring |
| 7 | [`design-inspection-engine.md`](requirements/design-inspection-engine.md) | Deterministic inspection contract |
| 8 | [`design-ai-report-generator.md`](requirements/design-ai-report-generator.md) | AI provider boundary and reporting contract |
| 9 | [`docs/adr/`](adr/), [`.ai/decision-log.md`](../.ai/decision-log.md) | Accepted decisions |
| 10 | [`roadmap.md`](roadmap.md) | Current direction |
| 11 | [`deployment/configuration.md`](deployment/configuration.md) | Runtime variables and activation procedure |
| 12 | [`verification/`](verification/) | Dated live evidence |

## New-machine resume procedure

Use [Usage](usage.md), then run:

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

Credentials remain machine-local and must never be committed. Optional local scanners
may be absent; CI remains authoritative.

## Resume prompt

> Read `AGENTS.md`, `CLAUDE.md`, `.ai/guardrails.md`, `.ai/README.md`, and
> `docs/development-handoff.md`. Confirm `main` is current and tracked changes belong to
> draft PR #69. The public-GA4 Acceptance A technical candidate passed and its temporary
> GCP/GitHub resources were torn down. Review the dated evidence, obtain the repository
> owner's human Acceptance A decision, complete PR #69, then move to service packaging or
> a second engagement. Do not recreate the deleted environment without new approvals.
