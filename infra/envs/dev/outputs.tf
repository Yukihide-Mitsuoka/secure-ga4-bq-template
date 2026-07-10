output "dataset_ids" {
  description = "Map: layer name -> dataset id."
  value       = { for k, m in module.layer_datasets : k => m.dataset_id }
}

output "policy_tag_ids" {
  description = "Map: sensitivity level -> full policy-tag resource name. Feed these to dbt (policy_tags) / Dataform (bigqueryPolicyTags) column configs."
  value       = module.sensitivity.policy_tag_ids
}
