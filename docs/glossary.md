---
id: glossary
title: Glossary — Ubiquitous Language
updated: 2026-07-02
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
