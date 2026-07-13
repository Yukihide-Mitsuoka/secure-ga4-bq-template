output "cost_gate_workload_identity_provider" {
  description = "Cost-gate-only WIF provider resource name -> repo variable COST_GATE_WIF_PROVIDER."
  value       = google_iam_workload_identity_pool_provider.cost_gate.name
}

output "cost_gate_sa_email" {
  description = "BigQuery dry-run SA email -> repo variable COST_GATE_SA."
  value       = google_service_account.cost_gate.email
}
