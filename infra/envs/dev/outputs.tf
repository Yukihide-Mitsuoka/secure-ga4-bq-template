output "dataset_ids" {
  description = "Map: layer name -> dataset id."
  value       = { for k, m in module.layer_datasets : k => m.dataset_id }
}

output "policy_tag_ids" {
  description = "Map: sensitivity level -> full policy-tag resource name. Feed these to dbt (policy_tags) / Dataform (bigqueryPolicyTags) column configs."
  value       = module.sensitivity.policy_tag_ids
}

# GitHub repo variables (design B-2 step 3): WIF_PROVIDER / DEPLOYER_SA / INSPECTOR_SA.
output "workload_identity_provider" {
  description = "WIF provider resource name -> repo variable WIF_PROVIDER."
  value       = module.github_oidc.workload_identity_provider
}

output "deployer_sa_email" {
  description = "Deployer SA email -> repo variable DEPLOYER_SA (tf-plan/tf-apply)."
  value       = module.github_oidc.service_account_email
}

output "inspector_sa_email" {
  description = "Inspector SA email -> repo variable INSPECTOR_SA (bq-inspect; read-only, FR-6)."
  value       = google_service_account.inspector.email
}

output "inspector_role_id" {
  description = "Full bqInspector custom role resource name (design A-5)."
  value       = module.inspector_role.role_id
}
