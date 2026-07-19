# ADR-0010: Separate foundation and project document ownership

| Field | Value |
|-------|-------|
| Status | proposed |
| Date | 2026-07-19 |
| Deciders | repository owner |
| Author | Codex (AI agent) |
| Supersedes / Superseded by | Supersedes ADR-0002 for project-specific documents; extends ADR-0008 |

## Context

ADR-0008 protects the entire `docs/` tree while this repository catches up to its
direct Terraform parent. That prevented unsafe overwrites, but it also prevents the new
foundation documentation namespace from propagating. Accepted parent checkpoint
`ee9e61c` now instructs agents to read templates under `docs/foundation/` and to write
project documents in Japanese, while later parent checkpoints materialize those
foundation files.

The current tree predates that convention. Foundation-authored README files, templates,
onboarding guides, and early ADR copies share root `docs/` directories with Secure GA4
requirements, architecture, verification evidence, runbooks, and adapted governance
guides. Keeping the whole tree leaf-owned causes inherited guidance to drift. Making the
whole tree parent-owned would let template sync overwrite product evidence and local
decisions. Moving project documents into a deeper generic namespace would also make the
leaf's primary artifacts less direct than reusable foundation material.

The migration must keep every intermediate link valid, preserve all product documents
and local ADR history, stay within review-size limits, and perform no live GitHub, GCP,
or Terraform operation.

## Options considered

### Option 1: Keep all of `docs/` protected

This has no migration cost and preserves local files, but blocks the accepted parent
namespace and leaves agents reading stale foundation copies. Rejected.

### Option 2: Inherit all of `docs/`

This is simple and maximizes propagation, but gives the parent ownership of local
requirements, evidence, architecture, and ADRs. Rejected.

### Option 3: Put project documents under `docs/project/`

This separates ownership, but places the repository's primary human-authored artifacts
below reusable material and requires needless path churn. Rejected.

### Option 4: Inherit only `docs/foundation/`

Reserve `docs/foundation/` for direct-parent material and keep project documents at
`docs/` or explicit project-owned subdirectories. Remove only confirmed duplicate
foundation copies after their namespaced replacements are present. This requires an
explicit protected-path list but gives each path one clear owner.

## Decision

Adopt Option 4. The inheritance manifest MUST add `docs/foundation/` to
`inherited_paths` and MUST replace the broad protected root `docs/` with explicit local
files and subdirectories. At minimum, Secure GA4 requirements, ADRs, architecture,
API/report contracts, deployment configuration, runbooks, troubleshooting adaptations,
verification evidence, glossary, roadmap, usage guides, and handoff documents remain
leaf-owned. A new project-document location is unowned until reviewed into the manifest;
ownership overlap remains invalid.

Foundation-owned guidance and templates under `docs/foundation/` remain in their source
language and MUST be byte-and-mode equivalent to the accepted direct parent. AI agents
MUST write new or materially rewritten project-specific documents in Japanese unless
the repository owner or an external contract explicitly requires another language.
This project rule supersedes ADR-0002's English requirement; it does not require a
same-facts translated sibling.

Migration follows expand, verify, then contract:

1. materialize the accepted AI documentation and requirements-skill rules plus the
   inheritance contract README;
2. add `docs/foundation/` ownership and materialize its files one parent checkpoint at
   a time;
3. verify every local product document and link remains reachable; and
4. remove only root files proven to be obsolete foundation duplicates in a reviewed PR.

No local product document is moved or deleted merely because its name resembles a
foundation file. Candidate deletions remain separately reviewed, and no live system
mutation is authorized.

## Consequences

**Positive:** Foundation guidance propagates without competing with leaf artifacts;
project documents stay prominent; AI language instructions are explicit; and ownership
remains fail-closed and auditable.

**Negative:** The manifest must enumerate local documentation roots. Mixed historical
directories require a careful file-by-file cleanup, and existing English project
documents are not automatically translated until they are materially rewritten.

Rollback is a reviewed PR restoring the prior manifest entry and duplicate files from
Git history. It does not affect live GitHub or cloud state.

**Follow-ups:**

1. Adapt parent checkpoint `ee9e61c` without broken intermediate references.
2. Advance and materialize each later `docs/foundation/` checkpoint separately.
3. Add regression tests for disjoint ownership, required foundation paths, and absence
   of confirmed legacy duplicates.
