---
id: verification-public-ga4-dry-run
title: Live evidence — public GA4 Dataform compilation and source dry run
status: executed 2026-07-14
---

# Live evidence: public GA4 source dry run

This run proves that the Dataform profile compiles against Google's public GA4
ecommerce sample with isolated managed-layer dataset IDs and that the source-facing
staging SQL validates in BigQuery without executing a query or creating a persistent
resource.

## Result

| Item | Observed value |
|------|----------------|
| Repository commit | `3af6a45` in [PR #59](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/pull/59), merged as `7e88642` |
| Source | `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*` |
| Source location | `US` |
| Billing project | `adr-main-application` |
| Generated targets | `ga4_verify_example_staging` and `ga4_verify_example_marts` in the example project |
| Compilation | Credential-free; exported three SQL files: staging, mart, and assertion |
| Staging dry-run estimate | `1,604,088,078` bytes |
| Persistent resources created | None |
| APIs changed | None; the already-enabled BigQuery API was used |

The Dataform project was activated under a temporary local directory from
[`public-ga4-workflow-settings.yaml.example`](../../profiles/dataform-bigquery/public-ga4-workflow-settings.yaml.example).
The compile target completed with `found 0 vulnerabilities` and reported:

```text
exported 3 Dataform SQL file(s) to target/compiled
```

The generated staging SQL contained this fully qualified source reference:

```sql
from `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
```

## BigQuery command and output

The executed command used only BigQuery's documented
[`--dry_run`](https://cloud.google.com/bigquery/docs/running-queries#dry-run) mode:

```bash
bq query \
  --project_id=adr-main-application \
  --location=US \
  --use_legacy_sql=false \
  --dry_run \
  < target/compiled/tables/example-verification-project__ga4_verify_example_staging__stg_ga4__events.sql
```

Observed output:

```text
Query successfully validated. Assuming the tables are not modified, running this query will process 1604088078 bytes of data.
```

## Scope limitation

This run validates credential-free compilation, public-source resolution, isolated
target naming, and the source query's byte estimate. It does not prove the downstream
mart or assertion dry runs because their temporary managed datasets do not exist yet.
It did not materialize data, attach policy tags, run the 100% inspection, generate the
same-scope AI report, configure GitHub variables, or exercise WIF. Those operations
remain a separately approved temporary cloud run.
