variable "github_repository_id" {
  description = "Immutable numeric GitHub repository ID whose callers may use the cost-gate identity. Engagement instances MUST override this with their own repository ID."
  type        = string
  default     = "1296879276"

  validation {
    condition     = can(regex("^[0-9]+$", var.github_repository_id))
    error_message = "github_repository_id must contain digits only."
  }
}

variable "cost_gate_provider_id" {
  description = "Workload Identity Pool provider ID dedicated to the trusted cost-gate reusable workflow."
  type        = string
  default     = "github-cost-gate"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,30}[a-z0-9]$", var.cost_gate_provider_id))
    error_message = "cost_gate_provider_id must be 4-32 lowercase letters, digits, or hyphens, starting with a letter and ending with a letter or digit."
  }
}

variable "cost_gate_service_account_id" {
  description = "Account ID of the BigQuery dry-run-only cost-gate service account."
  type        = string
  default     = "bq-cost-gate"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.cost_gate_service_account_id))
    error_message = "cost_gate_service_account_id must be 6-30 lowercase letters, digits, or hyphens, starting with a letter and ending with a letter or digit."
  }
}

variable "cost_gate_workflow_ref" {
  description = "Exact job_workflow_ref accepted for WIF; must match the immutable bq-cost-gate caller release."
  type        = string
  default     = "Yukihide-Mitsuoka/gcp-cicd-workflows/.github/workflows/bq-cost-gate.yml@refs/tags/v2.0.1"

  validation {
    condition = can(regex(
      "^[^/]+/[^/]+/\\.github/workflows/[^@]+@refs/tags/v[0-9]+\\.[0-9]+\\.[0-9]+$",
      var.cost_gate_workflow_ref,
    ))
    error_message = "cost_gate_workflow_ref must identify an exact semantic-version tag under .github/workflows."
  }
}

variable "cost_gate_source_datasets" {
  description = "Additional source datasets the dry-run gate may read, including raw GA4 or cross-project sources. Managed staging/intermediate/marts datasets are included automatically."
  type = list(object({
    project_id = string
    dataset_id = string
  }))
  default = []

  validation {
    condition = alltrue([
      for dataset in var.cost_gate_source_datasets :
      length(trimspace(dataset.project_id)) > 0 &&
      can(regex("^[A-Za-z0-9_]+$", dataset.dataset_id))
    ])
    error_message = "Every cost_gate_source_datasets entry needs a project_id and an alphanumeric-or-underscore dataset_id."
  }

  validation {
    condition = length(var.cost_gate_source_datasets) == length(toset([
      for dataset in var.cost_gate_source_datasets :
      "${dataset.project_id}/${dataset.dataset_id}"
    ]))
    error_message = "cost_gate_source_datasets must not contain duplicate project/dataset pairs."
  }
}
