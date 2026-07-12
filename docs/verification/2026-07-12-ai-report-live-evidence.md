---
id: verification-ai-report-live
title: Live evidence - AI inspection report generation through Vertex AI
status: executed 2026-07-12
updated: 2026-07-12
---

# Live evidence: AI inspection report generation through Vertex AI

This run proves delivery slice 5 of
[`design-ai-report-generator.md`](../requirements/design-ai-report-generator.md): the
local CLI accepted a complete synthetic inspection artifact, invoked Gemini through
Vertex AI, validated the structured response, and atomically wrote `ai-report.md`.

## Execution boundary

| Item | Value |
|------|-------|
| Project | `example-verification-project` (development project) |
| Location | `global` |
| Model | `gemini-2.5-flash` |
| Authentication | Interactive ADC; no credential value was logged or persisted in the repository |
| Input | One fully synthetic CHK-03 finding from the reporting unit-test builder |
| Command | `make report-ai FINDINGS=<synthetic-findings.json> OUT=<temporary-directory>` |
| Repository revision | `main` after #38 (`dcbeee0`) |

The input contained no real customer data. The provider boundary pseudonymized the
synthetic project and resource identifiers and omitted the synthetic observed value,
catalog path, and remediation text from the prompt as required by ADR-0004.

## Result

The command exited `0` and wrote one 861-byte, 34-line `ai-report.md`. Local structural
checks confirmed all required frame elements:

| Check | Result |
|-------|--------|
| Draft notice | Present |
| Coverage section | Present |
| Executive summary | Present |
| `CHK-03` finding | Present exactly once |
| Explanation and deterministic remediation hint | Present |
| Next action | Present |
| Generation metadata | Present |

Artifact hashes record the exact local inputs and outputs without committing generated
content:

| Artifact | SHA-256 |
|----------|---------|
| Synthetic `findings.json` | `849e783b1c3d84dd46296b0fbdee763a9edd6d67629f685a4ae18796900b1ceb` |
| Generated `ai-report.md` | `3c277bffe3bdc5049a1dbf5e03bc0d5d3a1a8458de150021877a6bdb19b24047` |

The generated report remained in `/tmp` for local review and was not committed because
AI prose is non-deterministic and is not an audit source of truth. The deterministic
`findings.json` and `summary.md` contracts remain authoritative.

## Failure-path observations

Two fail-closed paths were observed before the successful call:

1. Missing `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION` exited `2` before any
   provider call.
2. A disabled Vertex AI API exited `1` with the non-sensitive provider error and left no
   partial report.

The Vertex AI API was enabled only for the successful run and then disabled. The enabled
API query returned an empty result before and after the run, restoring the tested cloud
configuration to its prior state.

## Scope conclusion

Delivery slices 1-5 are now verified. This evidence proves the narrative-report slice;
Terraform/policy remediation drafts and reusable workflow integration remain separate
future slices and are not implied by this result.
