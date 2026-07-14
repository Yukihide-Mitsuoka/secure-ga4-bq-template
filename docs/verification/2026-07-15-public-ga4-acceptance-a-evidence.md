---
id: verification-public-ga4-acceptance-a
title: Live evidence - public GA4 Acceptance A technical candidate
status: executed 2026-07-15
updated: 2026-07-15
---

# Live evidence: public GA4 Acceptance A technical candidate

The technical candidate passed materialization, the dedicated WIF cost gate, complete
deterministic inspection, deterministic remediation rendering, one AI narrative request,
and teardown. The repository owner's human Acceptance A decision remains pending because
the source is a public obfuscated sample, not a customer engagement.

## Execution boundary

| Item | Value |
|------|-------|
| GCP project | `adr-main-application`, shared with unrelated workloads |
| Public source | `bigquery-public-data.ga4_obfuscated_sample_ecommerce` |
| Location | BigQuery `US`; Data Catalog resource paths normalized to `us` |
| Managed scope | `ga4v58_staging`, `ga4v58_intermediate`, `ga4v58_marts` |
| Terraform inventory | 25 namespaced resources; no public-source IAM |
| Per-SQL dry-run ceiling | `2,000,000,000` bytes |
| Total actual-processing ceiling | `4,000,000,000` bytes |
| AI ceiling | One request, no automatic retry |
| Cost-gate run | [GitHub Actions run 29351607935](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/actions/runs/29351607935) |

Before mutation, BigQuery was enabled, Data Catalog and Vertex AI were disabled, the
state bucket did not exist, and the only repository variable was
`TEMPLATE_SYNC_ENABLED=true`. The repository owner approved the named resource scope and
the ceilings above. The existing `github-actions-pool` and `github-actions-deployer`
resources were excluded from every plan and mutation.

## Materialization and actual bytes

Credential-free Dataform compilation exported three SQL files. The staging query and an
explicitly projected equivalent both estimated `1,604,088,078` bytes, confirming that
BigQuery projection pruning already avoided charging for unused source columns. The
assertion was separately reduced to a constant projection by
[PR #66](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/pull/66) because
projecting protected mart columns created an unnecessary authorization dependency.

| Action | BigQuery job | Processed bytes | Billed bytes | Result |
|--------|--------------|----------------:|-------------:|--------|
| Staging view | `dataform-ff547400-d746-45b8-9cdf-f6e864d06671` | 0 | 0 | Created |
| Mart table | `dataform-66df6ef1-e4f0-42a9-a639-f1a890050775` | 1,604,088,078 | 1,604,321,280 | Created with partitioning, clustering, and policy tags |
| Assertion action | `dataform-73b173ea-17ed-4a82-be66-c37435c4ba06` and `dataform-11d441af-b6c0-4544-afd8-175ed0b00fab` | 0 | 0 | Passed |

Total actual processing was `1,604,088,078` bytes, below the approved
`4,000,000,000`-byte ceiling. Dry runs do not add billed query processing.

## Dedicated WIF cost gate

The draft verification PR temporarily activated the checked-in Dataform profile. The
reusable workflow compiled without cloud credentials, staged exactly three regular SQL
files, authenticated through the cost-gate-only provider and service account, and applied
the default ceiling to every file.

| Compiled SQL | Estimated bytes | Budget | Result |
|--------------|----------------:|-------:|--------|
| `fct_events_event_name_not_null.sql` | 0 | 2,000,000,000 | OK |
| `fct_events.sql` | 1,604,088,078 | 2,000,000,000 | OK |
| `stg_ga4__events.sql` | 1,604,088,078 | 2,000,000,000 | OK |

Both `cost-gate / compile` and `cost-gate / gate` completed successfully. The temporary
profile activation and all seven cost-gate repository variables were removed after the
run; the check was not added to branch protection.

## Deterministic inspection

The inspection engine used metadata REST APIs and issued no BigQuery query jobs.
Coverage was complete for the managed scope:

| Coverage | Count |
|----------|------:|
| Datasets | 3 |
| Tables/views | 3 |
| Columns | 19 |
| Skipped resources | 0 |

The run emitted 12 findings: 3 HIGH, 1 MEDIUM, 4 LOW, and 4 INFO. Their deterministic
distribution was CHK-01 HIGH=3, CHK-03 MEDIUM=1, CHK-05 INFO=1, CHK-07 LOW=1, and
CHK-11 INFO=3/LOW=3. No CHK-04 missing-column-tag, CHK-08 large-unpartitioned-table, or
CHK-09 missing-partition-filter finding was emitted. Exact member and resource identifiers
remain Internal data and are not committed to this public repository.

The first live inspection exposed case-sensitive Data Catalog location handling. The fix
normalizes only Data Catalog boundaries and preserves canonical BigQuery `US`; regression
tests, a no-change live Terraform plan, and the successful inspection are recorded in
[PR #68](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/pull/68).

## Reporting artifacts

The complete inspection artifact produced a deterministic summary and non-applying
remediation draft. One Vertex AI request then generated an advisory narrative with
`gemini-2.5-flash` in `global`; no retry occurred. The provider adapter pseudonymizes
project/resource identifiers and omits observed values. The AI prose is non-authoritative
and is not committed.

| Artifact | Bytes | SHA-256 |
|----------|------:|--------|
| `findings.json` | 6,025 | `ff5f8ed9918bf2c55e04c6baa1ece0e745202dc88606c6f401183175bcc76903` |
| `summary.md` | 3,874 | `7fff39ef14134b0826b7c91f2eea48108aac45ebf1141e8a40530ca46af359c8` |
| `remediation-draft.md` | 9,298 | `0cc76a77fc9abe43205e95d6bc7952423bda8adc50e3392f47e4cabb4573e8b4` |
| `ai-report.md` | 6,335 | `246911dedc4320dab3a7d07cc4549b403c0b9aa9b98a9e82f82431437da453e4` |

Structural review found the same 12 finding references in the AI draft: CHK-01=3,
CHK-03=1, CHK-05=1, CHK-07=1, and CHK-11=6. Deterministic `findings.json` and
`summary.md` remain authoritative.

## Teardown and residual state

The three Dataform-created objects were deleted first because the dataset module uses
`delete_contents_on_destroy=false`. A saved destroy plan then completed with
`0 added, 0 changed, 25 destroyed`. Terraform state was empty before every listed object
version and the dedicated bucket were deleted.

| Check after teardown | Observed result |
|----------------------|-----------------|
| Namespaced BigQuery datasets | None |
| Namespaced service accounts and active IAM members | None |
| Custom inspector role | Destroyed by the saved plan |
| State bucket | Direct describe returned 404 |
| Temporary repository variables | None; `TEMPLATE_SYNC_ENABLED=true` remains |
| API baseline | BigQuery enabled; Data Catalog and Vertex AI disabled |
| Existing shared WIF/SA | `github-actions-pool` ACTIVE; `github-actions-deployer` enabled |
| Temporary WIF pool | `github-ga4v58` is a DELETED soft-delete tombstone |

No unrelated shared-project resource was changed. The tombstone reserves the temporary
pool ID during Google's undelete window but grants no active access.

## Limitations and human decision

- The source is production-equivalent public sample data, not evidence from a customer
  engagement and not a GA4 dataset owned by the target project.
- The complete inspection used interactive ADC. Terraform created the dedicated
  inspector service account, custom role, and repository WIF binding, but this candidate
  did not invoke the reusable inspection workflow under that identity.
- A+ PII value scanning, scheduled reconciliation, and remediation application were out
  of scope.
- Provider-boundary pseudonymization was verified through implementation/tests and output
  structure, not independent packet capture.

**Technical candidate result: PASS. Human Acceptance A decision: pending repository-owner
confirmation.**
