---
id: design-ai-report-generator
title: Implementation design - A-level AI inspection report generator
status: implemented-live-v1
updated: 2026-07-12
---

# Implementation design: A-level AI inspection report generator

- Status: slices 1-5 implemented and verified; evidence:
  [live Vertex AI evidence](../verification/2026-07-12-ai-report-live-evidence.md).
- Public entry point: `make report-ai FINDINGS=<findings.json> [OUT=<directory>]`.
- Requirements: `requirements-secure-asset.md` FR-5, section 4.2, section 7.1, and
  acceptance level A in section 8.
- Architecture gate: [ADR-0004](../adr/0004-isolate-ai-report-generation.md).
- Input: the B-level inspection engine's deterministic `findings.json`.
- First slice: a customer-readable Markdown narrative. Terraform and policy drafts are
  deferred and remain non-applying artifacts.

## 1. Acceptance criteria

1. A local CLI accepts one `findings.json` and writes one `ai-report.md`.
2. Input is validated before a provider call. Unknown schema versions, malformed
   findings, unsupported check IDs or severities, excessive size, and incomplete coverage
   fail with exit code 2 and a non-sensitive error.
3. The provider receives only the validated report frame. The implementation never reads
   environment files, credentials, table rows, raw GA4 values, or unrelated files into
   the prompt.
4. The provider returns structured JSON keyed by pseudonymous finding references.
   Generated content cannot add, remove, reclassify, or resolve findings. A deterministic
   validator rejects output outside the frame and local code renders the Markdown.
5. Output is labeled as an AI-generated draft requiring human review and contains scope,
   coverage, an executive summary, finding explanations, and next actions. Slice 1
   contains no executable remediation.
6. Authentication, timeout, rate-limit, malformed-response, and refusal failures are
   explicit. Failure never alters deterministic artifacts or leaves a partial report.
7. Credentials come from the provider's standard credential chain (for example, ADC/WIF
   or an environment variable), and are never CLI values, persisted, or logged. Prompt
   and response bodies are not logged by default.
8. Unit tests use a fake provider and no network. Security tests cover hostile metadata,
   prompt injection text, output paths, and secret non-disclosure.

## 2. Scope

Included in slice 1:

- Versioned input validation for the existing `findings.json` shape.
- Bounded, pseudonymized prompt construction from validated fields.
- A provider-neutral application port and Vertex AI adapter using `google-genai`.
- Markdown validation, atomic output writing, local CLI, tests, and module docs.

Deferred:

- Terraform/IAM/policy remediation drafts and machine-readable remediation actions.
- Reusable workflow integration and artifact upload.

Out of scope:

- Changing inspection findings, severity, or coverage.
- Applying remediation or creating pull requests.
- PII value scanning and scheduled Cloud Run execution (A+).
- Sending BigQuery rows or raw GA4 event values to an LLM.

## 3. Proposed module boundary

```
src/modules/reporting/
  MODULE.md
  domain/
    inspection_artifact.py
    generated_report.py
  application/
    ports.py
    generate_ai_report.py
  infrastructure/
    json_artifact_reader.py
    <provider>_generator.py
    markdown_report_writer.py
  interface/
    cli.py
```

The module consumes the serialized public artifact, not
`src.modules.inspection` internals. This keeps the contract usable across processes and
repositories and prevents coupling to private inspection objects.

## 4. Data and security boundary

Treat the complete artifact as **Internal** under SEC-011.

- AI generation is opt-in.
- Reject oversized files before parsing.
- Treat every string as data, never instructions, and delimit records structurally.
- Replace project/resource identifiers with deterministic aliases before submission.
- Omit observed values, `catalog_path`, and skipped error details from provider input.
- Reattach exact local identifiers only while rendering the final Markdown.
- Write atomically to a fixed filename beneath the selected output directory.
- Fail if output exists unless an explicit overwrite policy is approved.
- Log only event names, counts, provider/model identifiers, and timing.
- Verify TLS; bound timeouts and retries to transient failures.

## 5. Provider port

```
ReportGenerator.generate(request) -> GeneratedText
```

The request contains the validated frame and prompt-template version. The result contains
structured JSON, provider/model names, and a request ID when available. Aggregate token
counts may be retained; prompt and response bodies are not retained outside the final
report.

The first adapter uses Gemini on Vertex AI through the official `google-genai` SDK,
stable API `v1`, and ADC/WIF. It sets a bounded timeout, requests a JSON response schema,
does not supply tools, and closes the SDK client after generation.

## 6. Output and exit contract

`ai-report.md` contains a draft notice, deterministic scope/coverage, executive summary,
findings without changed IDs or severity, next actions from existing hints, and generation
metadata. Every input finding ID must appear exactly once; unknown IDs are rejected.
`summary.md` remains the audit source of truth.

| Exit | Meaning |
|------|---------|
| 0 | report generated and atomically written |
| 1 | provider or generated-output failure; deterministic artifacts remain valid |
| 2 | invalid CLI/config, unsafe path, or invalid/unsupported input |

## 7. Delivery slices

| Slice | Content | Gate |
|-------|---------|------|
| 1 | ADR-0004 + this design + indexes | owner approves ADR and provider |
| 2 | skeleton, input domain/schema validation, fake provider, tests | unit suite green |
| 3 | use case, prompt framing, output validator/writer, CLI | security tests green |
| 4 | approved provider adapter and dependency | lint/test/security scan green |
| 5 | live opt-in generation from synthetic findings | verified 2026-07-12 |
| 6 | Terraform/policy draft design and implementation | separate review |
| 7 | reusable workflow integration | local CLI stable |

## 8. Owner rulings

1. Separate `reporting` bounded context: approved.
2. Initial provider: Gemini on Vertex AI via `google-genai` and ADC/WIF.
3. Provider-bound project/resource identifiers: deterministic pseudonyms.
4. Existing `ai-report.md`: fail closed; no overwrite option in slice 1.

