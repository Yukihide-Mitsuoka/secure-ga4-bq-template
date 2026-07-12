---
id: known-issues
title: Known issues
---

# Known issues

## ga4-bq-report: GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION are required

**Cause:** Vertex AI routing configuration is incomplete.

**Fix:** Set both variables shown in `.env.example`, then rerun `make report-ai`.

## ga4-bq-report: invalid input or output: inspection coverage is incomplete

**Cause:** One or more resources were skipped during deterministic inspection.

**Fix:** Resolve the skipped-resource cause and rerun `make inspect`. AI reporting does
not describe a partial inspection as complete.

## ga4-bq-report: generation failed: Vertex AI report generation failed

**Cause:** ADC/WIF, model permission, location, quota, timeout, or provider availability.

**Fix:** Verify ADC and the configured project/location/model. Deterministic
`findings.json` and `summary.md` remain valid; no cleanup is required.

## ga4-bq-report: invalid input or output: report already exists

**Cause:** The output directory already contains `ai-report.md`.
**Fix:** Select a new `OUT` directory. Existing AI drafts are never overwritten.
