---
id: terraform-gcp-template-agent-overlay
title: Terraform GCP Template Agent Overlay
authority: 3
read_when: [agent-entry]
---

# Terraform GCP Template Agent Overlay

This protected project layer contains repository identity and stack facts only. The
explicit agent profile loads it after the inherited foundation contract.

- Repository: `Yukihide-Mitsuoka/terraform-gcp-template`.
- Role: reusable Terraform template for Google Cloud projects.
- Stack: Terraform on Google Cloud, with root configurations under `infra/envs/`.
- Modules: external modules come from `Yukihide-Mitsuoka/terraform-gcp-modules` at
  immutable release tags; their implementations remain in the module repository.
- Execution model: repository files describe desired configurations. Applying
  Terraform, changing GitHub governance, and creating Google Cloud resources are
  separate authenticated operations.
