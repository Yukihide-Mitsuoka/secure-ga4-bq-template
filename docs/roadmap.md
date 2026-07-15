---
id: roadmap
title: Roadmap
updated: 2026-07-15
---

# Roadmap

Direction and sequencing. Agents use this to judge whether a proposed change aligns
with where the project is going (mission.md success criteria) — not as a work queue
(that's GitHub issues/milestones).

**Update triggers:** milestone completed, priorities re-ordered, scope added/dropped.
Keep `updated:` current; stale roadmaps mislead agents (DOC-040).

## Now (current milestone)

- Complete the approved public-GA4 technical Acceptance A record. The approval is
  constrained to the public sample, interactive ADC inspection, and an inspector WIF
  path that was not invoked; see
  [the dated evidence](verification/2026-07-15-public-ga4-acceptance-a-evidence.md).

## Next (1-2 milestones out)

- Implement the additive, source-agnostic CHK-12 mart-description check specified by
  Issue #70 and PR #71.
- Review and baseline the service-packaging draft: common core, customization axes,
  presets, and evidence expected from an engagement.
- Apply the asset to a second engagement and measure reuse effort for acceptance S.

## Later (intended, not committed)

- Add A+ GA4 PII value detection only after its data-access and cost boundary is approved.
- Add scheduled Cloud Run reconciliation only after a continuing owner and SLO exist.

## Explicitly not planned

- Automatically applying remediation or opening remediation PRs; ADR-0005 requires a
  deterministic, non-applying draft and human review.
- Reusing deployer or inspector credentials for the cost gate; ADR-0006 requires a
  dedicated provider and least-privilege service account.
- Generalizing the shared OIDC module before a second consumer proves the pattern.
