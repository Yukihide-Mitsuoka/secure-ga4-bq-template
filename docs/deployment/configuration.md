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
