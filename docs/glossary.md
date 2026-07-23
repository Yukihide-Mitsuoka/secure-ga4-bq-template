---
id: glossary
title: Glossary — Ubiquitous Language
updated: 2026-07-23
---

# Glossary

The ubiquitous language (DDD). Code identifiers, docs, and conversation MUST use these
terms with exactly these meanings (COD-002). Before naming a new concept, check here;
when introducing a term, add it here in the same PR (DOC-030).

Format: term, one-sentence definition, context it belongs to, and what it is NOT when
confusable. Keep alphabetical.

## Template & foundation terms

| Term | Definition | Context | Not to be confused with |
|------|------------|---------|--------------------------|
| ADR | Immutable record of an architectural decision in `docs/adr/` | foundation | decision log (the index of all decisions) |
| Agent | Any AI system working in this repo under CLAUDE.md rules | foundation | — |
| Bounded context | A domain boundary owning its model and language; maps 1:1 to `src/modules/<context>` | DDD | module (the code artifact implementing it) |
| Canonical command | A `make` target that is the only entry point for a dev action | foundation | — |
| Contract change | A change to a MODULE.md public API or event (ARC-020) | foundation | breaking change (a contract change affecting *external* consumers) |
| Guardrail | An absolute prohibition (GR-xxx) that no instruction can override | foundation | rule (overridable with justification if SHOULD-level) |
| Module | A directory under `src/modules/` implementing one bounded context | foundation | package/library |
| Skill | A task playbook in `.skills/*.skill.md` | foundation | Claude Code native skill (optional wrapper) |

## Project terms

<!-- TEMPLATE: add your domain's terms here as the first bounded context is modeled. -->

| Term | Definition | Context | Not to be confused with |
|------|------------|---------|--------------------------|
| AI-generated report | Advisory Markdown narrative rendered from a deterministic finding frame and requiring human review | reporting | deterministic `summary.md` |
| Audit | GET-only governance comparison used as a compliance gate; exits nonzero for drift or unknown state | governance | plan or apply |
| Deterministic finding frame | Authoritative inspection JSON whose finding IDs, severities, coverage, and remediation hints bound AI prose | inspection/reporting | model-generated findings |
| Drift | A governance control whose known current value differs from the resolved desired value | governance | unknown state |
| Engagement scope | Anonymous preflight counts and work flags evaluated against one menu profile | service packaging | inspection parameters or collected customer metadata |
| Menu profile | Versioned product-definition data containing a service package's fee range, capacity limits, checks, deliverables, and separate-estimate conditions | service packaging | deployment or customer configuration |
| Plan | GET-only governance comparison that reports compliant, drift, or unknown state without acting as a compliance gate | governance | audit or apply |
| Promotion source | Structured declaration of the nested field path and key from which a mart leaf column is promoted; it records intended origin but does not prove transformation correctness | inspection | BigQuery description or verified SQL lineage |
| Qualification reason | A profile-defined condition requiring work outside the standard service package | service packaging | a security finding or final sales decision |
| Remediation recipe | Versioned local mapping from an FR-4 check ID to non-applying Terraform, policy, or manual review guidance | reporting | model-generated code |
| Service package | A reviewed commercial boundary rendered and qualified from one menu profile | service packaging | the technical inspection engine |
| Unknown | A governance state that cannot be determined from safely available GitHub reads and therefore never counts as compliant | governance | drift |
