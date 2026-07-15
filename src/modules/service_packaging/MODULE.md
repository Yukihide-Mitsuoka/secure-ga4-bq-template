---
id: module-service-packaging
title: Service Packaging Module
updated: 2026-07-15
---

# Service Packaging Module

Purpose: own versioned service-menu profiles and the deterministic product rules that
turn those profiles into customer material and engagement qualification. This context is
local-only and remains separate from technical inspection and report generation under
[ADR-0007](../../../docs/adr/0007-generate-service-packages-from-versioned-profiles.md).

## Public API

| Entry point | Layer | Description |
|-------------|-------|-------------|
| `MenuProfile`, `FeeRange`, `CapacityLimits`, `LabeledItem` | domain | Immutable service-menu vocabulary and validation |
| `RenderInspectionMenu.handle(profile_path, out_dir)` | application | Coordinate profile loading and deterministic material generation |
| `YamlMenuProfileRepository.load(path)` | infrastructure | Load and validate a schema-v1 product profile |
| `MarkdownMenuWriter.write(profile, out_dir)` | infrastructure | Atomically render a customer-facing menu without overwriting existing output |
| `render_menu_cli.main(argv)` | interface | Local CLI used by `make render-inspection-menu` |

## Events

None; this is a local batch tool.

## Owned data

The context owns reviewed product-definition profiles under `service-packages/`. Profiles
contain no credentials, customer identifiers, row values, or environment branches.
Generated `inspection-menu.md` files are local artifacts under the selected output
directory and are not committed product definitions.

## Invariants

1. Profiles are immutable after loading and fail closed on invalid or incomplete input.
2. Profile values, not Python constants, define fees, limits, checks, deliverables, review
   sessions, and separate-estimate conditions.
3. The context imports no inspection or reporting internals and calls no GCP or AI API.
4. The default profile contains only the standard capabilities approved in Issues #76
   and #79; conditional masking and PII value detection are not standard deliverables.
5. Rendering is deterministic, escapes profile text, publishes atomically, and never
   overwrites an existing menu.

## Dependencies

| Uses | Via | Why |
|------|-----|-----|
| PyYAML | infrastructure adapter | Parse the existing repository YAML format |
