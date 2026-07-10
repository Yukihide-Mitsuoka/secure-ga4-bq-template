---
id: infra
title: Terraform layout
---

# infra/ — Terraform root configurations

| Path | Role |
|------|------|
| `envs/<env>/` | One root config per environment (start: `dev`). State and providers live here |

Rules:

- **Modules are referenced, never vendored.** Building blocks come from
  [terraform-gcp-modules](https://github.com/Yukihide-Mitsuoka/terraform-gcp-modules)
  pinned by tag: `source = "git::https://github.com/Yukihide-Mitsuoka/terraform-gcp-modules.git//modules/<name>?ref=vX.Y.Z"`.
  Upgrading = bumping `?ref=` in a reviewed PR. Do not copy module code into this repo;
  a module worth writing is worth contributing to the library.
- Truly project-specific glue (a one-off resource, a local wrapper) may live beside the
  env's `main.tf`; if it grows reusable, promote it to the library (rule of three, COD-020).
- `make build` validates every env without credentials; `make plan ENV=dev` needs
  credentials and a configured backend (`versions.tf`).

Update triggers: new env → new `envs/<env>/`; new module reference → bump/pin note in the
PR; backend change → `versions.tf` + `docs/deployment/`.
