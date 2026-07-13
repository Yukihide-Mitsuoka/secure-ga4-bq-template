# ADR-0006: Bind cost-gate WIF to the trusted reusable workflow

| Field | Value |
|-------|-------|
| Status | proposed |
| Date | 2026-07-13 |
| Deciders | Repository owner |
| Author | Codex |
| Supersedes / Superseded by | - |

## Context

The A-level acceptance path requires the pull-request cost gate to dry-run compiled SQL
against BigQuery. That operation needs `bigquery.jobs.create` in the execution project
and `bigquery.tables.getData` on every referenced table or view. The existing deployer
service account is writable and therefore too privileged, while the inspector identity
is intentionally query-free and must remain read-only metadata access.

The original `bq-cost-gate` reusable workflow ran caller-controlled compilation after
WIF authentication. `gcp-cicd-workflows` v2 fixes that boundary by compiling without
credentials and allowing only isolated SQL files into a fixed authenticated dry-run
job. The caller repository must now wire that workflow without recreating a credential
confused-deputy path.

The current WIF provider and service-account bindings trust every workflow in one named
GitHub repository through `attribute.repository`. A pull request can modify a caller
workflow, so repository-only trust would let a different job request the same cost-gate
credentials. Repository names can also be reclaimed after deletion. The cost-gate trust
boundary must identify both the immutable caller repository identity and the trusted
reusable workflow that owns the authenticated job.

## Options considered

### Option 1: Do nothing

Do not wire the cost gate. This has no new infrastructure or operational cost, but leaves
the A-level cost-gate requirement incomplete and provides no pull-request scan-budget
enforcement.

### Option 2: Reuse the deployer or the repository-wide WIF provider

This is the smallest Terraform change. A dedicated service account on the existing
provider would improve role separation, but any workflow in the caller repository could
still impersonate it. Reusing the deployer would additionally expose write permissions.
Both variants preserve the trust-boundary flaw and are rejected by GR-030.

### Option 3: Add a dedicated provider and least-privilege service account

Create a second provider in the existing pool. Map `repository_id` and
`job_workflow_ref`, require the expected numeric caller repository ID and the exact
released `bq-cost-gate.yml` ref, and bind a dedicated service account through the mapped
workflow attribute. Grant only BigQuery Job User on the execution project and BigQuery
Data Viewer on managed layer datasets plus explicitly configured source datasets.

This adds several Terraform resources and makes reusable-workflow upgrades deliberate:
the caller ref and WIF condition must change together. It has the smallest credential
blast radius and leaves the existing deployer and inspector paths unchanged.

### Option 4: Generalize the shared github-oidc module first

Extend `terraform-gcp-modules//modules/github-oidc` to model multiple providers, claim
sets, service accounts, and resource-level grants. This could help future consumers, but
it expands a shared public interface before a repeated provider-specific pattern exists.
The cost gate also needs dataset IAM that the project-IAM-oriented module does not own.
The larger cross-repository blast radius is not justified yet.

## Decision

Choose option 3. The cost gate MUST use its own WIF provider and service account. The
provider MUST accept only the configured numeric caller `repository_id` and exact
`job_workflow_ref` for the released v2 cost-gate workflow. The service account MUST NOT
receive write roles or project-wide BigQuery Data Viewer; it receives BigQuery Job User
on the execution project and Data Viewer only on managed layer datasets and explicitly
listed source datasets. The caller MUST use the matching immutable workflow release and
a credential-free compile command. Existing `WIF_PROVIDER`, deployer, and inspector
bindings remain unchanged; the caller receives separate `COST_GATE_WIF_PROVIDER` and
`COST_GATE_SA` values.

## Consequences

**Positive:**

- Pull-request-controlled jobs cannot obtain cost-gate credentials merely by belonging
  to the trusted repository; authentication is tied to the reviewed reusable workflow.
- A compromised cost-gate identity cannot apply Terraform or mutate BigQuery resources.
- Numeric repository identity prevents repository-name reclamation from inheriting
  trust, and dataset-level grants keep readable data scope explicit.
- The existing deployment and inspection paths do not migrate or share new permissions.

**Negative:**

- The environment gains a provider, service account, impersonation binding, project IAM
  binding, and dataset IAM bindings.
- Upgrading the reusable workflow requires a coordinated caller and Terraform condition
  change. A mismatch fails closed by rejecting WIF authentication.
- Every raw or cross-project source referenced by compiled SQL must grant Data Viewer to
  the cost-gate service account explicitly.
- BigQuery dry-run output exposes estimated processed bytes to pull-request logs. It does
  not return row data, but repository access remains part of the information boundary.

**Follow-ups:**

- Implement and test the dedicated provider, service account, outputs, and scoped IAM.
- Add an opt-in caller pinned to the matching v2 release and a credential-free compile
  target for the selected transform profile.
- Document repository variables, source-dataset grants, upgrade order, and fail-closed
  troubleshooting.
- Reconsider a shared module only after another consumer needs the same multi-provider
  claim-boundary pattern.
