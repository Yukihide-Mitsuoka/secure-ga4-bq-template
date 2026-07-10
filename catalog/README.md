---
id: catalog
title: GA4 Sensitivity Catalog
updated: 2026-07-11
---

# catalog/ — GA4 sensitivity catalog

[ga4-sensitivity.yml](ga4-sensitivity.yml) maps GA4-derived column names to sensitivity
levels (`high`/`medium`/`low`). It is the single source both modes consume
(requirements FR-1.1/FR-1.2):

| Consumer | How |
|----------|-----|
| Build mode (dbt/Dataform) | Every `policy_tags` declaration in the model YAML must agree with the catalog level for that column (level → tag resource name via `terraform output policy_tag_ids`) |
| Inspect mode (planned) | Checkpoint #4: a column the catalog marks `high`/`medium` that carries no policy tag is a finding; checkpoint #5 cross-checks tag/taxonomy integrity |

Rules:

- **Defaults stay unchanged in engagements.** Re-leveling (e.g. `user_pseudo_id` → `high`
  for a regulated client) goes in `overrides:` only — that keeps the template body
  identical across engagements (FR-1.2/FR-7) and the diff reviewable.
- The `levels` list must match the Terraform taxonomy levels
  (`bigquery-policy-tags` module `levels` input); both default to the same 3 tiers.
- Consistency between this file and the model YAML is currently maintained by review;
  the inspector automates the check when it lands (do not build a generator — rail
  decision: no meta-compiler).

Update triggers: new mart column carrying user data → add it here in the same PR
(DOC-030 "new domain term" spirit); taxonomy level change → update `levels` + the
Terraform input together.
