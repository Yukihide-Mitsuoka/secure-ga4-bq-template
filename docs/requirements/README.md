---
id: requirements-index
title: Requirements — Index
updated: 2026-07-15
---

# Requirements

Normative requirement and design documents for this asset. These are the source of truth
for **what** to build; `.ai/` stays the source of truth for **how** to work.

| Doc | Content | Status |
|-----|---------|--------|
| [requirements-secure-asset.md](requirements-secure-asset.md) | Main requirements: 2 modes (build / inspect), 3 controls, GA4 sensitive-column catalog (FR-1.1), nested-column unnest design (FR-1.3), 11 deterministic security checkpoints (FR-4), additive mart-description governance (FR-9 / CHK-12), asset-integration plan (§7.2) | v1.0 + CHK-12 |
| [requirements-dbt-dataform-rail.md](requirements-dbt-dataform-rail.md) | Mart-build rail: dbt/Dataform engine selection via profile-copy, shared governance layer, CI dry-run cost gate | v1.0 |
| [requirements-service-packaging.md](requirements-service-packaging.md) | Service packaging: evidenced common core, inspection-menu limits and qualification, 3 standard presets, conditional options, pricing rationale, and proposal-draft AI | v1.2 draft |
| [design-modules-wif-wiring.md](design-modules-wif-wiring.md) | Implementation design: interfaces of the 5 new Terraform modules, WIF wiring (deployer SA / inspector SA), new CI workflows | baseline implemented v1; cost-gate extension in ADR-0006 |
| [design-inspection-engine.md](design-inspection-engine.md) | Implementation design: FR-4 and FR-9 inspection engine — module layout, snapshot model, deterministic rules for CHK-01..CHK-12, engagement params, CLI/report contract, delivery slices (ADR-0003) | **implemented through CHK-12** |
| [design-ai-report-generator.md](design-ai-report-generator.md) | A-level AI narrative report design: deterministic input frame, security boundary, CLI/output contract, and delivery slices (ADR-0004) | implemented-live-v1 |

## Reading notes

- **Language**: the docs are Japanese, imported verbatim from the author's working
  drafts (2026-07-10). This deviates from ADR-0002 (AI-facing docs in English)
  deliberately: they are user-authored requirement *sources*, and translation would risk
  meaning drift. English summaries will be added as implementation proceeds (LOG-0008).
- **External references**: the docs cite personal-goal and interview-preparation
  documents (`参照_*`, `面談準備_*`, `面談台本_*`). Those are intentionally **not** in
  this repo — they are HR artifacts, not requirements. The links were flattened to plain
  text marked リポジトリ外.
- **Disclosure boundary**: this repository and its reviewed requirement sources are
  public, including the pricing ranges and organization context they contain. Complete
  inspection artifacts remain Internal under SEC-011 and must not be committed; see the
  root README [Visibility](../../README.md#visibility) section.
- **Design principle carried throughout**: deterministic guards decide (inspection
  checkpoints, cost gates, preset detection); AI only writes text within the frame the
  deterministic result provides. Do not invert this when implementing.
