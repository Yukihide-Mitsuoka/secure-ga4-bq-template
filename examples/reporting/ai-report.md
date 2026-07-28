# AI-generated inspection report

> Sample only: this narrative was written manually to preview the output format. It is not
> an AI-generated result or Acceptance evidence. Human review is required, and deterministic
> findings remain authoritative.

- Project: `sample-project`
- Captured at: `2026-01-01T00:00:00+00:00`
- Coverage: 1 datasets, 1 tables, 6 columns
- Generator: `sample` / `manual-preview-v1`

## Executive summary

One high-severity column-protection finding and two low-severity metadata findings require
review. Prioritize the missing Policy Tag, then complete the documentation declarations.

## F001: CHK-04

- Severity: **HIGH**
- Resource: `projects/sample-project/datasets/sample_mart/tables/customer_daily/columns/customer_email`
- Rule: `FR-4 #4`

### Explanation

The catalog classifies this column as high sensitivity, but the schema does not reference a
Policy Tag. Access controls expected for the catalog level therefore cannot be confirmed.

### Deterministic remediation hint

declare policy\_tags/bigqueryPolicyTags for this column in the model config

### Next action

Confirm the approved taxonomy and attach its high-sensitivity Policy Tag through the owning model.

## F002: CHK-12

- Severity: **LOW**
- Resource: `projects/sample-project/datasets/sample_mart/tables/customer_daily`
- Rule: `FR-9`

### Explanation

The mart table has no usable description, so consumers cannot confirm its intended purpose from
BigQuery metadata alone.

### Deterministic remediation hint

add an approved description in the owning model

### Next action

Have the data owner approve a concise description and add it to the version-controlled model.

## F003: CHK-13

- Severity: **LOW**
- Resource: `projects/sample-project/datasets/sample_mart/tables/customer_daily/columns/campaign_name`
- Rule: `FR-10.1`

### Explanation

The promoted column declaration omits the source key. The declaration is incomplete and does not
record which nested value is intended, but completing it will not prove SQL lineage.

### Deterministic remediation hint

complete the structured promotion source declaration and review the transformation separately

### Next action

Record the approved source key and separately review the transformation that produces the column.

## Generation metadata

- Request ID: `not-applicable-sample`
