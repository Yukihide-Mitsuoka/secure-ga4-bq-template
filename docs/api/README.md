---
id: api-docs
title: API Documentation
---

# API Documentation

Contracts for every interface this system exposes (HTTP, events, CLI).

**Update triggers (DOC-030):** any change to a public endpoint, event schema, CLI
command, or error contract. Breaking contract changes additionally require the
`BREAKING CHANGE:` commit footer (WF-020) and consumer migration notes.

## Rules

- **Schema first**: the machine-readable contract (OpenAPI 3.x at `openapi.yaml`,
  AsyncAPI for events, JSON Schema for payloads) is the source of truth; prose
  commentary supplements, never contradicts.
- Contract tests verify implementation against the schema (TST-001 integration level);
  drift between schema and implementation is a CI failure, not a doc chore.
- Every endpoint documents: auth requirement (SEC-020), inputs with validation rules,
  outputs, **every error response** with its trigger condition, idempotency, rate limits.
- Examples use obviously fake credentials (GR-002) and realistic payloads.
- Versioning: breaking API changes follow expand→migrate→contract (REL-040); document
  deprecation windows here.

## Structure

| File | Content |
|------|---------|
| `openapi.yaml` | HTTP API contract (source of truth) |
| `events.md` / `asyncapi.yaml` | Published/consumed events |
| [`report-ai-cli.md`](report-ai-cli.md) | `make report-ai` inputs, outputs, auth, and exit codes |
| `errors.md` | Error catalog: code → meaning → caller action |
| `changelog.md` | Contract-level changes and deprecation schedule |

## Engagement qualification CLI

```bash
make qualify-inspection-scope \
  MENU_PROFILE=service-packages/inspection-standard.yml \
  SCOPE=engagement-scope.example.yml \
  MENU_OUT=reports/service-packaging
```

The local command evaluates one anonymous schema-v1 scope against one schema-v1 menu
profile. It requires no authentication, cloud access, AI provider, or environment
variable.

| Input | Default | Validation |
|-------|---------|------------|
| `MENU_PROFILE` | `service-packages/inspection-standard.yml` | complete schema-v1 profile with all evaluator condition IDs |
| `SCOPE` | `engagement-scope.example.yml` | positive counts, Boolean special-condition flags, and no unknown fields |
| `MENU_OUT` | `reports/service-packaging` | writable local directory without either output filename |

The command writes byte-deterministic `qualification.json` and `qualification.md` with
the profile identity, supplied scope, eligibility, and every ordered reason. Existing
output fails before publication; a pair-publication failure rolls back files created by
that invocation.

| Exit | Meaning | Caller action |
|------|---------|---------------|
| 0 | both artifacts written | review the qualification before preparing a proposal |
| 2 | invalid/missing input, existing output, or local I/O failure | correct the named path or field and rerun in an empty output location |

The result is preflight sales-support information. It is not collected customer
metadata, an inspection finding, a final price, or approval to perform work.
