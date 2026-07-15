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
| `EngagementScope`, `ScopeCounts`, `QualificationResult`, `QualificationReason` | domain | Immutable preflight input and complete qualification result |
| `evaluate_scope(profile, scope)` | domain | Decide standard-package eligibility and every separate-estimate reason |
| `RenderInspectionMenu.handle(profile_path, out_dir)` | application | Coordinate profile loading and deterministic material generation |
| `QualifyEngagement.handle(profile_path, scope_path, out_dir)` | application | Load, evaluate, and publish one qualification artifact pair |
| `YamlMenuProfileRepository.load(path)` | infrastructure | Load and validate a schema-v1 product profile |
| `YamlEngagementScopeRepository.load(path)` | infrastructure | Load and strictly validate a schema-v1 anonymous scope input |
| `MarkdownMenuWriter.write(profile, out_dir)` | infrastructure | Atomically render a customer-facing menu without overwriting existing output |
| `QualificationArtifactWriter.write(result, out_dir)` | infrastructure | Publish deterministic JSON/Markdown as a rollback-safe pair |
| `render_menu_cli.main(argv)` | interface | Local CLI used by `make render-inspection-menu` |
| `qualify_cli.main(argv)` | interface | Local CLI used by `make qualify-inspection-scope` |

## Events

None; this is a local batch tool.

## Owned data

The context owns reviewed product-definition profiles under `service-packages/`. Profiles
contain no credentials, customer identifiers, row values, or environment branches.
Generated `inspection-menu.md` files are local artifacts under the selected output
directory and are not committed product definitions.
Generated `qualification.json` and `qualification.md` form one artifact pair in that
output directory and are never partially retained after a publication failure.
Engagement-scope inputs are supplied preflight facts; they contain counts and work flags,
not customer names, project IDs, credentials, or row values.

## Invariants

1. Profiles are immutable after loading and fail closed on invalid or incomplete input.
2. Profile values, not Python constants, define fees, limits, checks, deliverables, review
   sessions, and separate-estimate conditions.
3. The context imports no inspection or reporting internals and calls no GCP or AI API.
4. The default profile contains only the standard capabilities approved in Issues #76
   and #79; conditional masking and PII value detection are not standard deliverables.
5. Rendering is deterministic, escapes profile text, publishes atomically, and never
   overwrites an existing menu.
6. Schema-v1 qualification returns every triggered profile-defined reason in profile
   order; exact capacity limits remain eligible.
7. Qualification artifacts are byte-deterministic, fail closed on either existing target,
   and contain no inferred customer identifiers or final-price calculation.

## Dependencies

| Uses | Via | Why |
|------|-----|-----|
| PyYAML | infrastructure adapter | Parse the existing repository YAML format |
