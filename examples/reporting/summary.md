# Inspection summary — sample-project

Captured at: 2026-01-01T00:00:00+00:00

## Coverage (§4.2 denominator)

| Datasets | Tables | Columns | Skipped |
|---------:|-------:|--------:|--------:|
| 1 | 1 | 6 | 0 |

## Findings by severity

- HIGH: 1
- MEDIUM: 0
- LOW: 2
- INFO: 0

## Findings by checkpoint

### CHK-04 (FR-4 #4) — 1

- [HIGH] `projects/sample-project/datasets/sample_mart/tables/customer_daily/columns/customer_email` — no policy tag attached (expected: policy tag level=high (catalog: customer_email -> high); fix: declare policy_tags/bigqueryPolicyTags for this column in the model config)

### CHK-12 (FR-9) — 1

- [LOW] `projects/sample-project/datasets/sample_mart/tables/customer_daily` — table description is missing or blank (expected: mart tables and views declare non-empty descriptions; fix: add an approved description in the owning model)

### CHK-13 (FR-10.1) — 1

- [LOW] `projects/sample-project/datasets/sample_mart/tables/customer_daily/columns/campaign_name` — promotion source declaration is missing source.key (expected: promoted column declares non-empty source.field_path and source.key; fix: complete the structured promotion source declaration and review the transformation separately)
