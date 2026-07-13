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
never `DEPLOYER_SA`, and uploads `findings.json`, `summary.md`, and the deterministic
`remediation-draft.md`. Findings only fail a manually dispatched run when the operator
sets `fail_on`; scheduled runs remain report-only.

## Cost-gate infrastructure

ADR-0006 gives the BigQuery dry-run gate a provider and service account separate from
both deployment and inspection. Configure these Terraform inputs before apply:

| Terraform input | Required | Purpose |
|-----------------|----------|---------|
| `github_repository_id` | yes per engagement | Immutable numeric ID of the caller repository; names are not accepted as the security boundary |
| `cost_gate_workflow_ref` | yes when upgrading | Exact released reusable-workflow ref accepted by WIF; defaults to `bq-cost-gate.yml@refs/tags/v2.0.0` |
| `cost_gate_source_datasets` | when SQL references external sources | Project/dataset pairs for raw GA4 and cross-project tables; managed layer datasets are included automatically |

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

Run the compile command on a clean runner without ADC before enabling the gate. It must
produce the configured SQL glob without downloading unpinned tools, reading secrets, or
using cloud credentials. Leaving a required value empty fails closed once the gate is
enabled. Add the resulting cost-gate check to branch protection after its first green run.

Do not substitute `WIF_PROVIDER`, `DEPLOYER_SA`, or `INSPECTOR_SA`. Compilation must be
credential-free. When upgrading gcp-cicd-workflows, update the caller's immutable release
and `cost_gate_workflow_ref` together; a mismatch intentionally fails WIF authentication.
