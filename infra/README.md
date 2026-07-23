---
id: infra
title: Terraform layout
---

# infra/ — Terraform root configurations

| Path | Role |
|------|------|
| `envs/<env>/` | One root config per environment (start: `dev`). State and providers live here |

Rules:

- **Modules are referenced, never vendored.** Building blocks come from
  [terraform-gcp-modules](https://github.com/Yukihide-Mitsuoka/terraform-gcp-modules)
  pinned by tag: `source = "git::https://github.com/Yukihide-Mitsuoka/terraform-gcp-modules.git//modules/<name>?ref=vX.Y.Z"`.
  Upgrading = bumping `?ref=` in a reviewed PR. Do not copy module code into this repo;
  a module worth writing is worth contributing to the library.
- Truly project-specific glue (a one-off resource, a local wrapper) may live beside the
  env's `main.tf`; if it grows reusable, promote it to the library (rule of three, COD-020).
- `make build` validates every env without credentials; `make plan ENV=dev` needs
  credentials and a configured backend (`versions.tf`).

## This template's dev env

`envs/dev/` is the acceptance-criteria-B verification environment: three layer datasets
(`staging` / `intermediate` / `marts`) plus the sensitivity taxonomy, wired to
`bigquery-dataset` and `bigquery-policy-tags` at `?ref=v0.3.0`. Engagement parameters
(FR-7) enter via `layer_iam_members`, `fine_grained_readers`, and the opt-in
`data_policies`; the raw `analytics_*` export dataset is Google-created and locked down
out of band (requirements §3.3).

### Optional column masking

`data_policies` is empty by default and therefore creates no masking resources. Each map
entry binds one supported predefined masking expression to one sensitivity level through
`bigquery-data-policy` at `?ref=v0.4.0`:

```hcl
data_policies = {
  mask_high_email = {
    policy_tag_level      = "high"
    predefined_expression = "EMAIL_MASK"
    masked_readers = [
      "serviceAccount:masked-reader@example-project.iam.gserviceaccount.com",
    ]
  }
}
```

The root grants only `roles/bigquerydatapolicy.maskedReader` through the module. Configure
dataset-level `roles/bigquery.dataViewer` separately with `layer_iam_members`, and grant
`roles/datacatalog.categoryFineGrainedReader` through `fine_grained_readers` only to
members that must see cleartext. Query identities also need an engagement-owned
`bigquery.jobs.create` grant; the masking input never creates project-level IAM.

Only one masking policy may target each `high`, `medium`, or `low` tag. Unsupported
expressions, unknown levels, public principals, and invalid policy IDs fail during input
validation.

### Verification data (FR-8)

`scripts/seed-verification-data.sh` seeds a pseudo GA4 export shard
(`analytics_000000000.events_YYYYMMDD`, nested export shape, no real PII) covering the
whole catalog: `user_id`/planted emails (high), `user_pseudo_id`/`geo.city` (medium),
`page_location`/`page_referrer` keys for typed promotion (FR-1.3), and a
`?email=` query-string row for the A+ value-scan demo. Idempotent; point the dbt vars
`ga4_export_project`/`ga4_export_dataset` at the seeded dataset.

### WIF wiring (deployer / inspector / cost-gate SAs)

`wif.tf` wires the **deployer SA** (terraform plan/apply) and **inspector SA**
(metadata-only inspection). `cost_gate_wif.tf` adds the ADR-0006 boundary: a dedicated
provider accepts only the configured numeric caller repository ID and exact released
`bq-cost-gate.yml` ref, then lets the **cost-gate SA** create dry-run jobs. That SA has
BigQuery Data Viewer only on the managed layers and datasets listed in
`cost_gate_source_datasets`; it has no write role or project-wide data access.

After apply, set GitHub repository variables from the outputs:
`WIF_PROVIDER` / `DEPLOYER_SA` / `INSPECTOR_SA` plus
`COST_GATE_WIF_PROVIDER` / `COST_GATE_SA`. Raw `analytics_*` or cross-project datasets
referenced by compiled SQL must be listed in `cost_gate_source_datasets`. The cost-gate
caller is wired separately and must use the same immutable workflow release recorded in
`cost_gate_workflow_ref`; a mismatch rejects authentication.

Caller workflows that consume these identities (`tf-plan`/`tf-apply`/`bq-inspect` and
the cost gate from gcp-cicd-workflows) are wired separately. The opt-in cost-gate caller
is [`.github/workflows/bq-cost-gate.yml`](../.github/workflows/bq-cost-gate.yml); configure
its compile/glob/budget variables before setting `BQ_COST_GATE_ENABLED=true`.
The inspection caller is [`.github/workflows/bq-inspect.yml`](../.github/workflows/bq-inspect.yml):
run it manually after setting the variables and `inspection-params.yml`, then set
`BQ_INSPECT_ENABLED=true` to opt in to its weekly schedule.

Update triggers: new env → new `envs/<env>/`; new module reference → bump/pin note in the
PR; backend change → `versions.tf` + `docs/deployment/`.
