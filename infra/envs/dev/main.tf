# Example root config: modules come from the shared library, pinned by tag.
# Bump ?ref= deliberately when upgrading (never track a branch).

module "network" {
  source     = "git::https://github.com/Yukihide-Mitsuoka/terraform-gcp-modules.git//modules/network?ref=v0.1.0"
  project_id = var.project_id
  name       = "core"

  subnets = [
    { name = "app", cidr = "10.0.0.0/24", region = var.region },
  ]
}
