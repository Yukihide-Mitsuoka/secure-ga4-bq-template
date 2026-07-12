# Reporting module

## Purpose

Turn a deterministic inspection `findings.json` artifact into an advisory,
customer-readable AI report. The module never performs inspection, changes findings, reads
BigQuery rows, or applies remediation.

Architecture decision: [ADR-0004](../../../docs/adr/0004-isolate-ai-report-generation.md).

## Public API

| Entry point | Layer | Description |
|-------------|-------|-------------|
| `InspectionArtifact`, `GeneratedNarrative` | domain | Validated input and provider-output vocabulary |
| `GenerateAiReport.handle(input_path, out_dir)` | application | Read, pseudonymize, generate, validate, and write |
| `make report-ai FINDINGS=<json>` | interface | Opt-in Vertex AI CLI; writes `ai-report.md` |

## Owned data

No persistent state. It reads one inspection artifact and owns only the generated
`ai-report.md` written beneath a caller-selected directory.

## Invariants

1. The model receives aliases, check enums, coverage counts, and approved static guidance
   only; never artifact free text, project/resource identifiers, observed values, rows,
   credentials, or skipped error details.
2. Provider output cannot add, remove, reclassify, or resolve findings. Every expected
   finding reference appears exactly once.
3. `findings.json` and `summary.md` are never changed.
4. Existing `ai-report.md` fails closed and is never overwritten.
5. Provider failure leaves no partial report and never makes deterministic inspection
   artifacts unusable.

## Dependencies

| Uses | Via | Why |
|------|-----|-----|
| Inspection module | serialized `findings.json` contract only | Preserve bounded-context isolation |
| Vertex AI | `TextGenerator` application port | Replaceable provider adapter |

## Layout

```
domain/model.py
application/ports.py
application/generate_ai_report.py
infrastructure/json_artifact_reader.py
infrastructure/vertex_ai_generator.py
infrastructure/markdown_report_writer.py
interface/cli.py
```
