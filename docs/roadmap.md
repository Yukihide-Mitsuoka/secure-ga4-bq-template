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

- Apply the asset to a second engagement or department standard when an owner and scope
  exist, then measure reuse effort for Acceptance S. No cloud environment should be
  created before that scope and its approvals exist.

## Next (1-2 milestones out)

- Record customer-safe engagement evidence and compare actual reuse effort against the
  baseline.
- Revisit conditional service options only after engagement evidence establishes demand
  and an approved data-access boundary.

## Completed on 2026-07-15

- Technical Acceptance A was approved with the public-sample, interactive-ADC, and
  uninvoked-inspector-WIF limitations recorded in the
  [dated evidence](verification/2026-07-15-public-ga4-acceptance-a-evidence.md).
- Source-agnostic CHK-12 mart-description governance was specified and implemented
  through [Issue #70](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/issues/70)
  without changing the historical Acceptance B denominator.
- The approved standard-inspection packaging baseline was delivered as a versioned
  profile, deterministic menu renderer, scope evaluator, and rollback-safe JSON/Markdown
  qualification artifact pair through [PR #90](https://github.com/Yukihide-Mitsuoka/secure-ga4-bq-template/pull/90).

## Later (intended, not committed)

- Add A+ GA4 PII value detection only after its data-access and cost boundary is approved.
- Add scheduled Cloud Run reconciliation only after a continuing owner and SLO exist.

## Explicitly not planned

- Automatically applying remediation or opening remediation PRs; ADR-0005 requires a
  deterministic, non-applying draft and human review.
- Reusing deployer or inspector credentials for the cost gate; ADR-0006 requires a
  dedicated provider and least-privilege service account.
- Generalizing the shared OIDC module before a second consumer proves the pattern.
