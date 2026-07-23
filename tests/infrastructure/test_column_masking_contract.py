from pathlib import Path

ROOT = Path(__file__).parents[2]
ENV = ROOT / "infra" / "envs" / "dev"


def _terraform() -> str:
    source = "\n".join(path.read_text(encoding="utf-8") for path in sorted(ENV.glob("*.tf")))
    return " ".join(source.split())


def test_column_masking_is_opt_in_and_uses_the_shared_data_policy_module() -> None:
    terraform = _terraform()

    assert 'variable "data_policies"' in terraform
    assert "default = {}" in terraform
    assert 'module "data_policy"' in terraform
    assert "modules/bigquery-data-policy?ref=v0.4.0" in terraform
    assert "for_each = var.data_policies" in terraform
    assert (
        "policy_tag = module.sensitivity.policy_tag_ids[each.value.policy_tag_level]" in terraform
    )
    assert "masked_readers = each.value.masked_readers" in terraform


def test_column_masking_rejects_unknown_levels_expressions_and_public_readers() -> None:
    terraform = _terraform()

    assert "Every data policy ID must contain only letters, digits, and underscores." in terraform
    assert 'contains(["high", "medium", "low"], policy.policy_tag_level)' in terraform
    assert '"EMAIL_MASK"' in terraform
    assert '"RANDOM_HASH"' in terraform
    assert 'contains(["allUsers", "allAuthenticatedUsers"], member)' in terraform
    assert "Only one data masking policy may be configured for each policy-tag level." in terraform


def test_column_masking_does_not_grant_project_wide_query_access() -> None:
    terraform = _terraform()

    assert 'output "data_policy_ids"' in terraform
    assert 'resource "google_project_iam_member" "data_policy' not in terraform
    assert 'resource "google_project_iam_binding" "data_policy' not in terraform
