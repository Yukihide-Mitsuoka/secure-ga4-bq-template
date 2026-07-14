# Verification environment (acceptance criteria B): the minimum module set —
# layer datasets + sensitivity taxonomy. Modules come from the shared library,
# pinned by tag; bump ?ref= deliberately (never track a branch).
#
# The raw GA4 export dataset (analytics_*) is created by Google, not Terraform. Lock a
# private export down with dataset-level IAM out of band (requirements §3.3). Public
# verification sources remain externally managed and MUST NOT receive Terraform IAM.
#
# Both modules receive the SAME var.region: the taxonomy location must equal the
# dataset location or column-level security silently fails (design doc, horizontal
# constraint). Sharing one variable enforces that by construction.

locals {
  layers = {
    staging      = "GA4 staging layer (stg_ga4__*) - typed unnest of export columns"
    intermediate = "Intermediate logic (int_*)"
    marts        = "Mart layer (fct_*/dim_*) - policy-tagged columns live here"
  }
}

module "layer_datasets" {
  source   = "git::https://github.com/Yukihide-Mitsuoka/terraform-gcp-modules.git//modules/bigquery-dataset?ref=v0.3.0"
  for_each = local.layers

  project_id  = var.project_id
  dataset_id  = var.layer_dataset_ids[each.key]
  location    = var.region
  description = each.value
  labels      = { layer = each.key }
  iam_members = lookup(var.layer_iam_members, each.key, [])
}

module "sensitivity" {
  source = "git::https://github.com/Yukihide-Mitsuoka/terraform-gcp-modules.git//modules/bigquery-policy-tags?ref=v0.3.0"

  project_id            = var.project_id
  location              = var.region
  taxonomy_display_name = var.taxonomy_display_name
  fine_grained_readers  = var.fine_grained_readers
}
