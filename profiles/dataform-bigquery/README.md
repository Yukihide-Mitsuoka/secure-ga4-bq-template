# Profile: Dataform + BigQuery (secure-mart rail)

Dataform engine for the mart-build rail (requirements-dbt-dataform-rail.md). Activation
is a copy, per the rail's profile-copy decision — no generator, no meta-compiler. Same
governance as `profiles/dbt-bigquery/`, expressed in Dataform config (rail §2.3 mapping
table); pick ONE engine per repository (rail constraint).

## Activation

1. Copy [Makefile](Makefile) to the repo root (replaces the terraform-only one; all
   terraform targets are preserved, Dataform targets are added). Requires Node.js
   20-24 and npm; Dataform CLI/Core versions come only from the checked-in lockfile.
2. `cp -r profiles/dataform-bigquery/skeleton transform`
3. Edit `transform/workflow_settings.yaml`: set `defaultProject` / `defaultLocation`
   (MUST equal the Terraform `var.region` — taxonomy location match).
4. Wire the Terraform outputs into the `vars:` block:
   `terraform -chdir=infra/envs/dev output -json policy_tag_ids` → `policy_tag_high`
   etc.; set `ga4_export_project` / `ga4_export_dataset` to the Google-created export.
5. Credentials for `dataform run/test`: `cd transform && dataform init-creds` and pick
   **application-default-credentials**. Never create a JSON key file (GR-001);
   `.df-credentials.json` is gitignored either way.
6. `make setup && make build` — lockfile install plus credential-free validation.

## Cost-gate compilation

The profile provides `make compile-cost-gate`. It runs `npm ci --ignore-scripts`,
compiles the Dataform graph without ADC, and exports table, assertion, and operation
queries as regular SQL under `transform/target/compiled/`. Configure the caller with:

- `BQ_COST_GATE_COMPILE_COMMAND=make compile-cost-gate`
- `BQ_COST_GATE_SQL_GLOB=transform/target/compiled/**/*.sql`

Compilation errors, empty queries, duplicate output paths, and unmarked output
directories fail closed before WIF authentication. The package lock pins Dataform
CLI/Core and overrides the vulnerable `parse-duration` transitive dependency.

## Public GA4 verification in a shared project

Use [the public GA4 settings example](public-ga4-workflow-settings.yaml.example) to
compile against Google's obfuscated ecommerce export without copying or changing the
source dataset. The source is in `US`, so the temporary Terraform datasets, taxonomy,
and Dataform `defaultLocation` MUST also use `US`.

1. Give all three Terraform `layer_dataset_ids`, `github_workload_identity_pool_id`,
   and `deployer_service_account_id` unique values; do not use global default names in
   a shared project. Set a unique `taxonomy_display_name` as well.
2. Activate the profile, then replace `transform/workflow_settings.yaml` with the
   example. Change `defaultProject` and the three dataset IDs to match Terraform.
3. Keep `cost_gate_source_datasets` empty for this source. That input creates IAM
   bindings and is only for private datasets whose IAM the caller is allowed to manage;
   the public sample remains Google-managed.
4. Run `make compile-cost-gate`. This installs only lockfile-pinned tooling, needs no
   ADC, and emits regular SQL for a no-charge BigQuery dry run.
5. Replace the example policy-tag paths with Terraform output only before a credentialed
   Dataform run. Delete every temporary managed resource after live verification.

Before any Terraform apply, validate the source-facing staging SQL and obtain its byte
estimate. With the unchanged example names, run:

```bash
bq query \
  --project_id=example-verification-project \
  --location=US \
  --use_legacy_sql=false \
  --dry_run \
  < transform/target/compiled/tables/example-verification-project__ga4_verify_example_staging__stg_ga4__events.sql
```

Replace only the billing project when using the unchanged example. If dataset IDs or the
project in `workflow_settings.yaml` changed, use the matching generated filename. This
dry run validates the public source query without executing it; it does not validate the
downstream mart and assertion queries, which reference temporary managed datasets that do
not exist until the separately approved apply.

The public sample is suitable for development and a production-equivalent technical
proof, but it is not evidence of applying the asset to a real customer engagement.

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
  `make format`'s job. The CI dry-run cost gate uses the separate, engine-independent
  `gcp-cicd-workflows` v2 workflow.
