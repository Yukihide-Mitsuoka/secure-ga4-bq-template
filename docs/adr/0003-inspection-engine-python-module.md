# ADR-0003: Build the FR-4 inspection engine as a Python module using REST metadata only

| Field | Value |
|-------|-------|
| Status | accepted (2026-07-11, repository owner: "クエリは実行しない" confirmed) |
| Date | 2026-07-11 |
| Deciders | repository owner |
| Author | Claude (AI agent) |
| Supersedes / Superseded by | — |

## Context

Requirements FR-4/FR-5/FR-6 (requirements-secure-asset.md) demand an inspection engine:
collect BigQuery/IAM/Logging configuration from a customer project **read-only** (FR-6,
A-5 role), evaluate 11 deterministic checkpoints, and emit machine-readable findings
plus a summary (the frame for later AI-generated reports). The B acceptance bar is ≥10
checkpoints detected, deterministic and high-confidence only.

The repo today is a pure-IaC starter: the root Makefile wires only Terraform; the only
Python under `src/` is the template's example module. Three structural questions must
be answered before implementation (ARC-020: architectural):

1. Where does the engine live and in what shape?
2. What runtime/toolchain does the repo adopt for it?
3. How does it talk to Google APIs within the A-5 least-privilege envelope and the §6
   cost NFR (avoid scans)?

## Options considered

### Option 1: Do nothing / ad-hoc scripts in `scripts/`

Shell or single-file Python calling `gcloud`/`bq`, parsing JSON output.

- Pros: no new toolchain; fastest first demo.
- Cons: the 11 rules end up interleaved with I/O and CLI parsing — untestable without
  GCP, violating TST-010 determinism and the ≥80% domain coverage target; output
  parsing of CLI tools is version-fragile; contradicts ARC-001 (business logic belongs
  in a module). The engine is the asset's second core deliverable (§9.2, 8–12
  person-days) — not a script.

### Option 2: Python bounded context `src/modules/inspection/`, Google discovery client, REST metadata only — **chosen**

Clean Architecture module: pure-function checks in `domain/`, collection behind ports,
Google API access via `google-api-python-client` (+`google-auth`) adapters, `PyYAML`
for the catalog/params files. All 11 checkpoints are decided from REST **metadata**
(`datasets.get`, `tables.get` incl. per-field `policyTags`, `projects.getIamPolicy`,
`taxonomies.list`, `sinks/exclusions.list`) — no BigQuery query jobs.

- Pros: checks are pure and unit-testable without GCP; zero bytes billed (stronger than
  the "prefer INFORMATION_SCHEMA" NFR); collection needs strictly fewer permissions
  than A-5 grants (`bigquery.jobs.create` unused until the A+ value scan); one client
  library uniformly covers all four APIs (BQ, Resource Manager, Data Catalog, Logging)
  with pagination/retry handled; SDK isolated in `infrastructure/` (COD-041) so it is
  swappable.
- Cons: three new dependencies; repo stops being "pure IaC" — Makefile/CI must wire
  Python (uv/Ruff/mypy/pytest via the bundled python-uv profile); one `tables.get` per
  table (fine at ICP scale; an INFORMATION_SCHEMA adapter can be added behind the same
  port if an engagement has thousands of tables).

### Option 3: Same module shape, but per-API Google Cloud SDKs (`google-cloud-bigquery`, `-datacatalog`, `-logging`, `-resource-manager`)

- Pros: idiomatic typed clients.
- Cons: four heavyweight dependency trees (gRPC/protobuf) to get what are simple GET
  calls; larger supply-chain surface for a security tool delivered into customer
  engagements; COD-040 says prefer the smaller footprint.

### Option 4: Same module shape, hand-rolled REST (`google-auth` + stdlib urllib)

- Pros: minimal dependencies (google-auth + PyYAML only).
- Cons: hand-written pagination, retries, and error mapping across four APIs — the
  most defect-prone part of the engine rewritten from scratch; more code to test for
  no behavioral gain. Kept as fallback if the discovery client becomes a problem.

## Decision

Adopt Option 2. The engine MUST live in `src/modules/inspection/` following
ARC-001/002; checkpoint logic MUST be pure functions over an immutable snapshot
(deterministic, clock injected); all Google API access MUST go through
`infrastructure/` adapters implementing application ports; the B-path MUST NOT execute
BigQuery query jobs or any mutating API call (FR-6, GR-030). Dependencies added:
`google-api-python-client`, `google-auth`, `PyYAML` (pinned via uv lock, COD-040
justification in the PR). The root toolchain adopts the python-uv profile merged into
the existing Terraform Makefile, keeping the canonical target contract intact.
Detailed design: [design-inspection-engine.md](../requirements/design-inspection-engine.md).

## Consequences

**Positive:**

- FR-4's 11 rules become the most-tested code in the repo (pure domain, ≥80% coverage
  gate applies) and the B acceptance evidence is reproducible byte-for-byte.
- Inspection costs zero scanned bytes and needs less than the A-5 permission set —
  feeds the A-5 review (design-modules-wif-wiring §D-3) with concrete data.
- The findings JSON gives the A-level AI report generator a fixed deterministic frame,
  preserving the repo-wide "deterministic guards decide; AI writes text" principle.

**Negative:**

- The repo now carries two toolchains (Terraform + Python/uv); CI and the Makefile get
  more moving parts, and contributors need uv locally (`make setup` handles it).
- Three runtime dependencies enter the supply chain; Renovate + `make sbom` +
  security-scan must cover Python from PR 2 onward.
- Per-table `tables.get` collection is O(tables) API calls; very large estates will
  eventually want the INFORMATION_SCHEMA adapter (port already planned).

**Follow-ups:**

- Open the implementation issue + PR series per design §8 (GR-020 slices).
- Record in design-modules-wif-wiring §D-3: `bigquery.jobs.create` unused by the B
  path; keep in A-5 only for the A+ value scan.
- Decide deletion of the example `src/modules/catalog/` module (its MODULE.md says
  delete when real code lands).
- Update `.ai/architecture.md` stack table and `docs/requirements/README.md` index.
