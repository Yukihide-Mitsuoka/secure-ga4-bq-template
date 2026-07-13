# Cost-gate WIF boundary (ADR-0006): the authenticated job is owned by the reviewed
# reusable workflow, not by caller-controlled compilation. A dedicated provider checks
# both the immutable caller repository ID and the exact reusable-workflow release.

resource "google_iam_workload_identity_pool_provider" "cost_gate" {
  project                            = var.project_id
  workload_identity_pool_id          = basename(module.github_oidc.pool_name)
  workload_identity_pool_provider_id = var.cost_gate_provider_id
  display_name                       = "BQ cost gate"
  description                        = "OIDC provider restricted to the trusted bq-cost-gate reusable workflow"

  attribute_condition = "attribute.repository_id == \"${var.github_repository_id}\" && attribute.job_workflow_ref == \"${var.cost_gate_workflow_ref}\""

  attribute_mapping = {
    "google.subject"             = "assertion.sub"
    "attribute.repository_id"    = "assertion.repository_id"
    "attribute.job_workflow_ref" = "assertion.job_workflow_ref"
  }

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account" "cost_gate" {
  project      = var.project_id
  account_id   = var.cost_gate_service_account_id
  display_name = "BQ cost gate (${var.github_repository})"
  description  = "BigQuery dry-run identity; no write roles and no project-wide data viewer."
}

resource "google_service_account_iam_member" "cost_gate_workload_identity_user" {
  service_account_id = google_service_account.cost_gate.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${module.github_oidc.pool_name}/attribute.job_workflow_ref/${var.cost_gate_workflow_ref}"
}

resource "google_project_iam_member" "cost_gate_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.cost_gate.email}"
}

locals {
  managed_cost_gate_datasets = {
    for dataset_id in keys(local.layers) :
    "${var.project_id}/${dataset_id}" => {
      project_id = var.project_id
      dataset_id = dataset_id
    }
  }

  cost_gate_reader_datasets = merge(
    local.managed_cost_gate_datasets,
    {
      for dataset in var.cost_gate_source_datasets :
      "${dataset.project_id}/${dataset.dataset_id}" => dataset
    },
  )
}

resource "google_bigquery_dataset_iam_member" "cost_gate_reader" {
  for_each = local.cost_gate_reader_datasets

  project    = each.value.project_id
  dataset_id = each.value.dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${google_service_account.cost_gate.email}"

  depends_on = [module.layer_datasets]
}
