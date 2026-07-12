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
