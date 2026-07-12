# ADR-0004: Isolate AI report generation behind a reporting boundary

| Field | Value |
|-------|-------|
| Status | accepted (2026-07-12, repository owner) |
| Date | 2026-07-12 |
| Deciders | repository owner |
| Author | Codex (AI agent) |
| Supersedes / Superseded by | - |

## Context

FR-5 and acceptance level A require natural-language inspection reports and remediation
drafts generated from the deterministic `findings.json` artifact. The completed B-level
inspection engine deliberately excludes AI generation and owns the authoritative finding
set. Adding an LLM introduces non-deterministic output, an external data boundary,
credentials, cost, vendor-specific APIs, and prompt-injection risk.

The design must preserve these constraints:

1. Only the inspection engine decides findings, severity, coverage, and remediation hints.
2. AI output is an advisory draft and is never applied automatically.
3. Secrets, sampled row values, and credentials are never sent to or logged by the model.
4. Inspection remains usable when AI generation is disabled or fails.
5. Provider-specific code and dependencies remain replaceable.

## Options considered

### Option 1: Do nothing and keep the deterministic Markdown summary

- Pros: no new credentials, dependencies, cost, or data-processing boundary.
- Cons: does not meet FR-5 or acceptance level A; operators must write the customer-facing
  narrative and remediation plan manually.

### Option 2: Add AI generation directly to the inspection module

- Pros: one command and direct access to the typed `Report` object.
- Cons: mixes deterministic assessment with non-deterministic prose; expands the
  inspection contract and dependency surface; makes provider failure part of a previously
  reliable path; weakens the B/A boundary recorded by ADR-0003.

### Option 3: Add a reporting bounded context that consumes `findings.json` - chosen

A new `src/modules/reporting/` bounded context validates the versioned artifact,
constructs a bounded prompt, calls a provider through an application port, validates the
response, and writes a separate Markdown draft. The inspection module is unchanged.

- Pros: preserves ADR-0003 invariants; isolates provider adapters; failures cannot corrupt
  deterministic artifacts; the same use case can run locally or in a future workflow.
- Cons: adds a module and an artifact contract; duplicates some parsing instead of
  importing inspection internals; still needs one provider SDK, credential, and cost.

### Option 4: Generate reports only in GitHub Actions

- Pros: credentials stay in CI secrets; no runtime SDK in this repository.
- Cons: violates the local/CLI requirement; couples the report to workflow infrastructure;
  gives a third-party action a broader trust position than a narrow adapter.

## Decision

Adopt Option 3. AI report generation MUST live in a new `reporting` bounded context and
consume serialized `findings.json`, not inspection internals. Its application layer MUST
own a provider-neutral generation port. The interface MUST be an opt-in local CLI that
writes a separate `ai-report.md` without changing deterministic inspection artifacts.

The initial adapter uses Gemini on Vertex AI through Google's official `google-genai`
Python SDK, stable API `v1`, and ADC/WIF authentication. It is isolated in
`infrastructure/` and preferred over handwritten HTTP for maintained authentication,
timeouts, response schemas, and error handling. Before provider submission, project and
resource identifiers MUST be replaced with deterministic aliases and observed values MUST
be omitted. The provider returns structured JSON keyed by finding aliases; trusted local
code validates it and renders Markdown with original identifiers. Existing
`ai-report.md` files MUST NOT be overwritten.

## Consequences

**Positive:**

- The deterministic inspection engine and B-level evidence remain unchanged.
- AI can be disabled, replaced, or removed without changing checkpoint logic.
- The external boundary can enforce schema, size, redaction, timeout, and output checks.
- A future workflow can preserve deterministic artifacts when AI generation fails.

**Negative:**

- A second Python context and a versioned artifact schema must be maintained.
- Resource names and observed configuration may be Internal data; provider use requires
  engagement approval and acceptable retention/training terms.
- LLM output is not byte-deterministic and requires human review.
- The first provider adds a dependency, secret, cost model, and some vendor lock-in.

**Follow-ups:**

- Implement the slices in `design-ai-report-generator.md`.
- Add `bq-inspect.yml` only after the local CLI contract is stable.

