---
id: secure-ga4-bq-adr-index
title: Secure GA4 BigQuery Template Architecture Decision Records
---

# Secure GA4 BigQuery Template Architecture Decision Records

This directory contains decisions owned by `secure-ga4-bq-template`. Inherited foundation
decisions from the direct parent chain are synchronized under
[`docs/foundation/adr/`](../foundation/adr/).

## Rules

- Numbered sequentially: `NNNN-kebab-case-title.md`. Copy the
  [foundation ADR template](../foundation/templates/adr.md).
- Status flow: `proposed → accepted | rejected`; later `deprecated` or
  `superseded by ADR-NNNN`. **Accepted ADRs are never edited** — supersede them.
- One decision per ADR. Keep it under ~2 pages.
- The ADR PR is approved by a human before implementation starts (GR-022).
- Every ADR gets a line in [.ai/decision-log.md](../../.ai/decision-log.md).

## Index

| # | Title | Status | Date |
|---|-------|--------|------|
| [0003](0003-inspection-engine-python-module.md) | Build the FR-4 inspection engine as a Python module using REST metadata only | accepted | 2026-07-11 |
| [0004](0004-isolate-ai-report-generation.md) | Isolate AI report generation behind a reporting boundary | accepted | 2026-07-12 |
| [0005](0005-render-remediation-drafts-from-recipes.md) | Render remediation drafts from deterministic recipes | accepted | 2026-07-13 |
| [0006](0006-bind-cost-gate-wif-to-trusted-workflow.md) | Bind cost-gate WIF to the trusted reusable workflow | accepted | 2026-07-13 |
| [0007](0007-generate-service-packages-from-versioned-profiles.md) | Generate service packages from versioned profiles | accepted | 2026-07-15 |
| [0008](0008-adopt-direct-parent-inheritance-contract.md) | Adopt the direct-parent inheritance contract | accepted | 2026-07-16 |
| [0009](0009-expose-confirmed-local-governance-apply.md) | Expose confirmed local governance apply | accepted | 2026-07-17 |
| [0010](0010-separate-foundation-and-project-document-ownership.md) | Separate foundation and project document ownership | accepted | 2026-07-19 |
| [0011](0011-record-structured-promoted-column-lineage.md) | 昇格列の出所を構造化カタログで記録する | proposed | 2026-07-23 |

<!-- Append new Secure GA4 ADRs to this table (newest last). -->
