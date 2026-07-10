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

## This template's dev env

`envs/dev/` is the acceptance-criteria-B verification environment: three layer datasets
(`staging` / `intermediate` / `marts`) plus the sensitivity taxonomy, wired to
`bigquery-dataset` and `bigquery-policy-tags` at `?ref=v0.3.0`. Engagement parameters
(FR-7) enter via `layer_iam_members` and `fine_grained_readers`; the raw `analytics_*`
export dataset is Google-created and locked down out of band (requirements §3.3).

Update triggers: new env → new `envs/<env>/`; new module reference → bump/pin note in the
PR; backend change → `versions.tf` + `docs/deployment/`.
