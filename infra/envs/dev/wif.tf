# WIF wiring (design-modules-wif-wiring.md §B): keyless GitHub Actions auth with two
# purpose-separated service accounts — deployer (terraform apply) and inspector
# (read-only inspection, FR-6). The inspection path never carries write permissions.
#
# The inspector SA itself is a plain resource here, not a github-oidc module
# extension (design §D-2): that module creates exactly one SA and this is its
# first second consumer — promote to the library on the rule of three (COD-020).
# Its custom role, however, IS a library module (design §A-5): bq-inspector-role.

module "github_oidc" {
  source = "git::https://github.com/Yukihide-Mitsuoka/terraform-gcp-modules.git//modules/github-oidc?ref=v0.3.0"

  project_id         = var.project_id
  github_repository  = var.github_repository
  pool_id            = var.github_workload_identity_pool_id
  service_account_id = var.deployer_service_account_id
  roles              = var.deployer_roles
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
# reads (sink config in particular), and every predefined candidate is broader.
# ADR-0003 selected REST metadata only, so override the shared module's broader
# INFORMATION_SCHEMA-ready default and omit bigquery.jobs.create.
module "inspector_role" {
  source = "git::https://github.com/Yukihide-Mitsuoka/terraform-gcp-modules.git//modules/bq-inspector-role?ref=v0.4.0"

  project_id         = var.project_id
  inspector_sa_email = google_service_account.inspector.email
  permissions = [
    "bigquery.datasets.get",
    "bigquery.tables.get",
    "bigquery.tables.list",
    "datacatalog.taxonomies.get",
    "datacatalog.taxonomies.list",
    "datacatalog.categories.getIamPolicy",
    "resourcemanager.projects.getIamPolicy",
    "logging.sinks.get",
    "logging.sinks.list",
    "logging.exclusions.list",
  ]
}
