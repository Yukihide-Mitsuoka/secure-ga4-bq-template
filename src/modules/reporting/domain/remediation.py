from __future__ import annotations

from dataclasses import dataclass

REMEDIATION_RECIPE_VERSION = "v1"

_TERRAFORM_VALIDATION = (
    "Run terraform fmt -check on the reviewed configuration.",
    "Run terraform validate in the owning root module.",
    "Review terraform plan and obtain the engagement approval gate.",
)
_POLICY_VALIDATION = (
    "Validate the draft against the engagement policy and current GCP metadata.",
    "Confirm the scope and retention values with the data owner.",
    "Record human approval before translating the draft into configuration.",
)
_DATASET_IAM_EXAMPLE = """resource \"google_bigquery_dataset_iam_member\" \"replacement\" {
  project    = \"REPLACE_ME_PROJECT_ID\"
  dataset_id = \"REPLACE_ME_DATASET_ID\"
  role       = \"REPLACE_ME_LEAST_PRIVILEGE_ROLE\"
  member     = \"REPLACE_ME_MEMBER\"
}"""


@dataclass(frozen=True)
class RemediationRecipe:
    recipe_id: str
    title: str
    kind: str
    required_inputs: tuple[str, ...]
    example_language: str | None
    example: str | None
    validation_steps: tuple[str, ...]


REMEDIATION_RECIPES = {
    "CHK-01": RemediationRecipe(
        "IAM_BASIC_ROLE_V1",
        "Replace a basic role with dataset-scoped least privilege",
        "terraform",
        ("project_id", "dataset_id", "member", "least_privilege_role"),
        "hcl",
        _DATASET_IAM_EXAMPLE,
        _TERRAFORM_VALIDATION,
    ),
    "CHK-02": RemediationRecipe(
        "IAM_PUBLIC_ACCESS_V1",
        "Replace public access with an approved authenticated principal",
        "terraform",
        ("project_id", "dataset_id", "approved_member", "least_privilege_role"),
        "hcl",
        _DATASET_IAM_EXAMPLE,
        _TERRAFORM_VALIDATION,
    ),
    "CHK-03": RemediationRecipe(
        "IAM_PROJECT_SCOPE_V1",
        "Move broad project data access to dataset scope",
        "terraform",
        ("project_id", "dataset_id", "member", "dataset_role"),
        "hcl",
        _DATASET_IAM_EXAMPLE,
        _TERRAFORM_VALIDATION,
    ),
    "CHK-04": RemediationRecipe(
        "COLUMN_POLICY_TAG_V1",
        "Attach the catalog-required policy tag to the column schema",
        "policy-json",
        ("column_name", "column_type", "policy_tag_resource_name"),
        "json",
        """{
  \"name\": \"REPLACE_ME_COLUMN_NAME\",
  \"type\": \"REPLACE_ME_COLUMN_TYPE\",
  \"policyTags\": {\"names\": [\"REPLACE_ME_POLICY_TAG_RESOURCE_NAME\"]}
}""",
        _POLICY_VALIDATION,
    ),
    "CHK-05": RemediationRecipe(
        "TAXONOMY_RECONCILIATION_V1",
        "Reconcile taxonomy references in the owning regional catalog",
        "manual",
        ("taxonomy_location", "expected_policy_tag", "referencing_columns"),
        None,
        None,
        _POLICY_VALIDATION,
    ),
    "CHK-06": RemediationRecipe(
        "AUDIT_SCOPE_POLICY_V1",
        "Limit Data Access logging to the approved sensitivity scope",
        "policy-yaml",
        ("high_sensitivity_datasets", "approved_log_types", "exclusion_scope"),
        "yaml",
        """audit_scope:
  included_datasets:
    - REPLACE_ME_HIGH_SENSITIVITY_DATASET
  log_types:
    - REPLACE_ME_APPROVED_LOG_TYPE
  exclusion_filter: REPLACE_ME_EXCLUSION_FILTER""",
        _POLICY_VALIDATION,
    ),
    "CHK-07": RemediationRecipe(
        "LOG_SINK_RETENTION_V1",
        "Create a bounded audit sink with an approved filter",
        "terraform",
        ("project_id", "sink_name", "destination", "filter"),
        "hcl",
        """resource \"google_logging_project_sink\" \"audit\" {
  project                = \"REPLACE_ME_PROJECT_ID\"
  name                   = \"REPLACE_ME_SINK_NAME\"
  destination            = \"REPLACE_ME_DESTINATION\"
  filter                 = \"REPLACE_ME_FILTER\"
  unique_writer_identity = true
}""",
        _TERRAFORM_VALIDATION,
    ),
    "CHK-08": RemediationRecipe(
        "TABLE_PARTITION_CLUSTER_V1",
        "Add workload-appropriate partitioning and clustering",
        "terraform-fragment",
        ("partition_field", "partition_type", "clustering_fields"),
        "hcl",
        """time_partitioning {
  type  = \"REPLACE_ME_PARTITION_TYPE\"
  field = \"REPLACE_ME_PARTITION_FIELD\"
}
clustering = [\"REPLACE_ME_CLUSTERING_FIELD\"]""",
        _TERRAFORM_VALIDATION,
    ),
    "CHK-09": RemediationRecipe(
        "REQUIRE_PARTITION_FILTER_V1",
        "Require partition filters on the table",
        "terraform-fragment",
        ("owning_table_resource",),
        "hcl",
        "require_partition_filter = true",
        _TERRAFORM_VALIDATION,
    ),
    "CHK-10": RemediationRecipe(
        "TABLE_EXPIRATION_V1",
        "Set an approved table expiration",
        "terraform-fragment",
        ("retention_policy", "expiration_time_milliseconds"),
        "hcl",
        "expiration_time = REPLACE_ME_EPOCH_MILLISECONDS",
        _TERRAFORM_VALIDATION,
    ),
    "CHK-11": RemediationRecipe(
        "DATASET_HYGIENE_V1",
        "Align dataset location, expiration, and default encryption",
        "terraform-fragment",
        ("location", "default_table_expiration_ms", "kms_key_name"),
        "hcl",
        """location                    = \"REPLACE_ME_LOCATION\"
default_table_expiration_ms = REPLACE_ME_EXPIRATION_MILLISECONDS

default_encryption_configuration {
  kms_key_name = \"REPLACE_ME_KMS_KEY_NAME\"
}""",
        _TERRAFORM_VALIDATION,
    ),
    "CHK-12": RemediationRecipe(
        "MART_DESCRIPTION_V1",
        "Add the missing mart metadata description",
        "manual",
        ("owning_model", "resource_name", "approved_description"),
        None,
        None,
        (
            "Identify the owning dbt, Dataform, Terraform, or DDL definition.",
            "Add an approved non-empty description to the table, view, or leaf column.",
            "Deploy through the reviewed workflow and rerun the inspection.",
        ),
    ),
}


def recipe_for(check_id: str) -> RemediationRecipe:
    return REMEDIATION_RECIPES[check_id]
