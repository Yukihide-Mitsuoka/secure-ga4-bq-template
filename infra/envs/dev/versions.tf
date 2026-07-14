terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0, < 8.0"
    }
  }

  # The template selects the backend type but leaves the globally unique bucket to
  # each engagement: pass it with `terraform init -backend-config=...`.
  backend "gcs" {}
}

provider "google" {
  project = var.project_id
  region  = var.region
}
