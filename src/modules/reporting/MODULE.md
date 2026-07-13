# Reporting module

## Purpose

Turn a deterministic inspection `findings.json` artifact into advisory,
customer-readable output. The module never performs inspection, changes findings, reads
BigQuery rows, or applies remediation.

Architecture decisions: [ADR-0004](../../../docs/adr/0004-isolate-ai-report-generation.md)
and [ADR-0005](../../../docs/adr/0005-render-remediation-drafts-from-recipes.md).

## Public API

| Entry point | Layer | Description |
|-------------|-------|-------------|
| `InspectionArtifact`, `GeneratedNarrative` | domain | Validated input and provider-output vocabulary |
| `GenerateAiReport.handle(input_path, out_dir)` | application | Read, pseudonymize, generate, validate, and write |
| `GenerateRemediationDraft.handle(input_path, out_dir)` | application | Read, select versioned recipes, and write a deterministic draft |
| `make report-ai FINDINGS=<json>` | interface | Opt-in Vertex AI CLI; writes `ai-report.md` |
| `make remediation-draft FINDINGS=<json>` | interface | Offline deterministic CLI; writes `remediation-draft.md` |

## Owned data

No persistent state. It reads one inspection artifact and owns only the generated
`ai-report.md` and `remediation-draft.md` files written beneath a caller-selected
directory.

## Invariants

1. The model receives aliases, check enums, coverage counts, and approved static guidance
   only; never artifact free text, project/resource identifiers, observed values, rows,
   credentials, or skipped error details.
2. Provider output cannot add, remove, reclassify, or resolve findings. Every expected
   finding reference appears exactly once.
3. `findings.json` and `summary.md` are never changed.
4. Existing output files fail closed and are never overwritten.
5. Provider or writer failure leaves no partial report and never makes deterministic
   inspection artifacts unusable.
6. Remediation code and policy examples come only from versioned local recipes; the model
   and artifact free text never select or populate code.
7. Remediation output is deterministic, non-applying Markdown with explicit placeholders.

## Dependencies

| Uses | Via | Why |
|------|-----|-----|
| Inspection module | serialized `findings.json` contract only | Preserve bounded-context isolation |
| Vertex AI | `TextGenerator` application port | Replaceable provider adapter |

## Layout

```
domain/model.py
domain/remediation.py
application/ports.py
application/generate_ai_report.py
application/generate_remediation_draft.py
infrastructure/json_artifact_reader.py
infrastructure/vertex_ai_generator.py
infrastructure/markdown_report_writer.py
infrastructure/markdown_remediation_writer.py
interface/cli.py
interface/remediation_cli.py
```
