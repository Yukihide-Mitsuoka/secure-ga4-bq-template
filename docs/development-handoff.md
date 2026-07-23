---
id: development-handoff
title: Development Handoff
status: active
updated: 2026-07-23
---

# Development Handoff

This document records the durable repository state needed to resume work without the
conversation that produced it. Requirements, decisions, and dated evidence remain
authoritative in their linked documents.

## Snapshot

| Item | State on 2026-07-23 | Evidence or source |
|------|---------------------|--------------------|
| Default branch | Release baseline v2.0.1; reviewed inheritance and governance maintenance through 2026-07-23 is merged | [Release v2.0.1](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/releases/tag/v2.0.1) |
| Direct parent lock | `terraform-gcp-template` at `de7df1b760534644eb97b9bdd10ab72adb5f665c` | [Inheritance lock](../.github/inheritance/lock.json) |
| IaC governance prerequisite | Complete: exact `iac-scan` succeeded on PR #125 and its merged-main push | [PR run](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/actions/runs/29517379947), [main run](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/actions/runs/29518413106) |
| Active work | Issue #232 is implemented on `feat/232-column-masking-live`; cloud proof and teardown are complete, with review/merge pending | [Issue #232](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/232) |
| Repository visibility | Public; project/resource IDs are not treated as secrets, but raw inspection artifacts remain Internal | [Security guidance](../.ai/security.md) |
| Acceptance B | Complete: 11/11 checks proven deterministically and 8/11 live | [B evidence](verification/2026-07-12-inspection-engine-b-evidence.md) |
| Technical Acceptance A | APPROVED on 2026-07-15: public-source materialization, WIF cost gate, 100% inspection, remediation draft, one AI report, and teardown completed | [Accepted evidence](verification/2026-07-15-public-ga4-acceptance-a-evidence.md) |
| Acceptance boundary | Approval is constrained to the public sample, interactive ADC inspection, and an inspector WIF path that was not invoked; it is not customer-engagement evidence | [Evidence limitations](verification/2026-07-15-public-ga4-acceptance-a-evidence.md#limitations-and-human-decision) |
| Mart-description governance | Complete: CHK-12 retains table/view and leaf-column descriptions and reports missing metadata without changing the historical Acceptance B denominator | [Issue #70](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/70), [inspection design](requirements/design-inspection-engine.md) |
| Column masking | Opt-in technical acceptance PASS: default-off Terraform integration, clear/masked/denied behavior, bounded cost, and teardown proven with synthetic data | [Live evidence](verification/2026-07-23-column-masking-live-evidence.md) |
| Acceptance S | Not started; requires a second engagement or department-standard adoption | [Main requirements section 8](requirements/requirements-secure-asset.md) |
| Cloud baseline | Restored: both verification projects have no BigQuery datasets including anonymous datasets and no active verification SA/IAM; the new project retains only its pre-existing SA and two GCS buckets | [Column-masking teardown](verification/2026-07-23-column-masking-live-evidence.md) |
| Unrelated shared assets | `github-actions-pool` ACTIVE, `github-actions-deployer` enabled, and `TEMPLATE_SYNC_ENABLED=true` unchanged | Same teardown evidence |

`gcp-cicd-workflows` v2 remains the external reusable-workflow dependency. The cost-gate
caller and WIF condition are pinned together to `v2.0.2`.

## Next work

No cloud action is required after Issue #232. Continue in this order:

1. Review and merge the Issue #232 PR only after its required checks pass, then return
   to repository maintenance.
   Protected workflows remain repository-owned and are never overwritten by Template
   Sync.
2. Re-run the GET-only inheritance and governance planners before any future
   propagation or settings change. Treat every live target and run as separately
   approval-gated; implementation merge is not authorization for `apply`.
3. Apply the asset to a second engagement only when an owner, target scope, customer
   data approval, and cloud-cost approval exist, then measure reuse effort for
   Acceptance S.
4. Use the versioned standard-inspection profile, generated menu, and deterministic
   qualification artifacts as the service-packaging baseline; change profile values in
   a reviewed PR rather than editing generated material.
5. Keep customer delivery evidence and raw inspection artifacts outside this public
   repository because complete inspection artifacts remain Internal.

Do not recreate the deleted verification environment unless a new issue and approvals
require it.

The `github-ga4v58` WIF pool ID remains reserved as a harmless DELETED tombstone during
Google's undelete window. Do not reuse that ID during the window.

## Durable results

| Result | Value |
|--------|-------|
| Public source | `bigquery-public-data.ga4_obfuscated_sample_ecommerce` in `US` |
| Actual BigQuery processing | 1,604,088,078 bytes; billed 1,604,321,280 bytes |
| Dedicated WIF cost gate | Three SQL files passed the 2,000,000,000-byte per-file ceiling |
| Inspection coverage | 3 datasets, 3 tables/views, 19 columns, 0 skipped |
| Reporting | Deterministic JSON/CSV/Markdown inspection outputs and remediation plus one non-authoritative AI draft |
| CHK-12 | Implemented through the specification, reporting, and inspection slices; no query jobs or additional cloud resources |
| Service packaging | Versioned standard profile, customer-menu renderer, deterministic scope evaluator, and rollback-safe JSON/Markdown qualification publication |
| Column masking | Default-off opt-in integrated; clear/masked/denied paths passed with 300 processed bytes and 31,457,280 billed bytes |
| Teardown | Current 20-resource proof, its anonymous query datasets, and four historical anonymous verification datasets removed; both projects show zero BigQuery datasets |

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

Use [Usage](foundation/guides/usage.md), then run:

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
> `docs/development-handoff.md`. Confirm the v2.0.1 baseline and direct-parent lock
> `de7df1b760534644eb97b9bdd10ab72adb5f665c`. Keep the child-specific governance
> planner authoritative with `iac-scan` preserved. Do not run governance `apply` or
> mutate live GitHub/GCP state without a fresh GET-only plan and separate
> target-specific approval. Technical Acceptance A, CHK-12, opt-in column masking,
> service packaging, and release hardening are complete. Continue toward Acceptance S
> only when a second engagement or department-standard owner, scope, customer-data
> approval, and cloud-cost approval exist. Do not recreate the deleted verification
> environment without a new issue and approvals.
