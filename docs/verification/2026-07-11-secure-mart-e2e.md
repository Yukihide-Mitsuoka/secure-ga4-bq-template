---
id: verification-secure-mart-e2e
title: E2E verification — secure mart build (acceptance criteria B, core controls)
status: executed 2026-07-11
---

# E2E verification: Terraform → seed → dbt → column-level security

Live verification of the build rail against a real GCP project. Proves the
acceptance-criteria-B core: clean IaC build with the three controls' data-layer
parts, pseudo-sensitive columns actually protected by column-level security
(requirements-secure-asset.md §8).

| Item | Value |
|------|-------|
| Project | `example-verification-project` (dev; BigQuery unused there before/after — everything below was torn down) |
| Location | `asia-northeast1` (single `var.region` feeds both datasets and taxonomy) |
| Identity | Interactive user via ADC (`gcloud auth application-default login`); WIF/SA paths not exercised (needs GitHub Actions) |
| Branch/commits | `feat/verification-seed` @ `1fa6cb7` + `fix/dbt-skeleton-lint` @ `232348a` |
| Raw logs | `~/verify-logs/` on the workstation (not committed; key excerpts below) |

## Steps and results

| # | Step | Result |
|---|------|--------|
| 1 | Enable APIs (`bigquery`, `datacatalog`; 11 enabled incl. auto-companions, recorded) | OK — reverted after the run |
| 2 | `seed-verification-data.sh -n` (bq dry run) | `Query successfully validated ... 0 bytes` |
| 3 | `terraform apply` `infra/envs/dev` (datasets×3 + taxonomy + tags×3 = 7 resources) | `Apply complete! Resources: 7 added` |
| 4 | `seed-verification-data.sh -p ...` (FR-8 shard `analytics_000000000.events_20260711`) | 5 rows; 3 with `user_id`; 2 with planted emails |
| 5 | `dbt run` + `dbt test` (skeleton wired to terraform `policy_tag_ids` outputs) | PASS=2/2 both; `fct_events` = 5 rows |
| 6 | Column policy tags on `marts.fct_events` | `user_id`,`page_location`→high; `user_pseudo_id`,`geo_city`→medium (matches catalog) |
| 7 | Query untagged column with partition filter | rows returned (control) |
| 8 | **Query `user_id` (high)** | **`Access Denied: ... neither fine-grained reader nor masked get permission ... policy tag "ga4-sensitivity : high" on column ...fct_events.user_id`** — denied even for the project owner |
| 9 | Query without partition filter | `Cannot query over table ... without a filter over column(s) 'event_date'` (checkpoint #9 guard works) |
| 10 | Teardown: drop dbt relations + seed dataset, `terraform destroy` (7 resources), disable the 11 APIs | project returned to its pre-run API/dataset state |

## Defects found by this run (all fixed in the same PRs)

1. **Seed SQL struct-supertype failure** — `UNNEST([STRUCT(...)])` row literals typed
   bare NULLs as INT64 against FLOAT64 fields. Rewritten as UNION ALL with
   helper-emitted fully-cast structs (`1fa6cb7`). Caught by the `-n` dry run.
2. **bq flag-parsing crash** — SQL comment lines (`--`) in a positional query argument
   crash bq's flag suggester (RecursionError). Query now fed via stdin (`1fa6cb7`).
3. **Policy tags silently not attached** — dbt-bigquery applies `policy_tags` only when
   `persist_docs.columns: true`; the skeleton lacked it, so `dbt run` was green while
   high columns stayed readable. Fixed in the skeleton + verified denial (`232348a`).
   This is exactly the failure mode inspection checkpoint #4 (catalog⇔tag consistency)
   exists to catch in customer environments.

## Not covered here (separate verification)

- WIF/deployer/inspector SA paths (`feat/wif-sa-wiring`) — needs GitHub Actions, not
  exercisable from a workstation identity.
- Audit-log 4-layer design (FR-3), data-policy masking (A-3), inspection engine (FR-4).
- Dataform engine profile (compile/run needs `@dataform/cli`; not installed).
