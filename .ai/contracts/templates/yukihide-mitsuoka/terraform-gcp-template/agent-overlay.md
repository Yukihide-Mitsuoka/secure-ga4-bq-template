---
id: terraform-gcp-template-family-agent-overlay
title: Terraform GCP Template Family Agent Overlay
authority: 3
read_when: [agent-entry]
---

# Terraform GCP Template Family Agent Overlay

This owner-qualified template layer contains Terraform family rules intentionally
exported to direct descendants. Repository identity remains in each repository's
protected project overlay.

- Stack: Terraform on Google Cloud, with environment roots under `infra/envs/` unless a
  descendant documents a protected project-specific specialization.
- Modules: consume reusable modules from reviewed sources at immutable release tags;
  module implementation stays in the module repository.
- Required check: `iac-scan` remains an additive, always-reported governance check for
  repositories that inherit the Terraform family profile.
- Verification: use the repository's canonical `make` targets for Terraform formatting,
  validation, tests, and build checks.
- Execution boundary: repository files describe desired state. Terraform plan or apply,
  GitHub governance changes, and Google Cloud resource changes are separate authenticated
  operations and require their own authorization.
- Ownership: descendants must not use the exporting repository's protected project
  overlay as their project identity or local exception layer.
