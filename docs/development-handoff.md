---
id: development-handoff
title: Development Handoff
status: active
updated: 2026-07-18
---

# Development Handoff

This document records the durable repository state needed to resume work without the
conversation that produced it. Requirements, decisions, and dated evidence remain
authoritative in their linked documents.

## Snapshot

| Item | State on 2026-07-18 | Evidence or source |
|------|---------------------|--------------------|
| Default branch | Release baseline v1.7.0; PR #177 advanced the parent lock to vulnerability-intake merge `10e4a1a`, and PR #179 materialized the binding `SEC-003` rule plus dormant exact write shapes | [Release v1.7.0](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/releases/tag/v1.7.0), [PR #177](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/pull/177), [PR #179](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/pull/179) |
| IaC governance prerequisite | Complete: exact `iac-scan` succeeded on PR #125 and its merged-main push | [PR run](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/actions/runs/29517379947), [main run](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/actions/runs/29518413106) |
| Active work | Issue #178 phase 2 connects the accepted `SEC-003` foundation minimums to permission-aware discovery, comparison, and enable-only planning; no live write is executed | [Issue #178](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/178), [ADR-0009](adr/0009-expose-confirmed-local-governance-apply.md) |
| Repository visibility | Public; project/resource IDs are not treated as secrets, but raw inspection artifacts remain Internal | [Security guidance](../.ai/security.md) |
| Acceptance B | Complete: 11/11 checks proven deterministically and 8/11 live | [B evidence](verification/2026-07-12-inspection-engine-b-evidence.md) |
| Technical Acceptance A | APPROVED on 2026-07-15: public-source materialization, WIF cost gate, 100% inspection, remediation draft, one AI report, and teardown completed | [Accepted evidence](verification/2026-07-15-public-ga4-acceptance-a-evidence.md) |
| Acceptance boundary | Approval is constrained to the public sample, interactive ADC inspection, and an inspector WIF path that was not invoked; it is not customer-engagement evidence | [Evidence limitations](verification/2026-07-15-public-ga4-acceptance-a-evidence.md#limitations-and-human-decision) |
| Mart-description governance | Complete: CHK-12 retains table/view and leaf-column descriptions and reports missing metadata without changing the historical Acceptance B denominator | [Issue #70](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/70), [inspection design](requirements/design-inspection-engine.md) |
| Acceptance S | Not started; requires a second engagement or department-standard adoption | [Main requirements section 8](requirements/requirements-secure-asset.md) |
| Cloud baseline | Restored: no namespaced datasets/SAs/active IAM/state bucket/temporary variables; BigQuery enabled; Data Catalog and Vertex AI disabled | [Teardown evidence](verification/2026-07-15-public-ga4-acceptance-a-evidence.md#teardown-and-residual-state) |
| Unrelated shared assets | `github-actions-pool` ACTIVE, `github-actions-deployer` enabled, and `TEMPLATE_SYNC_ENABLED=true` unchanged | Same teardown evidence |

`gcp-cicd-workflows` v2 remains the external reusable-workflow dependency. The cost-gate
caller and WIF condition are pinned together to `v2.0.2`.

## Next work

No cloud action is required for the current milestone. Continue in this order:

1. Merge Issue #178 phase 2 atomically: foundation minimums, permission-aware discovery,
   comparison, enable-only action planning, tests, API guidance, and troubleshooting.
   Do not run governance `apply` as part of implementation or merge verification.
2. The 2026-07-18 GET-only evidence found vulnerability alerts and private vulnerability
   reporting disabled. After phase 2 is merged, review a fresh GET-only `plan` and obtain
   separate target-and-run approval before any live enablement; implementation merge is
   not authorization.
3. Review collaboration-settings merge `414aa03` after the `SEC-003` adaptation is
   merged.
4. Treat every live target and run as separately approval-gated after GET-only
   `plan`; implementation merge is not authorization.
5. Continue advancing only one first-parent commit per reviewed PR; keep lock changes
   separate from protected-file adaptations.
6. Apply the asset to a second engagement when an owner and customer scope exist, then
   measure reuse effort for Acceptance S.
7. Use the versioned standard-inspection profile, generated menu, and deterministic
   qualification artifacts as the service-packaging baseline; change profile values in
   a reviewed PR rather than editing generated material.
8. Keep customer delivery evidence and raw inspection artifacts outside this public
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
| Reporting | Deterministic summary/remediation plus one non-authoritative AI draft |
| CHK-12 | Implemented through the specification, reporting, and inspection slices; no query jobs or additional cloud resources |
| Service packaging | Versioned standard profile, customer-menu renderer, deterministic scope evaluator, and rollback-safe JSON/Markdown qualification publication |
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
> `docs/development-handoff.md`. Confirm the v1.7.0 baseline, PR #177, accepted ADR-0008,
> and accepted ADR-0009. The inheritance lock is `10e4a1a`, and the child-specific
> stricter-Ruleset planner remains authoritative with `iac-scan` preserved. PR #179
> merged Issue #178 phase 1's binding `SEC-003` rule and dormant transport preparation.
> Complete phase 2's atomic policy and planner connection without running `apply`, then
> review collaboration-settings candidate `414aa03`.
> Vulnerability alerts and private reporting were GET-only observed disabled on
> 2026-07-18; do not run governance `apply` or mutate live GitHub/GCP state without
> separate target-specific approval. Retain legacy sync.
> Technical Acceptance A, CHK-12,
> service packaging, and release hardening are complete. Continue toward Acceptance S
> only when a second engagement or department-standard owner and scope exist. Do not
> recreate the deleted verification environment without a new issue and approvals.
