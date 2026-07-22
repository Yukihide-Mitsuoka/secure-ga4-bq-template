---
id: module-inspection
title: Inspection Module
updated: 2026-07-23
---

# Inspection Module

Purpose: the FR-4 inspection engine — collect a read-only configuration snapshot of a
GCP project (BigQuery metadata, project IAM, taxonomies, logging config) and evaluate
the 11 deterministic FR-4 security checkpoints plus additive FR-9 mart-description
governance check into machine-readable findings. It does NOT own
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
| `RunInspection.handle(params) -> Report` | application | snapshot → 12 checks → sorted report; Acceptance B remains CHK-01..CHK-11 |
| `make inspect PARAMS=<yaml>` (`python -m src.modules.inspection.interface.cli`) | interface | engagement params in, `findings.json` + `findings.csv` + `summary.md` out; `--fail-on` gates CI |

## Events

| Direction | Event | Schema | Notes |
|-----------|-------|--------|-------|
| — | — | — | none; the engine is a batch read-evaluate-report pipeline |

## Owned data

None persisted. The module reads GCP configuration via read-only ports and owns only
its report artifacts (`findings.json`, `findings.csv`, `summary.md`) written to a
caller-chosen directory. JSON retains the complete authoritative frame; CSV is only the
flat finding-list projection. The module never mutates any GCP resource.

## Invariants (MUST always hold — each maps to a test)

1. Read-only: no code path calls a mutating Google API (FR-6, GR-030).
2. No BigQuery query jobs: collection is REST metadata only (ADR-0003).
3. Deterministic: identical snapshot + params + catalog ⇒ byte-identical report;
   findings are always sorted by `(check_id, resource)`; time comes from an injected
   Clock, never `datetime.now()` inside domain code.
4. Checks are pure functions `(snapshot, params, catalog) -> list[Finding]`; `domain/`
   imports nothing outside the standard library (ARC-002).
5. Every `Finding.check_id` is one of CHK-01..CHK-12. CHK-01..CHK-11 map 1:1 to the
   closed FR-4 security set; CHK-12 maps to FR-9 and never changes the historical
   Acceptance B denominator.
6. CHK-12 evaluates only table/view and flattened leaf-column descriptions in MART or
   conservative UNMATCHED scope. It issues no query jobs and never grades or parses text.
7. CSV uses the serialized finding vocabulary in a fixed column order, preserves report
   order, emits a header for zero findings, and is byte-deterministic UTF-8 with LF line
   endings. It never duplicates parameters, coverage, or skipped-resource detail from JSON.

## Dependencies

| Uses module | Via | Why |
|-------------|-----|-----|
| — | — | none; `catalog/ga4-sensitivity.yml` is consumed as data via a repository port |

## Layout

```
domain/                 # finding/snapshot/params/catalog/report models + checks/ (12 pure checkpoints)
application/            # ports.py + collect_snapshot.py + run_inspection.py
infrastructure/         # gcp/ adapters, YAML repos, JSON/CSV/Markdown writers, system clock
interface/cli.py        # argparse CLI (make inspect)
```

Tests mirror this at `tests/modules/inspection/` (unit tier + a live-flagged
integration smoke test gated on `INSPECT_LIVE_PROJECT`). Run: `make test-unit`.
