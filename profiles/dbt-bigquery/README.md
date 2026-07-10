# Profile: dbt + BigQuery (secure-mart rail)

dbt engine for the mart-build rail (requirements-dbt-dataform-rail.md). Activation is a
copy, per the rail's profile-copy decision — no generator, no meta-compiler.

## Activation

1. Copy [Makefile](Makefile) to the repo root (replaces the terraform-only one; all
   terraform targets are preserved, dbt targets are added).
2. `cp -r profiles/dbt-bigquery/skeleton transform`
3. `cd transform && cp profiles.yml.example profiles.yml` — adjust project/location.
   Local dev authenticates via `gcloud auth application-default login` (oauth method;
   no keyfiles, GR-001).
4. Wire the Terraform outputs into dbt vars (`transform/dbt_project.yml`):
   `terraform -chdir=infra/envs/dev output -json policy_tag_ids` → `policy_tag_high` etc.;
   set `ga4_export_project` / `ga4_export_dataset` to the Google-created export.
5. `make build` — credential-free gate (terraform validate + `dbt parse`).

## Where protection applies (deliberate, not an omission)

| Layer | Materialization | Protection |
|-------|-----------------|-----------|
| staging / intermediate | view | **dataset IAM only** — BigQuery does not support policy tags on view columns |
| marts | table | dataset IAM **+ column policy tags** declared in `_marts__models.yml` |

This implements "protect the mart" (requirements §3.3): the raw export and the view
layers are locked as datasets; column-level security engages where consumers read.

## Execution service account

Attaching tags from dbt needs, on top of BigQuery data access:
`datacatalog.taxonomies.get` + `bigquery.tables.setCategory` (rail FR-2). Wire these to
the deployer/transformer SA — see design-modules-wif-wiring.md.

## Governance declared in the exemplar

- `fct_events`: `partition_by` + `cluster_by` + `require_partition_filter = true` in the
  model config (cost checkpoint #8/#9), policy tags on sensitive columns.
- `stg_ga4__events`: typed unnest of `event_params` keys into real columns (FR-1.3) so
  marts can tag them; promoted keys are an engagement parameter.
- Tests are partition-aware (a `where` window) so `require_partition_filter` tables stay
  testable.
- SQL lint: SQLFluff via `make lint` (cloud-auth-free, so it lives here, not in
  gcp-cicd-workflows). The CI dry-run cost gate (`bq-cost-gate.yml`) is a separate,
  engine-independent workflow — planned in gcp-cicd-workflows.
