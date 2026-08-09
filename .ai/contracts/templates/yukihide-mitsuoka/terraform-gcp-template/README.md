---
id: terraform-gcp-template-child-contract
title: Terraform GCP Template Child Contract
updated: 2026-08-08
---

# Terraform Family Child Contract

`inheritance-export.json` is the machine-readable ownership and agent-input contract for
new direct children of `Yukihide-Mitsuoka/terraform-gcp-template`. The Foundation
`bootstrap-child` command reads this file from the exact parent source commit.

The export passes the Foundation contract and this Terraform family overlay to a child.
It also passes the Terraform governance profile and canonical Terraform Make profile.
Repository identity, project overlays, workflow callers, root README, project
documentation, Terraform configuration, source, and tests remain protected child-owned
paths.

Change the export only through a reviewed contract PR. Validate it with the repository
governance tests and `make doctor`. Creating or enabling a remote repository, applying
GitHub governance, and running Terraform remain separate authenticated operations.
