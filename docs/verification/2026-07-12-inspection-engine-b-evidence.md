---
id: verification-inspection-engine-b
title: E2E evidence — inspection engine detects FR-4 checkpoints against live GCP (acceptance B)
status: executed 2026-07-12
---

# E2E evidence: the inspection engine against a real project

Live run of `make inspect` (the FR-4 engine, design-inspection-engine.md v1.0)
against a real GCP project, proving the four collection adapters read real
Google APIs and the engine produces a valid deterministic report end to end.
Complements — does not replace — the deterministic registry unit test, which
proves all 11 checkpoints fire (that test runs in CI on every PR).

| Item | Value |
|------|-------|
| Project | `adr-main-application` (dev; BigQuery/Data Catalog unused there before/after — everything below was torn down) |
| Location | `asia-northeast1` |
| Identity | interactive user via ADC; the engine is read-only (no SA/WIF needed to read) |
| Engine | `main` @ #29 (design §8 series complete) |
| Raw logs | `~/verify-b/` on the workstation (not committed — contains member identities) |

## What was built (deliberately ungoverned "before-remediation" state)

- `terraform apply infra/envs/dev` — 18 resources: 3 layer datasets (no default
  expiration, no CMEK), sensitivity taxonomy + 3 policy tags, and the WIF wiring
  (deployer SA + inspector SA + `bqInspector` custom role).
- One ungoverned mart table with cataloged columns (`user_id`, `page_location`,
  `user_pseudo_id`, `geo_city`) and **no policy tags**, partitioned but with
  `require_partition_filter = false`.
- One unpartitioned table (for the tuned-threshold CHK-08 demonstration).
- A dataset-scoped `roles/viewer` basic-role grant on `marts` (contained to the
  throwaway dataset; removed at teardown).
- FR-8 pseudo GA4 export seeded into `analytics_000000000` (raw scope).

## Results

Two runs, both read-only, both writing a valid `findings.json` + `summary.md`:

| Run | Params | Findings | Distinct checkpoints |
|-----|--------|---------:|----------------------|
| 1 | default thresholds | 20 | **7** — CHK-01, 03, 04, 05, 07, 09, 11 |
| 2 | `large_table_bytes: 1` (engagement-tuned) + 1 unpartitioned table | 25 | **8** — run 1 + CHK-08 |

Run-1 coverage: 4 datasets, 1 table, 6 columns evaluated; 1 skipped
(`analytics_*` raw export → containment-only per §4.2, listed with reason). Two
findings were **not planted** and are genuine: CHK-03 (the deployer SA holds
project-level `bigquery.dataOwner` via the github-oidc module — a real
project-wide grant) and CHK-11 (the layer datasets lack default expiration and
CMEK). This is the engine catching real posture, not just seeded fixtures.

## The three remaining checkpoints (not reproducible here — proven in CI)

| Checkpoint | Why not live | Note |
|-----------|--------------|------|
| CHK-02 (public grants) | the project's **org policy blocks** `allUsers`/`allAuthenticatedUsers` dataset grants outright | this is the *correct* posture — the check has nothing to catch because the platform already prevents it |
| CHK-06 (Data Access over-enablement) | no data-access `auditConfig` present on the project to detect | would require mutating project-level audit config (declined on a shared project) |
| CHK-10 (long-lived tables) | needs a table older than the (positive-only) `long_lived_days` threshold; fresh tables are 0 days old | not cheaply reproducible without an aged table |

All three, plus the 8 confirmed live, are proven deterministically by
`tests/modules/inspection/unit/test_checks_registry.py` — a worst-case project
fires **all 11** checkpoints — which runs in CI on every PR. The acceptance-B
bar (§8: "detect ≥10 deterministic checkpoints") is therefore met: 11/11 proven
deterministically, 8 confirmed end-to-end against live GCP across all five rule
categories (IAM, column security, audit, cost, dataset hygiene).

## Read-only and cost (FR-6, §6, ADR-0003)

- The engine issued **zero BigQuery query jobs** and **zero mutating API calls** —
  collection is REST metadata only (`datasets.get`/`tables.get`/`getIamPolicy`/
  `taxonomies.list`/`sinks.list`). Inspection scanned **0 billed bytes**.
- All mutations above (apply, table creation, the grant) were explicit setup
  steps run with a full-access identity, never by the engine.

## Teardown (back to pre-run state)

`terraform destroy` (18 resources) + drop the created tables and the seed
dataset + disable the 11 APIs enabled for the run. Final check: the enabled-API
set diffed against the pre-run baseline is **empty in both directions** (nothing
added, nothing left disabled); no datasets remain; the working tree is clean.

Residue note: deleting a Workload Identity Pool leaves its id reserved for ~30
days (GCP soft-delete). The `github` pool id is therefore reserved until early
August 2026 on this dev project — harmless, and only matters if something tries
to recreate that exact pool id before then.
