---
id: requirements-index
title: Requirements — Index
updated: 2026-07-11
---

# Requirements

Normative requirement and design documents for this asset. These are the source of truth
for **what** to build; `.ai/` stays the source of truth for **how** to work.

| Doc | Content | Status |
|-----|---------|--------|
| [requirements-secure-asset.md](requirements-secure-asset.md) | Main requirements: 2 modes (build / inspect), 3 controls, GA4 sensitive-column catalog (FR-1.1), nested-column unnest design (FR-1.3), 11 deterministic inspection checkpoints (FR-4), asset-integration plan (§7.2) | v1.0 |
| [requirements-dbt-dataform-rail.md](requirements-dbt-dataform-rail.md) | Mart-build rail: dbt/Dataform engine selection via profile-copy, shared governance layer, CI dry-run cost gate | v1.0 |
| [requirements-service-packaging.md](requirements-service-packaging.md) | Service packaging: common core + customization axes + 3 presets, pricing rationale, proposal-draft AI (deterministic preset detection → LLM fills text) | v1.0 draft |
| [design-modules-wif-wiring.md](design-modules-wif-wiring.md) | Implementation design: interfaces of the 5 new Terraform modules, WIF wiring (deployer SA / inspector SA), new CI workflows | draft v0.1 |

## Reading notes

- **Language**: the docs are Japanese, imported verbatim from the author's working
  drafts (2026-07-10). This deviates from ADR-0002 (AI-facing docs in English)
  deliberately: they are user-authored requirement *sources*, and translation would risk
  meaning drift. English summaries will be added as implementation proceeds (LOG-0008).
- **External references**: the docs cite personal-goal and interview-preparation
  documents (`参照_*`, `面談準備_*`, `面談台本_*`). Those are intentionally **not** in
  this repo — they are HR artifacts, not requirements. The links were flattened to plain
  text marked リポジトリ外.
- **Confidentiality**: pricing figures and internal organization names appear in
  requirements-service-packaging.md and requirements-secure-asset.md §2. This is why the
  repo is private (see root README "Visibility").
- **Design principle carried throughout**: deterministic guards decide (inspection
  checkpoints, cost gates, preset detection); AI only writes text within the frame the
  deterministic result provides. Do not invert this when implementing.
