---
id: module-inspection
title: Inspection Module
updated: 2026-07-11
---

# Inspection Module

Purpose: the FR-4 inspection engine — collect a read-only configuration snapshot of a
GCP project (BigQuery metadata, project IAM, taxonomies, logging config) and evaluate
the 11 deterministic checkpoints into machine-readable findings. It does NOT own
remediation application (FR-5: drafts only, humans apply), AI report generation
(A-level, consumes this module's JSON output), or PII value scanning (A+).

Architecture decision: [ADR-0003](../../../docs/adr/0003-inspection-engine-python-module.md)
— REST metadata only, **no BigQuery query jobs**. Detailed design:
[design-inspection-engine.md](../../../docs/requirements/design-inspection-engine.md).

## Public API (the contract — everything else in this module is private)

| Entry point | Layer | Description |
|-------------|-------|-------------|
| `Finding`, `Severity`, `sorted_findings` | domain | Output vocabulary every consumer reads |
| `Report`, `Coverage` | domain | The complete output frame: findings + §4.2 coverage + params echo |
| `RunInspection.handle(params) -> Report` | application | snapshot → 11 checks → sorted report |
| `make inspect PARAMS=<yaml>` (`python -m src.modules.inspection.interface.cli`) | interface | engagement params in, `findings.json` + `summary.md` out; `--fail-on` gates CI |

## Events

| Direction | Event | Schema | Notes |
|-----------|-------|--------|-------|
| — | — | — | none; the engine is a batch read-evaluate-report pipeline |

## Owned data

None persisted. The module reads GCP configuration via read-only ports and owns only
its report artifacts (`findings.json`, `summary.md`) written to a caller-chosen
directory. It never mutates any GCP resource.

## Invariants (MUST always hold — each maps to a test)

1. Read-only: no code path calls a mutating Google API (FR-6, GR-030).
2. No BigQuery query jobs: collection is REST metadata only (ADR-0003).
3. Deterministic: identical snapshot + params + catalog ⇒ byte-identical report;
   findings are always sorted by `(check_id, resource)`; time comes from an injected
   Clock, never `datetime.now()` inside domain code.
4. Checks are pure functions `(snapshot, params, catalog) -> list[Finding]`; `domain/`
   imports nothing outside the standard library (ARC-002).
5. Every `Finding.check_id` is one of CHK-01..CHK-11, mapping 1:1 to the FR-4 table.

## Dependencies

| Uses module | Via | Why |
|-------------|-----|-----|
| — | — | none; `catalog/ga4-sensitivity.yml` is consumed as data via a repository port |

## Layout

```
domain/                 # finding/snapshot/params/catalog/report models + checks/ (11 pure checkpoints)
application/            # ports.py + collect_snapshot.py + run_inspection.py
infrastructure/         # gcp/ discovery-client adapters, YAML repos, JSON/Markdown report writers, system clock
interface/cli.py        # argparse CLI (make inspect)
```

Tests mirror this at `tests/modules/inspection/` (unit tier + a live-flagged
integration smoke test gated on `INSPECT_LIVE_PROJECT`). Run: `make test-unit`.
