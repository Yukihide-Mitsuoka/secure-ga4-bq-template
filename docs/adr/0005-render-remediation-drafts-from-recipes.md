# ADR-0005: Render remediation drafts from deterministic recipes

| Field | Value |
|-------|-------|
| Status | accepted (2026-07-13, repository owner) |
| Date | 2026-07-13 |
| Deciders | repository owner |
| Author | Codex (AI agent) |
| Supersedes / Superseded by | extends ADR-0004 / - |

## Context

FR-5 and acceptance level A require a remediation draft containing Terraform or policy
guidance. ADR-0004 established a reporting boundary in which Gemini writes constrained
prose from a pseudonymized finding frame, while local code validates the response and
reattaches identifiers. Delivery slices 1-5 implement and verify that narrative report,
but intentionally contain no executable remediation.

Terraform and policy text has a different risk profile from prose:

1. A reviewer may mistake generated code for an approved change and apply it.
2. The current `findings.json` does not contain Terraform state addresses, repository
   ownership, import status, or every provider argument needed for an exact patch.
3. Artifact free text such as `observed` and `remediation_hint` is untrusted input and
   must not become instructions or source code.
4. IAM removal, audit-log changes, and retention changes can reduce access or delete data
   if rendered with incorrect assumptions.
5. The existing `make report-ai` contract is live and must remain backward compatible.

The remediation slice must therefore produce useful review material without expanding
the model into an arbitrary code generator or creating an apply path.

## Options considered

### Option 1: Do nothing

Keep the AI narrative and deterministic remediation hints as the only outputs.

- Pros: no new code path or executable-looking artifact.
- Cons: leaves FR-5's Terraform/policy draft and delivery slice 6 incomplete.

### Option 2: Ask the model to return free-form HCL or policy text

Extend the provider schema with a code field and write that field into the report or a
`.tf` file.

- Pros: flexible output and low initial implementation effort.
- Cons: model output could contain destructive or unrelated operations; syntax and
  provider behavior would be non-deterministic; prompt-injection text could influence
  code; identifiers would need a broader provider boundary; review would not establish
  that the code matches repository state. This option conflicts with GR-030 and the
  deterministic-frame principle in ADR-0004.

### Option 3: Render Markdown drafts from versioned local recipes - chosen

Map each validated `check_id` to a versioned local remediation recipe. Trusted local code
renders a separate `remediation-draft.md` containing review warnings, finding references,
required inputs, Terraform or policy examples, and validation steps. Missing engagement
details remain explicit `REPLACE_ME_*` placeholders or manual actions.

- Pros: byte-deterministic output; no model-generated code; recipes are unit-testable;
  identifiers stay local; the draft remains useful when Vertex AI is unavailable; the
  Markdown extension prevents accidental Terraform discovery or apply.
- Cons: recipes require maintenance as Google providers and organizational policy evolve;
  placeholders require human completion; a generic recipe cannot be a repository-ready
  patch without engagement-specific Terraform state and ownership data.

### Option 4: Add a separate remediation bounded context

Create another module that consumes `findings.json` and owns remediation planning.

- Pros: strongest conceptual separation and room for a future patch engine.
- Cons: speculative for one consumer and one output; duplicates validation and aliasing;
  increases the public surface without a proven independent lifecycle. The existing
  reporting context already owns advisory outputs and can isolate a second use case.

## Decision

Adopt Option 3 inside the existing `reporting` bounded context.

1. Add a separate `make remediation-draft FINDINGS=<json> [OUT=<directory>]` entry point.
   `make report-ai` and `ai-report.md` MUST remain unchanged.
2. The remediation command MUST NOT call an AI provider. The AI-generated narrative and
   deterministic remediation attachment form the FR-5 report package, but only trusted
   local code may emit Terraform or policy examples.
3. A versioned registry MUST map every supported FR-4 `check_id` to exactly one recipe.
   Version 1 MUST cover CHK-01 through CHK-11; recipes may resolve to Terraform, policy,
   or an explicit manual procedure where safe code cannot be inferred.
4. Recipe selection MUST depend only on validated enums and typed metadata. Artifact free
   text MUST NOT be interpreted as code, template syntax, identifiers, or instructions.
5. Code examples MUST use explicit `REPLACE_ME_*` placeholders for values absent from the
   deterministic contract. Raw artifact text MUST NOT appear inside code fences.
6. The output MUST be one atomic, byte-deterministic `remediation-draft.md`, labeled
   non-applying and human-review-required. Existing output MUST fail closed without an
   overwrite option.
7. The output MUST NOT contain apply automation, pull-request creation, destructive
   commands, or a `.tf`/policy file that tooling could discover automatically.
8. Every recipe MUST state required inputs and validation steps. Applying or converting a
   draft into repository code remains outside this module and requires the customer's
   normal review, plan, and approval gates.

## Consequences

**Positive:**

- FR-5 gains Terraform/policy review material without trusting probabilistic code.
- ADR-0004's provider data boundary and existing CLI remain unchanged.
- Remediation generation works offline and can be tested byte-for-byte.
- A future engagement-specific patch workflow can consume reviewed recipes without
  making that workflow part of the current slice.

**Negative:**

- The first output is a draft with placeholders, not an immediately applicable patch.
- Eleven recipe families increase maintenance and documentation work.
- Provider or API changes can make examples stale even when the renderer is correct.
- Users may still copy unsafe drafts, so warnings and validation steps are necessary but
  cannot replace human review.

**Migration and rollback:**

- This is additive: remove the new command, recipes, and output writer to return to the
  ADR-0004 behavior. No existing artifact migration is required.
- Recipe versions are immutable after release. A changed remediation approach adds a new
  recipe version so existing evidence remains reproducible.

**Follow-ups:**

- Specify the v1 recipe schema and per-check required inputs in the slice-6 design.
- Implement the registry, renderer, CLI, tests, module contract, and user documentation
  in GR-020-sized PRs after owner approval.
- Keep reusable workflow integration in delivery slice 7; it MUST NOT apply remediation.
