---
id: design-inspection-engine
title: Implementation design — Inspection engine (FR-4 deterministic checkpoints)
status: implemented-v1.0
updated: 2026-07-12
---

# Implementation design: Inspection engine

- Status: **v1.0 — implemented** (2026-07-12). The §8 series landed on main as
  PRs #13/#14/#15/#19/#22/#23/#24/#25/#26/#27/#28: 11 checkpoints + registry,
  collection adapters, YAML config, use cases, `make inspect` CLI, JSON/Markdown
  reports. 140 unit tests, 98% coverage; the worst-case registry test proves
  all 11 checkpoints fire (B bar ≥10, requirements §8, at unit scale). One
  documented deviation from §6: the CLI ships as `make inspect` / `python -m`
  instead of a console script (non-packaged repo; make is the canonical entry).
  Remaining evidence step: a live run against the FR-8 verification environment.
- Requirements: [requirements-secure-asset.md](requirements-secure-asset.md) FR-4 (11
  deterministic checkpoints), FR-5 (report output — machine-readable part only), FR-6 /
  [design-modules-wif-wiring.md](design-modules-wif-wiring.md) A-5 (inspector
  least-privilege role), FR-7 (engagement parameters), §4.2 (coverage denominator),
  §6 (idempotent, read-only, low scan cost).
- Scope of this design: the **B-level engine** — collect → evaluate 11 checkpoints →
  machine-readable findings + plain Markdown summary. Out of scope: AI-generated
  narrative reports and remediation drafts (A-level, consumes this engine's JSON),
  PII value scanning (A+), the `bq-inspect.yml` CI workflow (lives in
  gcp-cicd-workflows; its CLI contract is defined here).

## 1. Placement and shape

A new bounded context `src/modules/inspection/` (Python, Clean Architecture per
ARC-001/002). Decision and alternatives: ADR-0003.

```
src/modules/inspection/
  MODULE.md
  domain/
    snapshot.py        # ProjectSnapshot and sub-models (frozen dataclasses, stdlib only)
    catalog.py         # sensitivity catalog model + effective-level resolution (FR-1.2)
    params.py          # InspectionParams model (validated engagement parameters, FR-7)
    finding.py         # Finding, Severity, CheckResult, coverage counters
    checks/            # one pure function per checkpoint category
      iam.py           # CHK-01..03
      column_security.py  # CHK-04..05
      audit_logging.py    # CHK-06..07
      cost.py             # CHK-08..10
      dataset_hygiene.py  # CHK-11
  application/
    ports.py           # collection + output ports (see §3), Clock port
    collect_snapshot.py   # use case: assemble ProjectSnapshot via ports
    run_inspection.py     # use case: snapshot → run checks → Report
  infrastructure/
    gcp/               # one adapter per Google API, wraps the HTTP client (COD-041)
      bigquery_metadata.py   # datasets.list/get, tables.list/get
      resource_manager.py    # projects.getIamPolicy (policy v3, incl. auditConfigs)
      data_catalog.py        # taxonomies.list, policyTags.list
      logging_config.py      # sinks.list, exclusions.list
    yaml_catalog_repository.py   # loads catalog/ga4-sensitivity.yml
    yaml_params_repository.py    # loads engagement params file
    json_report_writer.py        # findings.json (stable ordering)
    markdown_report_writer.py    # deterministic summary.md rendering
  interface/
    cli.py             # argparse entry point; boundary validation (COD-011)
tests/modules/inspection/        # mirrors the tree (TST-001)
  unit/                          # pure checks over snapshot builders — no I/O
  integration/                   # adapters against recorded/live responses (flagged)
```

Design invariant (mirrors the repo-wide principle): **the deterministic engine decides;
AI only ever writes text inside the frame of `findings.json`.** Nothing in this module
calls an LLM.

## 2. Data model

### 2.1 ProjectSnapshot (domain)

Everything the 11 checks need, collected once, immutable afterwards. Checks are pure
functions `(snapshot, params, catalog) -> list[Finding]`, which makes determinism and
the ≥80% domain coverage target (TST-003) straightforward.

| Model | Key fields | Collected via |
|-------|-----------|---------------|
| `ProjectIam` | `bindings[{role, members[]}]`, `audit_configs[{service, log_types[], exempted_members[]}]` | `cloudresourcemanager.projects.getIamPolicy` (requestedPolicyVersion=3) |
| `DatasetMeta` | `dataset_id, location, default_table_expiration_ms, default_partition_expiration_ms, cmek_key, access[{role, member}], labels` | `bigquery.datasets.get` |
| `TableMeta` | `table_id, type, num_bytes, creation_time, expiration_time, time_partitioning, range_partitioning, require_partition_filter, clustering_fields, schema_fields[{path, type, policy_tag_ids[]}]` | `bigquery.tables.get` (schema carries `policyTags`; nested fields flattened to dotted paths) |
| `Taxonomy` | `name, location, policy_tags[{id, display_name}]` | `datacatalog.taxonomies.list` + `policyTags.list` |
| `LoggingConfig` | `sinks[{name, destination, filter, disabled}]`, `exclusions[{name, filter, disabled}]` | `logging.sinks.list`, `logging.exclusions.list` |
| `SnapshotMeta` | `project_id, captured_at, skipped[{resource, reason}]` | injected Clock; collection bookkeeping |

**No BigQuery query jobs.** All eleven checkpoints are decidable from REST metadata
alone (`datasets.get` / `tables.get` return partitioning, clustering, expirations,
`numBytes`, and per-field `policyTags`). Consequences:

- Inspection scan cost is **zero bytes billed** — stronger than the NFR "prefer
  INFORMATION_SCHEMA" (§6).
- `bigquery.jobs.create` is **not needed for the B path** and the B environment
  explicitly omits it from the inspector role. The shared A-5 module keeps an
  INFORMATION_SCHEMA-ready default for future A+ consumers; those consumers require a
  separate permission review (design-modules-wif-wiring §D-3).
- Trade-off: one `tables.get` per table instead of one `INFORMATION_SCHEMA` query per
  dataset. Acceptable at ICP scale (hundreds of tables); if a future engagement has
  thousands, add an INFORMATION_SCHEMA-backed adapter behind the same port — the domain
  does not change.

### 2.2 Engagement parameters (FR-7)

One YAML file per engagement (default `inspection-params.yml`), validated at the CLI
boundary. The template ships defaults; engagements override the file, never the code —
same philosophy as `catalog/ga4-sensitivity.yml`.

```yaml
version: 1
project_id: my-project            # required
expected_location: asia-northeast1  # CHK-11 baseline
datasets:
  mart_patterns: ["mart_*", "stg_*"]     # full column-level inspection (coverage denominator)
  raw_patterns: ["analytics_*"]          # containment-only: IAM checks, no column checks
  exclude: []                            # explicitly out of scope, listed in the report
audit:
  high_sensitivity_datasets: []          # FR-3: the only place Data Access logs should target
  retention_max_days: 365                # CHK-07 sink-destination retention ceiling
thresholds:
  large_table_bytes: 10737418240         # 10 GiB — CHK-08
  long_lived_days: 90                    # CHK-10
  require_cmek: false                    # CHK-11: false → CMEK absence is INFO, true → HIGH
catalog_path: catalog/ga4-sensitivity.yml
```

### 2.3 Finding

```
Finding:
  check_id: "CHK-04"          # stable ID, maps 1:1 to FR-4 row number
  severity: HIGH | MEDIUM | LOW | INFO
  resource: "projects/p/datasets/d/tables/t/columns/user_id"   # canonical path
  observed: "no policy tag"                                    # fact
  expected: "policy tag level=high (catalog: user_id -> high)" # rule
  rule_ref: "FR-4 #4"
  remediation_hint: "attach policy_tags in the model config"   # one line, deterministic
```

Findings are sorted by `(check_id, resource)` before output — identical environment ⇒
byte-identical report (idempotence, §6).

## 3. Ports (application layer)

| Port | Methods | Implemented by |
|------|---------|----------------|
| `BigQueryMetadataPort` | `list_datasets`, `get_dataset`, `list_tables`, `get_table` | `infrastructure/gcp/bigquery_metadata.py` |
| `IamPolicyPort` | `get_project_iam_policy` | `resource_manager.py` |
| `TaxonomyPort` | `list_taxonomies(location)` | `data_catalog.py` |
| `LoggingConfigPort` | `list_sinks`, `list_exclusions` | `logging_config.py` |
| `CatalogRepository` | `load() -> SensitivityCatalog` | `yaml_catalog_repository.py` |
| `ParamsRepository` | `load(path) -> InspectionParams` | `yaml_params_repository.py` |
| `ReportWriter` | `write(report, out_dir)` | JSON + Markdown writers |
| `Clock` | `now() -> datetime` | real clock / fixed clock in tests (TST-010) |

Unit tests fake the collection ports with builders; no GCP, no network, deterministic.

## 4. The 11 checkpoints — deterministic rules

Scope note: "in-scope datasets" = matched by `mart_patterns`; `raw_patterns` datasets
get **containment checks only** (CHK-01/02/03 at dataset grain — per §4.2 they are in
the coverage denominator only for closure confirmation); `exclude` datasets are skipped
and listed with reasons.

| ID | FR-4 # | Flag when (deterministic rule) | Severity | Inputs |
|----|--------|--------------------------------|----------|--------|
| CHK-01 | 1 | `roles/owner` or `roles/editor` in project bindings or dataset `access`; `roles/viewer` likewise | HIGH (owner/editor), MEDIUM (viewer) | ProjectIam, DatasetMeta.access |
| CHK-02 | 2 | any member `allUsers` / `allAuthenticatedUsers` in project bindings or dataset access | HIGH | same |
| CHK-03 | 3 | BigQuery data roles (`roles/bigquery.dataViewer/dataEditor/dataOwner/admin`) bound at **project** level (should be dataset/table grain) | MEDIUM | ProjectIam |
| CHK-04 | 4 | column in an in-scope table whose **effective catalog level** (columns ∪ promoted_event_params ∪ overrides, FR-1.2) is high/medium and the schema field has no `policyTags` | HIGH (high-level col), MEDIUM (medium) | TableMeta.schema, catalog |
| CHK-05 | 5 | (a) a column references a policy-tag ID not present in any collected taxonomy (dangling); (b) taxonomy location ≠ dataset location of tagged columns (breaks CLS — design doc cross-cutting constraint); (c) taxonomy defines a tag no column uses (orphan) | HIGH (a,b), INFO (c) | schema, Taxonomy |
| CHK-06 | 6 | `audit_configs` enable `DATA_READ`/`DATA_WRITE` for `allServices`, or for `bigquery.googleapis.com` while `audit.high_sensitivity_datasets` is empty; any sink filter ingesting BigQuery data-access entries without restricting to the declared high-sensitivity datasets | MEDIUM | ProjectIam.audit_configs, sinks, params |
| CHK-07 | 7 | (a) no enabled sink whose filter matches BigQuery audit logs (sink未設定); (b) sink destination is a BQ dataset whose `default_table_expiration_ms` is unset or exceeds `retention_max_days` (保持過大); (c) zero enabled exclusions project-wide (除外フィルタ不在) | MEDIUM (a,b), LOW (c) | sinks, exclusions, DatasetMeta |
| CHK-08 | 8 | `num_bytes ≥ large_table_bytes` and neither time nor range partitioning (missing clustering on such tables → INFO) | MEDIUM | TableMeta, thresholds |
| CHK-09 | 9 | partitioned table with `require_partition_filter` false/unset | LOW | TableMeta |
| CHK-10 | 10 | table age (Clock − creation_time) > `long_lived_days` **and** table `expiration_time` unset **and** dataset default expiration unset | LOW | TableMeta, DatasetMeta, Clock |
| CHK-11 | 11 | (a) dataset location ≠ `expected_location`; (b) `default_table_expiration_ms` unset; (c) CMEK unset — severity per `require_cmek` | MEDIUM (a), LOW (b), INFO/HIGH (c) | DatasetMeta, params |

Known limitation (recorded, not silently dropped): CHK-07(b) retention is only
verifiable for **BigQuery** sink destinations; GCS bucket lifecycle would need
`storage.buckets.get`, which the A-5 role deliberately does not include. GCS
destinations are reported as `INFO: retention not verifiable with inspector role`.

## 5. Output (FR-5, machine-readable part)

`inspect` produces into `--out-dir` (default `reports/<project>/<timestamp>/`):

- `findings.json` — `{meta: SnapshotMeta+params digest, coverage: {datasets, tables,
  columns, skipped[]}, findings[]}`. Stable key order and finding sort. This is the
  **frame** the A-level AI report generator will consume.
- `summary.md` — deterministic template rendering: coverage table, findings grouped by
  check, severity counts. No LLM involved.

Coverage counters implement §4.2's 100%-coverage denominator: every in-scope dataset,
table, and column is either evaluated or listed in `skipped[]` with a reason.

## 6. CLI contract (consumed by bq-inspect.yml later)

```
uv run ga4-bq-inspect --params inspection-params.yml [--out-dir reports/] [--fail-on HIGH]
```

- Exit 0 = ran to completion (findings themselves do not fail the run); `--fail-on`
  optionally gates CI on a severity floor.
- Read-only by construction: the module contains no mutating API call (FR-6 / GR-030).
- Auth: Application Default Credentials — works with `gcloud auth` locally and WIF in
  CI unchanged.

## 7. Toolchain integration

- Root gains `pyproject.toml` managed with **uv** (python-uv profile), dependencies per
  ADR-0003.
- Root Makefile merges python-uv targets with the existing terraform ones:
  `format` = terraform fmt + ruff format; `lint` = terraform fmt-check/tflint + ruff
  check + mypy; `test-unit` = pytest unit tier + terraform fmt-check; `test-integration`
  = terraform test + pytest integration tier; `coverage` = pytest --cov (ratchet,
  TST-003). Contract semantics (profiles/README.md) unchanged.
- New extension target: `make inspect PARAMS=<file>`.

## 8. Delivery plan (GR-020-sized slices)

| PR | Content | ~size |
|----|---------|-------|
| 1 | ADR-0003 + this design + index updates | docs only |
| 2 | pyproject/uv + Makefile python wiring + module skeleton + MODULE.md | small |
| 3 | domain models (snapshot/params/catalog/finding) + builders + unit tests | medium |
| 4 | CHK-01..05 (IAM + column security) + tests | medium |
| 5 | CHK-06..11 (audit + cost + hygiene) + tests | medium |
| 6 | collection adapters + integration tests | medium |
| 7 | use cases + CLI + report writers + E2E against FR-8 verification env | medium |

Each PR lands green and releasable; effort tracks requirements §9.2 (点検エンジン
8–12 person-days: collection 3–4, checks 3–5, report 2–3).

## 9. Open points carried into implementation

1. CHK-06 sink-filter matching: exact BigQuery data-access filter grammar to recognize
   (start with the two house patterns from FR-3 layer 2/3; extend by evidence).
2. ~~`roles/viewer` severity~~ **Settled 2026-07-11 (owner)**: viewer IS detected,
   at MEDIUM; owner/editor stay HIGH (LOG-0014).
3. ~~Placeholder `src/modules/catalog/` deletion~~ **Settled 2026-07-11 (owner)**:
   delete as soon as it is no longer needed — i.e. in the PR that lands the real
   inspection module skeleton (LOG-0014).
