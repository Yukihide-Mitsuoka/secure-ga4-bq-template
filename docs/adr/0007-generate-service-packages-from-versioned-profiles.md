# ADR-0007: Generate service packages from versioned profiles

| Field | Value |
|-------|-------|
| Status | proposed |
| Date | 2026-07-15 |
| Deciders | repository owner |
| Author | Codex (AI agent) |
| Supersedes / Superseded by | — |

## Context

The inspection service has an approved fixed-price default boundary: one GCP project,
up to 10 non-excluded datasets, 200 table resources, and 2,000 flattened leaf columns;
CHK-01 through CHK-12; one report/remediation package; and one review session. Exceeded
limits, multiple projects, customer WIF setup, query jobs, and row-value inspection
require a separate estimate.

The service menu must remain easy to revise. Maintaining the limits independently in
requirements, customer material, and qualification logic would allow them to drift. A
reviewed parameter change must therefore update both the presented menu and the
standard-package eligibility decision without a Python change.

The design must preserve these constraints:

1. Inspection remains the sole owner of metadata collection and deterministic findings.
2. Reporting remains the sole owner of AI narrative and remediation-draft generation.
3. Menu rendering and qualification are deterministic, local, and independent of GCP,
   credentials, query jobs, row values, and AI providers.
4. The approved default fee range and limits remain unchanged.
5. Existing PyYAML is sufficient; no dependency is needed.
6. Menu profiles are reviewed product-definition data, not deployment or
   environment-specific runtime configuration governed by ARC-010.

## Options considered

### Option 1: Keep the menu in documentation only

Humans edit requirements and customer material, then qualify engagements manually.

- Pros: no new code or public contract; lowest immediate implementation cost.
- Cons: duplicates commercial limits across documents; cannot prove that a proposal
  matches the approved profile; makes boundary decisions reviewer-dependent; does not
  meet the requirement for parameter-only menu changes.

### Option 2: Add menu configuration and qualification to `inspection`

The inspection CLI reads commercial limits and emits service eligibility with findings.

- Pros: collected coverage is already available; one execution can produce all outputs.
- Cons: mixes product packaging and price presentation into the technical assessment
  boundary; a sales-menu change would alter the inspection contract; qualification could
  become coupled to GCP access even when only a preflight estimate is needed; rollback
  would risk the accepted ADR-0003 path.

### Option 3: Add a separate `service_packaging` bounded context — chosen

A versioned YAML profile is the source for fee range, limits, included check IDs,
deliverables, review sessions, and separate-estimate conditions. A local module validates
the profile and a separately supplied engagement-scope file. Two deterministic use cases
render customer-facing menu Markdown and qualify the engagement into JSON and Markdown.

- Pros: profile values change without Python edits; presentation and qualification share
  one source; no cloud or provider boundary is added; inspection and reporting contracts
  remain unchanged; the module and generated artifacts can be removed independently.
- Cons: adds a third bounded context and two input schemas; supplied preflight counts can
  be wrong; configured check IDs can drift from the inspection registry unless a contract
  test reconciles the default profile.

### Option 4: Add standalone generators under `scripts/`

One or more scripts parse YAML and write the material without a module contract.

- Pros: fewer files than a bounded context; no cross-module calls.
- Cons: validation, business rules, and file I/O would be interleaved; error and boundary
  tests would have no stable domain seam; the service menu is a core product rule rather
  than repository automation, so `scripts/` would conflict with ARC-001.

## Decision

Adopt Option 3. A new `src/modules/service_packaging/` bounded context MUST own service
menu profiles and deterministic qualification. It MUST NOT import inspection or reporting
internals, call GCP or AI providers, calculate a final sales price, or apply remediation.
Versioned profile files are product-definition data and MUST NOT contain credentials,
customer identifiers, or environment-specific branches.

The module MUST expose two local CLI use cases through canonical Make targets:

1. render customer-facing Markdown from one versioned menu profile; and
2. evaluate one engagement-scope input against that profile and write deterministic JSON
   and Markdown containing eligibility plus every separate-estimate reason.

The default profile MUST retain the approved Issue #79 values. Dataset, table-resource,
and leaf-column counts MUST use the inspection coverage semantics documented by
`Report.coverage`. A contract test MUST reconcile the default profile's CHK-01..CHK-12
list with the implemented inspection registry without introducing a production import
between contexts. Existing output files MUST fail closed rather than be overwritten.

## Consequences

**Positive:**

- One reviewed profile change updates customer material and qualification behavior.
- Qualification can happen before cloud access is provisioned and produces auditable
  reasons instead of an unstructured sales judgment.
- The accepted inspection and reporting paths remain unchanged and independently usable.
- The implementation uses the existing Python toolchain and PyYAML dependency.

**Negative:**

- A third module, profile schema, engagement-scope schema, and generated-artifact contract
  require maintenance.
- Qualification is only as accurate as the supplied preflight counts and condition flags.
- Check capability is duplicated as configuration data; the default-profile contract test
  detects drift, but custom profiles remain a reviewed product decision.
- Parameter values are flexible, but adding a new parameter type still requires a schema
  and code change.

**Migration and rollback:**

- The change is additive. Existing inspection and reporting commands continue unchanged.
- Remove the new Make targets, module, profile files, and generated artifacts to roll back;
  no cloud resources or persisted data require migration.
- Profile schema versions are immutable after release. A breaking shape change introduces
  a new version and explicit reader support.

**Follow-ups:**

- After owner approval, implement Issue #79 in a feature PR with the default profile,
  example engagement scope, domain evaluator, YAML adapters, atomic writers, CLIs, tests,
  requirements, usage documentation, glossary, module map, and module contract.
- Keep generated customer material out of the normative requirements; link it to the
  versioned profile that produced it.
