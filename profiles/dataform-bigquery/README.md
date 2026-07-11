# Profile: Dataform + BigQuery (secure-mart rail)

Dataform engine for the mart-build rail (requirements-dbt-dataform-rail.md). Activation
is a copy, per the rail's profile-copy decision — no generator, no meta-compiler. Same
governance as `profiles/dbt-bigquery/`, expressed in Dataform config (rail §2.3 mapping
table); pick ONE engine per repository (rail constraint).

## Activation

1. Copy [Makefile](Makefile) to the repo root (replaces the terraform-only one; all
   terraform targets are preserved, Dataform targets are added). Requires the Dataform
   CLI: `npm i -g @dataform/cli`.
2. `cp -r profiles/dataform-bigquery/skeleton transform`
3. Edit `transform/workflow_settings.yaml`: set `defaultProject` / `defaultLocation`
   (MUST equal the Terraform `var.region` — taxonomy location match).
4. Wire the Terraform outputs into the `vars:` block:
   `terraform -chdir=infra/envs/dev output -json policy_tag_ids` → `policy_tag_high`
   etc.; set `ga4_export_project` / `ga4_export_dataset` to the Google-created export.
5. Credentials for `dataform run/test`: `cd transform && dataform init-creds` and pick
   **application-default-credentials**. Never create a JSON key file (GR-001);
   `.df-credentials.json` is gitignored either way.
6. `make build` — credential-free gate (terraform validate + `dataform compile`).

## Where protection applies (deliberate, not an omission)

| Layer | Materialization | Protection |
|-------|-----------------|-----------|
| staging / intermediate | view | **dataset IAM only** — BigQuery does not support policy tags on view columns |
| marts | table | dataset IAM **+ column policy tags** via `bigqueryPolicyTags` in the sqlx config |

This implements "protect the mart" (requirements §3.3): the raw export and the view
layers are locked as datasets; column-level security engages where consumers read.

## Execution service account

Attaching tags from Dataform needs, on top of BigQuery data access:
`datacatalog.taxonomies.get` + `bigquery.tables.setCategory` (rail FR-2). Wire these to
the deployer/transformer SA — see design-modules-wif-wiring.md.

## Governance declared in the exemplar

- `fct_events`: `bigquery.partitionBy` + `clusterBy` + `requirePartitionFilter: true`
  (cost checkpoints #8/#9), `bigqueryPolicyTags` on sensitive columns — full taxonomy
  resource names from Terraform, one tag per column (BigQuery constraint).
- `stg_ga4__events`: typed unnest of `event_params` keys into real columns (FR-1.3) so
  marts can tag them; promoted keys are an engagement parameter.
- Assertions on `requirePartitionFilter` tables are **manual with a partition window**
  (`fct_events_event_name_not_null.sqlx`) — the built-in `nonNull` generates an
  unfiltered query that BigQuery rejects. Assertions materialize into the IAM-locked
  `staging` dataset (`defaultAssertionDataset`), not an unmanaged one.
- Lint: `dataform format` has no check-only mode, so `make lint` enforces the rail
  naming conventions (`stg_*`/`int_*`/`fct_*`/`dim_*`) instead; formatting remains
  `make format`'s job. The CI dry-run cost gate (`bq-cost-gate.yml`) is a separate,
  engine-independent workflow — planned in gcp-cicd-workflows.
