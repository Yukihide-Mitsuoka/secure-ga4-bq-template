---
id: template-inheritance-validation
title: Template Inheritance Validation
---

# Template inheritance validation

This repository adopts the direct-parent inheritance contract defined by
[ADR-0008](../adr/0008-adopt-direct-parent-inheritance-contract.md).

Validate the child-owned manifest and lock without network or GitHub access:

```bash
python3 scripts/template_inheritance.py validate --root .
```

A successful command exits with status 0 and prints normalized JSON. Invalid schema, unsafe paths,
ownership overlap, missing mandatory protected paths, symlinks, repository mismatch, and invalid commit IDs fail closed with status 2.

The validator performs no Git operation, network request, file write, deletion, GitHub API call, Terraform command, or GCP operation.
It is derived from direct-parent commit `0a7f7eef8cbd269d310d46bebef9cc2c745fe414`; importing it does not advance the lock.
