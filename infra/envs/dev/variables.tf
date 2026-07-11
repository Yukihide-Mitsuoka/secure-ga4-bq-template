variable "project_id" {
  description = "GCP project for this environment."
  type        = string
}

variable "region" {
  description = "Region for ALL regional resources, including dataset location AND taxonomy location (one variable so they cannot diverge - column-level security requires them equal)."
  type        = string
  default     = "asia-northeast1"
}

variable "taxonomy_display_name" {
  description = "Sensitivity taxonomy display name (unique per project + location)."
  type        = string
  default     = "ga4-sensitivity"
}

# --- Engagement parameters (FR-7): override per engagement, template stays unchanged ---

variable "layer_iam_members" {
  description = "Per-layer dataset IAM bindings, keyed by layer name (staging/intermediate/marts). Basic roles and public members are rejected by the module."
  type = map(list(object({
    role   = string
    member = string
  })))
  default = {}
}

variable "fine_grained_readers" {
  description = "Sensitivity level -> members allowed to read columns tagged with that level."
  type        = map(list(string))
  default     = {}
}

# --- WIF wiring (design B) ---

variable "github_repository" {
  description = "GitHub repository (owner/name) whose workflows may impersonate the deployer and inspector SAs. Engagement instances MUST override this with their own repo."
  type        = string
  default     = "Yukihide-Mitsuoka/secure-ga4-bq-template"
}

variable "deployer_roles" {
  description = "Project roles for the deployer SA. Candidate minimal set per design B-1 (open point D-1: refine against a real apply; bigquery.dataOwner because dataEditor lacks bigquery.datasets.update, needed to manage dataset access entries; projectIamAdmin deliberately absent — this env manages no project-level IAM)."
  type        = list(string)
  default = [
    "roles/bigquery.dataOwner",
    "roles/datacatalog.admin",
    "roles/logging.configWriter",
  ]
}

variable "inspector_service_account_id" {
  description = "Account id (name before @) of the read-only inspector SA (FR-6)."
  type        = string
  default     = "bq-inspector"
}
