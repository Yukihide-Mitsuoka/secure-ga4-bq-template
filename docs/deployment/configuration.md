---
id: deployment-configuration
title: Runtime configuration
---

# Runtime configuration

| Variable | Required | Source | Purpose |
|----------|----------|--------|---------|
| `GOOGLE_CLOUD_PROJECT` | AI report only | local environment or CI variable | Vertex AI quota project |
| `GOOGLE_CLOUD_LOCATION` | AI report only | local environment or CI variable | Vertex AI request location |
| `GA4_BQ_REPORT_MODEL` | no | local environment or CI variable | model ID; defaults to `gemini-2.5-flash` |

Authentication uses Application Default Credentials locally and WIF in CI. No API key is
accepted by the CLI. The calling identity needs only the Vertex AI model invocation
permission in addition to permissions needed by the separate inspection step.

Inspection artifacts are Internal data (SEC-011). Engagement approval is required before
provider use. The implementation pseudonymizes identifiers and omits observed values before
submission, but the deterministic local artifacts retain exact identifiers.

## GitHub Actions inspection

The caller [`.github/workflows/bq-inspect.yml`](../../.github/workflows/bq-inspect.yml)
uses `gcp-cicd-workflows@v1` and the following repository variables:

| Variable | Required | Purpose |
|----------|----------|---------|
| `WIF_PROVIDER` | yes | Workload Identity provider resource name from Terraform output |
| `INSPECTOR_SA` | yes | Dedicated read-only inspector service account email |
| `BQ_INSPECT_ENABLED` | schedule only | Set to `true` after a successful manual run to enable the weekly schedule |

Copy `inspection-params.example.yml` to the engagement-owned
`inspection-params.yml`, replace `project_id` and `expected_location`, and review every
scope and threshold before the first manual run. The workflow uses the inspector identity,
never `DEPLOYER_SA`, and uploads `findings.json`, the flat `findings.csv` projection,
`summary.md`, and the deterministic `remediation-draft.md`. Findings only fail a manually
dispatched run when the operator sets `fail_on`; scheduled runs remain report-only.

## Cost-gate infrastructure

ADR-0006 gives the BigQuery dry-run gate a provider and service account separate from
both deployment and inspection. Configure these Terraform inputs before apply:

| Terraform input | Required | Purpose |
|-----------------|----------|---------|
| `layer_dataset_ids` | shared target project | Explicit staging/intermediate/marts dataset IDs; use three unique values to prevent collisions with unrelated datasets |
| `github_repository_id` | yes per engagement | Immutable numeric ID of the caller repository; names are not accepted as the security boundary |
| `github_workload_identity_pool_id` | when `github` is unavailable | GitHub Actions WIF pool ID; override when the project already has or recently deleted the default pool |
| `deployer_service_account_id` | shared target project | Deployer account ID; override when the default account exists or was recently deleted |
| `cost_gate_workflow_ref` | yes when upgrading | Exact released reusable-workflow ref accepted by WIF; defaults to `bq-cost-gate.yml@refs/tags/v2.0.2` |
| `cost_gate_source_datasets` | when SQL references private external sources | Project/dataset pairs on which Terraform may manage reader IAM; managed layers are automatic, and public datasets must be omitted |

For the Google-managed public GA4 sample, use the isolated `US` configuration and
teardown rules in the [Dataform profile](../../profiles/dataform-bigquery/README.md#public-ga4-verification-in-a-shared-project).

After apply, set the following repository variables for the cost-gate caller:

| Variable | Source | Purpose |
|----------|--------|---------|
| `COST_GATE_WIF_PROVIDER` | Terraform output `cost_gate_workload_identity_provider` | Provider restricted to the caller repository ID and trusted reusable workflow |
| `COST_GATE_SA` | Terraform output `cost_gate_sa_email` | Dedicated dry-run identity with project Job User and dataset-scoped Data Viewer |

The caller is [`.github/workflows/bq-cost-gate.yml`](../../.github/workflows/bq-cost-gate.yml).
Keep it disabled until every required value below is configured:

| Repository variable | Required | Purpose |
|---------------------|----------|---------|
| `GCP_PROJECT_ID` | yes | Project billed for BigQuery dry-run jobs |
| `BQ_COST_GATE_SQL_GLOB` | yes | Relative glob of regular compiled SQL files produced inside the checkout |
| `BQ_COST_GATE_COMPILE_COMMAND` | when SQL is generated | Credential-free command backed by a checked-in target and lockfile-pinned tooling |
| `BQ_COST_GATE_DEFAULT_MAX_BYTES` | no | Per-file byte ceiling; unset uses 100 GB |
| `BQ_COST_GATE_BUDGETS_FILE` | no | Relative YAML file containing reviewed path-specific overrides and reasons |
| `BQ_COST_GATE_ENABLED` | last | Set to `true` only after the other values and dataset grants are ready |

For the Dataform profile, use `make compile-cost-gate` and
`transform/target/compiled/**/*.sql` for the compile command and SQL glob. The target
installs only the lockfile, compiles without ADC, and exports executable queries from
the Dataform graph. dbt `compile` is not the credential-free default because its
BigQuery adapter initializes ADC even when introspection and cache population are off.

Run the compile command on a clean runner without ADC before enabling the gate. It must
produce the configured SQL glob without downloading unpinned tools, reading secrets, or
using cloud credentials. Leaving a required value empty fails closed once the gate is
enabled. Add the resulting cost-gate check to branch protection after its first green run.

When no source dataset exists, an infrastructure-only live proof MAY use
`tests/fixtures/bq-cost-gate/smoke.sql` with an empty compile command, a matching SQL
glob, and a zero-byte budget. This proves the WIF and artifact boundaries but does not
replace the Dataform compile proof or the acceptance-A run against an approved scope.

Do not substitute `WIF_PROVIDER`, `DEPLOYER_SA`, or `INSPECTOR_SA`. Compilation must be
credential-free. When upgrading gcp-cicd-workflows, update the caller's immutable release
and `cost_gate_workflow_ref` together; a mismatch intentionally fails WIF authentication.

## Optional column masking

Column masking is disabled when Terraform `data_policies` is empty. When an engagement
approves masking, configure each authorization boundary independently:

| Reader behavior | Dataset access | Policy access |
|-----------------|----------------|---------------|
| Cleartext | `roles/bigquery.dataViewer` | `roles/datacatalog.categoryFineGrainedReader` on the matching policy tag |
| Masked | `roles/bigquery.dataViewer` | `roles/bigquerydatapolicy.maskedReader` on the matching data policy |
| Denied control | `roles/bigquery.dataViewer` | Neither policy role |

All three query identities need an engagement-owned permission containing
`bigquery.jobs.create`; the template does not broaden project IAM when masking is enabled.
Attach the selected policy tag to a materialized table column before testing. Views cannot
carry policy tags.

For a live proof, use synthetic values, estimate every query before execution, set a
maximum-bytes-billed ceiling, and test cleartext, masked, and denied behavior separately.
Save an explicit destroy plan, delete all temporary objects immediately after the proof,
and verify the namespace is absent. Do not disable a project API unless the recorded
before-state proves the proof enabled it and no unrelated dependency uses it.

BigQuery stores successful query results in per-principal anonymous datasets, which are
visible only with `bq ls -a`. Inspect and remove those datasets before deleting temporary
query identities; after an identity is deleted, another principal cannot recursively
delete its result tables. Cached result tables normally expire after approximately 24
hours, but the empty anonymous dataset can remain visible and must still be included in
the residual check. See the [live proof](../verification/2026-07-23-column-masking-live-evidence.md)
for the verified teardown sequence.
