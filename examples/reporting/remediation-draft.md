# Deterministic remediation draft

> Sample only. Do not apply directly. Human review, repository adaptation, plan, and engagement
> approval are required.

- Project: `sample-project`
- Captured at: `2026-01-01T00:00:00+00:00`
- Recipe version: `v1`
- Findings: 3

## F001: CHK-04

- Severity: **HIGH**
- Resource: `projects/sample-project/datasets/sample_mart/tables/customer_daily/columns/customer_email`
- Rule: `FR-4 #4`
- Recipe: `COLUMN_POLICY_TAG_V1` (policy-json)

### Attach the catalog-required policy tag to the column schema

Required inputs:

- `column_name`
- `column_type`
- `policy_tag_resource_name`

### Draft example

```json
{
  "name": "REPLACE_ME_COLUMN_NAME",
  "type": "REPLACE_ME_COLUMN_TYPE",
  "policyTags": {"names": ["REPLACE_ME_POLICY_TAG_RESOURCE_NAME"]}
}
```

### Validation

1. Validate the draft against the engagement policy and current GCP metadata.
2. Confirm the scope and retention values with the data owner.
3. Record human approval before translating the draft into configuration.

## F002: CHK-12

- Severity: **LOW**
- Resource: `projects/sample-project/datasets/sample_mart/tables/customer_daily`
- Rule: `FR-9`
- Recipe: `MART_DESCRIPTION_V1` (manual)

### Add the missing mart metadata description

Required inputs:

- `owning_model`
- `resource_name`
- `approved_description`

### Draft example

No safe code example can be inferred. Complete the required inputs and follow the validation
procedure.

### Validation

1. Identify the owning dbt, Dataform, Terraform, or DDL definition.
2. Add an approved non-empty description to the table, view, or leaf column.
3. Deploy through the reviewed workflow and rerun the inspection.

## F003: CHK-13

- Severity: **LOW**
- Resource: `projects/sample-project/datasets/sample_mart/tables/customer_daily/columns/campaign_name`
- Rule: `FR-10.1`
- Recipe: `PROMOTION_SOURCE_V1` (manual)

### Complete the promoted-column source declaration

Required inputs:

- `owning_model`
- `target_column`
- `source_field_path`
- `source_key`

### Draft example

No safe code example can be inferred. Complete the required inputs and follow the validation
procedure.

### Validation

1. Identify the owning model and intended nested source field and key.
2. Add non-empty source.field_path and source.key to the promoted column entry.
3. Review the transformation separately; the declaration does not prove SQL lineage.
4. Rerun the inspection and confirm CHK-13 is absent.

No changes were applied or submitted by this sample.
