# ADR-0008: Adopt the direct-parent inheritance contract

| Field | Value |
|-------|-------|
| Status | proposed |
| Date | 2026-07-16 |
| Deciders | repository owner |
| Author | Codex (AI agent) |
| Supersedes / Superseded by | Formalizes LOG-0008; proposes superseding local LOG-0004 |

## Context

LOG-0008 already defines `terraform-gcp-template` as this repository's direct parent,
and `.github/workflows/template-sync.yml` points to that repository. The current
transport is still a target-owned `.templatesyncignore` denylist with no accepted parent
commit, inherited allowlist, ownership validation, or deterministic one-commit plan.
It therefore cannot prove which parent state produced a file or prevent a newly added
parent path from overwriting secure-GA4 product files.

The original child tree provides exact provenance: initial child commit `1e37f2e` and
`terraform-gcp-template` commit `157b3c2` share root tree
`d51cb39d50b495a54de382e2ad6c2659e1f5a4e5`. The reviewed parent target after
Terraform PR #30 is `e2b42fcb21e02d9a158f56061635333a30235b53`. Treating that target
as an immediate bootstrap lock would skip the intervening review history.

The parent now supplies a manifest validator, one-first-parent planner, layered GitHub
governance resolver, and `terraform-gcp` profile. That profile adds the always-reported
`iac-scan` context. This child still exposes a path-filtered job named `scan`, while its
workflows intentionally use digest-pinned `actions/checkout` v7 and include
product-specific CI, BigQuery inspection, and cost-gate behavior that the parent does
not own.

Constraints are: preserve all secure-GA4 code, requirements, evidence, workflows, IAM,
and release behavior; keep every intermediate `main` green; retain solo-friendly
zero-approval defaults; add no repository-administration credential; make no live GitHub or
GCP change during migration; keep each PR within GR-020; and leave the sibling
`nextjs-saas-template` unchanged.

## Options considered

### Option 1: Do nothing

Keep the denylist-only scheduled sync. This has no migration cost, but ownership and
accepted provenance remain unprovable, scheduled workflow updates can still fail, and
the Terraform governance profile cannot be inherited safely. Rejected.

### Option 2: Bypass the Terraform parent

Point this repository directly at `ai-dev-foundation`. This shortens the chain but
violates the accepted direct-parent topology, drops Terraform-family policy, and makes
Terraform workflow adaptation a leaf-only responsibility. Rejected.

### Option 3: Replace files from the latest parent snapshot

Copy selected files from parent target `e2b42fc` in one reviewed PR. This is reversible
through Git but skips the provenance between `157b3c2` and the target, risks exceeding
GR-020, and can regress child-specific workflow hardening. Rejected.

### Option 4: Adopt manifest-driven direct-parent inheritance

Bootstrap at the exact matching parent commit, declare inherited and protected paths,
then advance one first-parent commit per reviewed PR. Adapt protected child workflows
before selecting the inherited Terraform profile. This requires more PRs and maintainer
time, but it is fail-closed, reviewable, and consistent with the parent architecture.

| Option | Simplicity | Blast radius and reversibility | Operational cost and security |
|--------|------------|--------------------------------|-------------------------------|
| Do nothing | Lowest initial effort | Drift remains hard to bound or undo confidently | Red sync and ownership ambiguity continue; no new credential |
| Bypass Terraform | Shorter graph | Breaks the accepted family boundary; normal PR rollback | Drops Terraform policy and duplicates adaptation work |
| Latest snapshot | One migration PR | Largest diff; Git rollback is possible but skipped provenance is not recovered | No new credential, but high review and regression risk |
| Manifest direct parent | More small PRs | One parent commit per reversible PR; unknown paths fail closed | Highest maintainer time; least privilege and no new vendor or credential |

## Decision

Adopt Option 4 and the contracts in
[ai-dev-foundation ADR-0004](https://github.com/Yukihide-Mitsuoka/ai-dev-foundation/blob/main/docs/adr/0004-harden-multi-level-template-inheritance.md)
and
[terraform-gcp-template ADR-0003](https://github.com/Yukihide-Mitsuoka/terraform-gcp-template/blob/main/docs/adr/0003-adopt-direct-parent-template-inheritance.md).
This repository MUST name
`Yukihide-Mitsuoka/terraform-gcp-template` as its only direct parent and MUST bootstrap
its lock at parent commit `157b3c2e299722f35957c15e915139aa64730fe1`, whose complete tree
matches the original child tree. Parent target `e2b42fc` is reached only through the
planner's first-parent sequence; a later target is never accepted by skipping commits.

Every path MUST have one owner. The child manifest, lock, repository governance policy,
`.gitignore`, `.templatesyncignore`, product code, requirements, evidence, Python and
Terraform configuration, product workflows, and stack-specific scripts are protected.
Only byte-and-mode-equivalent parent paths begin as inherited. Unknown paths remain
unowned and uncopied until a reviewed ownership change. Candidate deletion remains
disabled and requires separate GR-031 approval.

The current child `iac.yml` remains protected until it preserves digest-pinned checkout
v7 while exposing a unique `iac-scan` result on every pull request and `main` push. The
`terraform-gcp` profile MUST NOT be selected or enforced before both PR and merged-main
evidence show that exact context. The inherited foundation and Terraform checks are
monotonic; a protected leaf `repository.json` may add child-specific checks but cannot
remove them.

Migration follows expand → migrate → contract:

1. add the manifest, lock, offline validator, and read-only planner without removing
   legacy sync;
2. advance one reviewed parent commit at a time, adapting protected child files instead
   of overwriting them;
3. make child `iac-scan` always report, then inherit the Terraform profile and add the
   protected leaf governance policy;
4. record a GET-only governance plan; and
5. remove or demote legacy write-capable sync only after equivalent read-only drift
   visibility exists.

No governance `apply`, repository-setting mutation, Terraform `apply`, GCP resource,
or sibling-repository change is authorized by this ADR.

## Consequences

**Positive:** Parent provenance and ownership become deterministic; secure-GA4 assets
remain leaf-owned; Terraform policy flows through the correct parent; required checks
cannot silently lose foundation controls; and workflow updates need no CI administrator
credential.

**Negative:** The verified history from `157b3c2` to the current parent requires multiple
small PRs. Protected workflow adaptations need explicit review, and legacy sync remains
temporarily present as a non-authoritative second mechanism.

Every intermediate commit remains releasable. Rollback is a reviewed PR restoring the
previous lock or removing an unconsumed expand-stage component. Existing GitHub settings
and cloud state remain unchanged because migration planning is read-only.

**Follow-ups:** Continue Issue #104 only after the repository owner accepts this ADR.
Bootstrap the contract first; do not combine ADR approval with inherited-file migration.
