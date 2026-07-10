variable "project_id" {
  description = "GCP project for this environment."
  type        = string
}

variable "region" {
  description = "Default region for regional resources."
  type        = string
  default     = "asia-northeast1"
}
