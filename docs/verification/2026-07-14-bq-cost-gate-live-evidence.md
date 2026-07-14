---
id: verification-bq-cost-gate-live
title: Live evidence — BigQuery cost gate authenticates and enforces a zero-byte budget
status: executed 2026-07-14
---

# Live evidence: BigQuery cost gate

This run proves that the pull-request caller can pass isolated SQL through the released
reusable workflow, authenticate through its dedicated WIF boundary, and enforce a
BigQuery dry-run byte budget. It used no GA4 dataset and did not execute a query.

## Result

| Item | Observed value |
|------|----------------|
| Caller | PR #51, commit `13fdf664ae72d380ae8796afe726d20dc37597a6` |
| Reusable workflow | `gcp-cicd-workflows` `v2.0.2` |
| GitHub Actions run | [29328902861](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/actions/runs/29328902861) |
| Compile job | `87071802594`: staged and uploaded one isolated SQL artifact |
| Gate job | `87071843190`: downloaded the artifact, authenticated, and completed the dry run |
| SQL | `tests/fixtures/bq-cost-gate/smoke.sql` (`SELECT 1 AS cost_gate_smoke;`) |
| Estimate and budget | `0` bytes estimated, `0` bytes allowed, `OK` |
| Execution project | `example-verification-project` |
| Source datasets | None; no GA4 dataset was available or created |

The authenticated identity was the dedicated `bq-cost-gate` service account. Its
temporary grants were project-level BigQuery Job User plus Data Viewer on only the
three temporary layer datasets. Compilation ran in the preceding job without OIDC or
Google Cloud credentials. The inspector identity did not receive query-job permission.

## Defects found by the live proof

| Released version | Live observation | Resolution |
|------------------|------------------|------------|
| `v2.0.0` | The dot-prefixed staging directory was excluded by `upload-artifact` | [gcp-cicd-workflows PR #5](https://github.com/Yukihide-Mitsuoka/gcp-cicd-workflows/pull/5), released as `v2.0.1` |
| `v2.0.1` | WIF and the dry run succeeded, but an external-account warning caused the job JSON parser to fail | [gcp-cicd-workflows PR #7](https://github.com/Yukihide-Mitsuoka/gcp-cicd-workflows/pull/7), released as `v2.0.2` |

The successful run used the fixes from both releases. The caller and Terraform WIF
condition are pinned to the same immutable `v2.0.2` reference.

## Scope limitation

This is an infrastructure-only proof. The constant query proves artifact isolation,
WIF authentication, least-privilege job creation, dry-run parsing, and budget
enforcement. It does not prove credential-free Dataform compilation against an
engagement project or estimate bytes for GA4 models. That requires an approved source
dataset and remains part of acceptance A.

## Teardown and residual state

The approved Terraform destroy plan removed all 22 managed resources. Verification
then found an empty Terraform state, no `staging`, `intermediate`, or `marts` datasets,
and none of the three temporary service accounts. The GCS state bucket
`example-verification-state-bucket`, including all object versions, and
all six temporary GitHub repository variables were deleted. Data Catalog API was
returned to disabled.

BigQuery API remains enabled. Its normal disable operation was rejected because the
active BigQuery Storage API depends on it. Audit logs confirmed that this proof
explicitly requested only BigQuery and Data Catalog, but did not establish the origin
of the BigQuery Storage enablement. The human declined a force-disable because it would
also disable that dependent service in a shared project. The deleted WIF pool remains
as a provider-managed soft-delete tombstone; it has no active credentials or grants.
