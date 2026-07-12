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
