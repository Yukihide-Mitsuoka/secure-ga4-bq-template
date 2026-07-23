---
id: catalog
title: GA4 Sensitivity Catalog
updated: 2026-07-23
---

# catalog/ — GA4 sensitivity catalog

[ga4-sensitivity.yml](ga4-sensitivity.yml) maps GA4-derived column names to sensitivity
levels (`high`/`medium`/`low`). It is the single source both modes consume
(requirements FR-1.1/FR-1.2):

| Consumer | How |
|----------|-----|
| Build mode (dbt/Dataform) | Every `policy_tags` declaration in the model YAML must agree with the catalog level for that column (level → tag resource name via `terraform output policy_tag_ids`) |
| Inspect mode | CHK-04 reports cataloged `high`/`medium` columns without a policy tag; CHK-05 cross-checks tag/taxonomy integrity |

Rules:

- **Defaults stay unchanged in engagements.** Re-leveling (e.g. `user_pseudo_id` → `high`
  for a regulated client) goes in `overrides:` only — that keeps the template body
  identical across engagements (FR-1.2/FR-7) and the diff reviewable.
- The `levels` list must match the Terraform taxonomy levels
  (`bigquery-policy-tags` module `levels` input); both default to the same 3 tiers.
- `promoted_columns` uses the target flattened leaf-column path as its key. `level`
  drives CHK-04; `source.field_path` and `source.key` record declaration lineage without
  asserting that transformation SQL is correct.
- Source values are not GA4 enums. The shipped file uses `event_params`, but engagements
  can declare any nested field path and key without a Python change.
- Catalog version 1 remains readable throughout 2.x. Its `promoted_event_params` entry is
  interpreted as `field_path: event_params` with a source key equal to the target key.
  New or changed catalogs use version 2; version 1 removal can occur no earlier than an
  explicit 3.0.0 breaking change.
- CHK-13 production is intentionally deferred to the next Issue #235 implementation
  slice. Until then, the reader preserves missing source values but emits no lineage
  finding.

Version 2 promotion example:

```yaml
version: 2
levels: [high, medium, low]
promoted_columns:
  page_location:
    level: high
    source:
      field_path: event_params
      key: page_location
```

Update triggers: new mart column carrying user data → add it here in the same PR
(DOC-030 "new domain term" spirit); taxonomy level change → update `levels` + the
Terraform input together; promoted target or extraction-key change → update the target
and `source` together.
