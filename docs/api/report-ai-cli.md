---
id: report-ai-cli
title: AI inspection report CLI contract
---

# AI inspection report CLI

## Command

```bash
make report-ai FINDINGS=reports/project/timestamp/findings.json
```

The command is opt-in and uses Vertex AI through ADC/WIF. It reads one complete
`findings.json` (maximum 1 MiB) and writes `ai-report.md` beside it, or beneath
`OUT=<directory>`.

## Contract

- Accepted schema: inspection artifact v1; the current unversioned B artifact is treated as
  v1 for backward compatibility.
- Required coverage: `coverage.skipped` is empty.
- Provider input: deterministic aliases and finding metadata only. Project/resource IDs,
  observed values, rows, credentials, and skipped details are excluded.
- Output: an advisory draft. `summary.md` and `findings.json` remain authoritative.
- Idempotency: existing `ai-report.md` is never overwritten.

| Exit | Meaning | Caller action |
|------|---------|---------------|
| 0 | report written | review the draft against `summary.md` |
| 1 | provider or generated-output failure | retain deterministic artifacts; retry after diagnosis |
| 2 | invalid config, input, coverage, path, or existing output | correct the local input/config |

Authentication requires `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, ADC, and
Vertex AI invocation permission. The model defaults to `gemini-2.5-flash` and can be
changed through `GA4_BQ_REPORT_MODEL`.

## Deterministic remediation command

```bash
make remediation-draft FINDINGS=reports/project/timestamp/findings.json
```

This command uses no AI provider and needs no cloud credentials. It validates the same
complete inspection artifact and writes `remediation-draft.md` beside it, or beneath
`OUT=<directory>`. CHK-01 through CHK-11 map to versioned local recipes.

The output is byte-deterministic, non-applying Markdown. It contains required inputs,
`REPLACE_ME_*` placeholders, Terraform or policy examples where safe, and validation
steps. Artifact free text never selects or populates code. Existing output is never
overwritten.

| Exit | Meaning | Caller action |
|------|---------|---------------|
| 0 | remediation draft written | complete placeholders and review against the authoritative findings |
| 2 | invalid input, coverage, path, or existing output | correct the local input or output location |

The command never runs Terraform, applies policy, creates a pull request, or calls Vertex
AI. Converting the Markdown into repository code remains behind the engagement's normal
review, plan, and approval gates.
