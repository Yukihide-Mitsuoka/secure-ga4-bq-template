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

## `actions/checkout` fails with `Repository not found` in Scorecard or Labels Sync

**Affects:** workflow revisions before issue #52.

**Cause:** the job-level permissions block replaced workflow defaults without granting
`contents: read` for the private repository.

**Fix:** update to a revision containing issue #52, then rerun the affected workflow.

**Prevention:** the workflow contract test requires least-privilege checkout and SARIF
permissions together.

**Refs:** #52, SEC-021.

## CodeQL fails immediately with no jobs or logs

**Affects:** workflow revisions before issue #52.

**Cause:** an empty language matrix creates no analysis jobs and produces a failed run.

**Fix:** update to a revision containing issue #52; this repository analyzes Python.

**Prevention:** the workflow contract test requires the repository primary language in
the CodeQL matrix.

**Refs:** #52, SEC-030.
