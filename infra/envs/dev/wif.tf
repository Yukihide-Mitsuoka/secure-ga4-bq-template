# WIF wiring (design-modules-wif-wiring.md §B): keyless GitHub Actions auth with two
# purpose-separated service accounts — deployer (terraform apply) and inspector
# (read-only inspection, FR-6). The inspection path never carries write permissions.
#
# The inspector SA is plain resources here, not a github-oidc module extension
# (design §D-2): the module creates exactly one SA and this is its first second
# consumer — promote to the library on the rule of three (COD-020).

module "github_oidc" {
  source = "git::https://github.com/Yukihide-Mitsuoka/terraform-gcp-modules.git//modules/github-oidc?ref=v0.3.0"

  project_id        = var.project_id
  github_repository = var.github_repository
  roles             = var.deployer_roles
}

# --- Inspector SA (FR-6): federated read-only identity for bq-inspect runs ---

resource "google_service_account" "inspector" {
  project      = var.project_id
  account_id   = var.inspector_service_account_id
  display_name = "BQ governance inspector (${var.github_repository})"
  description  = "Read-only inspection engine identity (FR-6). Never grant write roles."
}

# Same pool, same repository attribute as the deployer — only workflows of this
# repository can impersonate the inspector.
resource "google_service_account_iam_member" "inspector_workload_identity_user" {
  service_account_id = google_service_account.inspector.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${module.github_oidc.pool_name}/attribute.repository/${var.github_repository}"
}

# Custom read-only role per design §A-5. No predefined role bundles exactly these
# reads (sink config in particular), and every predefined candidate is broader —
# a governance tool must not itself demand excess permissions (FR-6).
resource "google_project_iam_custom_role" "bq_inspector" {
  project     = var.project_id
  role_id     = "bqInspector"
  title       = "BigQuery governance inspector (read-only)"
  description = "Least-privilege reads for the FR-4 inspection engine: BQ metadata, taxonomies, project IAM, logging config."

  permissions = [
    # BigQuery metadata / schema (datasets, tables, per-field policy tags)
    "bigquery.datasets.get",
    "bigquery.tables.get",
    "bigquery.tables.list",
    # Query jobs: NOT used by the deterministic B path (REST metadata only,
    # ADR-0003) — kept solely for the A+ value scan, which genuinely queries data.
    "bigquery.jobs.create",
    # Taxonomies / policy tags (checkpoint #5) + tag-level IAM review
    "datacatalog.taxonomies.get",
    "datacatalog.taxonomies.list",
    "datacatalog.categories.getIamPolicy",
    # Project IAM policy incl. auditConfigs (checkpoints #1-#3, #6)
    "resourcemanager.projects.getIamPolicy",
    # Logging routing config (checkpoints #6-#7)
    "logging.sinks.get",
    "logging.sinks.list",
    "logging.exclusions.list",
  ]
}

resource "google_project_iam_member" "inspector_custom_role" {
  project = var.project_id
  role    = google_project_iam_custom_role.bq_inspector.id
  member  = "serviceAccount:${google_service_account.inspector.email}"
}
