---
id: template-inheritance-validation
title: Template Inheritance Validation and Planning
---

# Template inheritance validation and planning

This repository adopts the direct-parent inheritance contract defined by
[ADR-0008](../adr/0008-adopt-direct-parent-inheritance-contract.md).

Validate the child-owned manifest and lock without network or GitHub access:

```bash
python3 scripts/template_inheritance.py validate --root .
```

A successful command exits with status 0 and prints normalized JSON. Invalid schema, unsafe paths,
ownership overlap, missing mandatory protected paths, symlinks, repository mismatch, and invalid commit IDs fail closed with status 2.

Plan the next direct-parent commit from an existing local parent checkout:

```bash
python3 scripts/template_inheritance.py plan \
  --root . \
  --parent-root ../terraform-gcp-template
```

The parent must be a Git worktree whose credential-free GitHub `origin` matches the
manifest. Planning reads the existing `origin/main` ref without fetching and requires
the locked commit to be on its first-parent history. It reports at most the immediate
next commit, even when the local remote ref is further ahead.

Changed paths are classified as:

- `add`, `modify`, `candidate_delete`, or `already_current` for inherited paths;
- `protected` or `unowned` under `skipped` for paths the planner must not import.

Unsafe paths, non-regular files, child symlinks, parent identity mismatch, missing
history, oversized history, and commits changing more than 1,000 paths fail closed.

The validator performs no Git operation. The planner performs only bounded local Git
reads: no network request, fetch, checkout, file write, materialization, deletion,
GitHub API call, Terraform command, or GCP operation. It is derived from direct-parent
commit `0736ac460edf951395baf38e627fb9f55049674c`; planning does not advance the lock.
