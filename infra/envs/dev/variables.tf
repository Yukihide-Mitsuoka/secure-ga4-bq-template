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
