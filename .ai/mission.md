---
id: mission
title: Mission
authority: 4
read_when: [onboarding, planning, architecture]
---

# Mission

## What this project is

secure-ga4-bq-template — a reusable template that builds (Terraform + CI/CD) and
inspects (read-only deterministic checks) GA4→BigQuery **mart layers** with three
security controls baked in: column-level security via policy tags, least-privilege IAM,
and cost-optimized audit logging. Normative requirements live in
[docs/requirements/](../docs/requirements/README.md).

| Field | Value |
|-------|-------|
| Problem being solved | Conventional GA4→BQ builds (export → query → mart → viz) ship with zero security controls; retrofitting them is manual, unrepeatable, and usually skipped |
| Primary users | AI-agent-driven engagements delivering GA4→BQ marts for mid-size data-active companies with thin security staffing; each engagement instantiates this template |
| Core value | Add the three controls at effort parity with a non-secure build (build mode), and audit existing environments with deterministic checks plus AI-drafted remediation (inspect mode) |
| Explicitly out of scope | Row-level security; Cloud-DLP-based protection; viz-tool (Looker etc.) access control; collection-time (client-side) PII prevention |

## Success criteria

<!-- Measurable. AI uses these to judge whether a proposed change moves the project forward. -->

1. Build mode: a verification environment reproduces a clean build with all three
   controls, and column-level access control demonstrably blocks a non-privileged
   reader on pseudo-sensitive columns (requirements §8, acceptance B).
2. Inspect mode: the inspector detects ≥10 of the 11 deterministic checkpoints (FR-4)
   read-only, under a least-privilege custom role (FR-6), at INFORMATION_SCHEMA-level
   scan cost.

## Role of AI agents in this project

AI agents are long-term team members, not code generators. Expectations:

- **Own the full task lifecycle**: requirements clarification → design → implementation →
  tests → documentation → PR. A task is not done when code compiles; it is done when the
  Definition of Done in `workflow.md` (WF-090) is met.
- **Preserve intent**: when code and documentation disagree, investigate which is correct
  before changing either. Record the resolution.
- **Prefer reversible steps**: small PRs, feature flags, additive migrations.
- **Escalate, don't guess**: for the escalation triggers listed in `CLAUDE.md` §13, stop
  and ask the human. For everything else, decide and record the reasoning.

## Human role

Humans own: product direction, priority calls, ADR approval, release approval,
security-sensitive decisions. AI prepares options and recommendations; humans decide.
