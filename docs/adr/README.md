---
id: adr-index
title: Architecture Decision Records
---

# Architecture Decision Records (ADR)

Immutable records of decisions with long-term consequences. Required by GR-022 for any
architectural change (definition: ARC-020 "Architectural" scope). Process:
`.skills/architecture.skill.md`.

## Rules

- Numbered sequentially: `NNNN-kebab-case-title.md`. Copy [0000-template.md](0000-template.md).
- Status flow: `proposed → accepted | rejected`; later `deprecated` or
  `superseded by ADR-NNNN`. **Accepted ADRs are never edited** — supersede them.
- One decision per ADR. Keep it under ~2 pages.
- The ADR PR is approved by a human before implementation starts (GR-022).
- Every ADR gets a line in [.ai/decision-log.md](../../.ai/decision-log.md).

## Index

| # | Title | Status | Date |
|---|-------|--------|------|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | accepted | 2026-07-02 |
| [0002](0002-ai-facing-docs-in-english.md) | AI-facing docs are written in English | accepted | 2026-07-02 |
| [0003](0003-inspection-engine-python-module.md) | Build the FR-4 inspection engine as a Python module using REST metadata only | accepted | 2026-07-11 |
| [0004](0004-isolate-ai-report-generation.md) | Isolate AI report generation behind a reporting boundary | accepted | 2026-07-12 |
| [0005](0005-render-remediation-drafts-from-recipes.md) | Render remediation drafts from deterministic recipes | accepted | 2026-07-13 |
| [0006](0006-bind-cost-gate-wif-to-trusted-workflow.md) | Bind cost-gate WIF to the trusted reusable workflow | accepted | 2026-07-13 |
| [0007](0007-generate-service-packages-from-versioned-profiles.md) | Generate service packages from versioned profiles | accepted | 2026-07-15 |
| [0008](0008-adopt-direct-parent-inheritance-contract.md) | Adopt the direct-parent inheritance contract | proposed | 2026-07-16 |

<!-- Append new ADRs to this table (newest last). -->
