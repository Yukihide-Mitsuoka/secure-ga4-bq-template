terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0, < 8.0"
    }
  }

  # TEMPLATE: configure your state backend, e.g.
  # backend "gcs" {
  #   bucket = "{{STATE_BUCKET}}"
  #   prefix = "envs/dev"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
