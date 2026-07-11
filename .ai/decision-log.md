---
id: decision-log
title: Decision Log
authority: 4
read_when: [architecture-change, planning, onboarding]
---

# Decision Log

Append-only index of decisions. Newest first. Two kinds of entries:

- **ADR-linked**: architectural decisions — full context lives in `docs/adr/`.
- **Lightweight**: decisions too small for an ADR but worth remembering (COD-052).

Rules: never edit or delete past entries; supersede with a new entry that references the
old one. One line per entry. AI agents append entries in the same PR as the change.

| Date | ID | Decision | Link |
|------|----|----------|------|
| 2026-07-11 | LOG-0013 | Dataform engine ships as `profiles/dataform-bigquery/` mirroring the dbt profile (rail §2.3 mapping): policy tags via `bigqueryPolicyTags` with full resource names from Terraform vars; assertions on `requirePartitionFilter` tables are MANUAL with a partition window (built-in `nonNull` emits an unfiltered query BigQuery rejects) and land in the IAM-locked `staging` dataset; `dataform format` has no check-only mode, so `make lint` enforces rail naming (`stg_*`/`int_*`/`fct_*`/`dim_*`) and never formats | [profiles/dataform-bigquery/](../profiles/dataform-bigquery/README.md) |
| 2026-07-11 | LOG-0012 | WIF wiring (design §B) lands in `infra/envs/dev/wif.tf`: deployer SA via `github-oidc` module; inspector SA is a **plain resource** (settles design §D-2 — github-oidc makes exactly one SA; promote to the library on rule of three, COD-020), bound to the `bq-inspector-role` **library module** (`?ref=v0.4.0`, design §A-5 — landed in terraform-gcp-modules concurrently with this PR; superseded an earlier inline `google_project_iam_custom_role` draft once the module appeared). Deployer default roles = design B-1 candidate set minus projectIamAdmin (no project-level IAM managed here); refinement of D-1 waits for a real apply | [infra/envs/dev/wif.tf](../infra/envs/dev/wif.tf) |
| 2026-07-11 | LOG-0011 | Sensitivity catalog lives at `catalog/ga4-sensitivity.yml` as data, consumed by both modes (build: model YAML must agree; inspect: checkpoint #4). Engagement re-leveling goes ONLY in `overrides:` — defaults never change per engagement (FR-1.2). Catalog↔model consistency stays review-enforced until the inspector lands; no generator (rail: no meta-compiler) | [catalog/](../catalog/README.md) |
| 2026-07-11 | LOG-0010 | dbt engine ships as `profiles/dbt-bigquery/` (Makefile + skeleton; activation = copy, per the rail's profile-copy decision). Policy tags are declared ONLY on mart tables — BigQuery cannot tag view columns, so staging/intermediate views rely on dataset IAM (this is the "protect the mart" design, not a gap). Tests on `require_partition_filter` tables carry a partition-aware `where` window | [profiles/dbt-bigquery/](../profiles/dbt-bigquery/README.md) |
| 2026-07-11 | LOG-0009 | Verification env (`infra/envs/dev`) wires the minimum module set (3 layer datasets + taxonomy, `?ref=v0.3.0`). The taxonomy/dataset location-match constraint is enforced by construction: both modules receive the same `var.region` | [infra/envs/dev/main.tf](../infra/envs/dev/main.tf) |
| 2026-07-11 | LOG-0008 | Repo bootstrapped as the 4th-tier template (parent: terraform-gcp-template; sync repointed). Requirements imported verbatim into `docs/requirements/` as Japanese source docs (deliberate ADR-0002 deviation — they are user-authored requirement sources, not AI-facing rules; English summaries follow with implementation). Repo stays **private** until business figures (pricing, internal org names) are sanitized | [docs/requirements/](../docs/requirements/README.md) |
| 2026-07-03 | LOG-0007 | Markdown formatting MUST be frontmatter-aware: mdformat pinned via pre-commit with `mdformat-frontmatter` + `mdformat-gfm`, config in `.mdformat.toml` (`wrap=keep`, `number=true`). A naive run once collapsed all YAML frontmatter into headings — never use a formatter without these plugins | [.mdformat.toml](../.mdformat.toml) |
| 2026-07-02 | ADR-0002 | AI-facing docs are written in English | [ADR-0002](../docs/adr/0002-ai-facing-docs-in-english.md) |
| 2026-07-02 | ADR-0001 | Record architecture decisions as ADRs | [ADR-0001](../docs/adr/0001-record-architecture-decisions.md) |
| 2026-07-02 | LOG-0006 | `guard-bash.sh` must work when `jq` is absent (the `\|\| cat` fallback greps raw hook JSON); GR-010/011 patterns therefore treat `"` as a token terminator. Do not "simplify" that away. Verified by a matrix test on both paths | — |
| 2026-07-02 | LOG-0005 | AI PR review runs via `ai-review.yml`, disabled by default (repo var `ENABLE_AI_REVIEW`); supplements, never replaces, human review | — |
| 2026-07-02 | LOG-0004 | Template updates distribute via actions-template-sync PRs; downstream-customized files protected by `.templatesyncignore` | — |
| 2026-07-02 | LOG-0003 | GitHub governance (branch protection etc.) bootstrapped by `scripts/setup-github.sh` (gh CLI, idempotent) instead of a Probot app — no extra runtime dependency | — |
| 2026-07-02 | LOG-0002 | Canonical make targets are a binding contract (check-only lint, no `%:` catch-all, GR-031-guarded destructive targets); stack examples live in `profiles/` | [profiles/README.md](../profiles/README.md) |
| 2026-07-02 | LOG-0001 | Skills are vendor-neutral files in `.skills/`, routed via CLAUDE.md table instead of duplicated `.claude/skills/` wrappers | — |
