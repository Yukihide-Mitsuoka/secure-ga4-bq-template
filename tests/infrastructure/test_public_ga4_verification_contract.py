from pathlib import Path

ROOT = Path(__file__).parents[2]
ENV = ROOT / "infra" / "envs" / "dev"
PROFILE = ROOT / "profiles" / "dataform-bigquery"
SKELETON = PROFILE / "skeleton"


def _terraform() -> str:
    source = "\n".join(path.read_text(encoding="utf-8") for path in sorted(ENV.glob("*.tf")))
    return " ".join(source.split())


def test_layer_dataset_ids_are_configurable_validated_and_used_by_cost_gate() -> None:
    terraform = _terraform()

    assert 'variable "layer_dataset_ids"' in terraform
    assert "staging = string" in terraform
    assert "intermediate = string" in terraform
    assert "marts = string" in terraform
    assert "Every layer dataset ID must contain only letters, numbers, or underscores" in terraform
    assert "Layer dataset IDs must be unique" in terraform
    assert "dataset_id = var.layer_dataset_ids[each.key]" in terraform
    assert "for dataset_id in values(var.layer_dataset_ids)" in terraform
    assert "for dataset_id in keys(local.layers)" not in terraform


def test_deployer_service_account_id_is_configurable_for_shared_projects() -> None:
    terraform = _terraform()

    assert 'variable "deployer_service_account_id"' in terraform
    assert 'default     = "github-deployer"' in terraform
    assert "deployer_service_account_id must be 6-30 lowercase letters" in terraform
    assert "service_account_id = var.deployer_service_account_id" in terraform


def test_dataform_profile_routes_models_to_configured_layer_datasets() -> None:
    settings = (SKELETON / "workflow_settings.yaml").read_text(encoding="utf-8")
    staging = (SKELETON / "definitions" / "staging" / "stg_ga4__events.sqlx").read_text(
        encoding="utf-8"
    )
    marts = (SKELETON / "definitions" / "marts" / "fct_events.sqlx").read_text(encoding="utf-8")

    for layer in ("staging", "intermediate", "marts"):
        assert f"{layer}_dataset:" in settings
    assert "schema: dataform.projectConfig.vars.staging_dataset" in staging
    assert "schema: dataform.projectConfig.vars.marts_dataset" in marts


def test_public_ga4_example_is_us_scoped_and_externally_managed() -> None:
    settings = (PROFILE / "public-ga4-workflow-settings.yaml.example").read_text(encoding="utf-8")

    assert "defaultLocation: US" in settings
    assert "ga4_export_project: bigquery-public-data" in settings
    assert "ga4_export_dataset: ga4_obfuscated_sample_ecommerce" in settings
    assert "staging_dataset: ga4_verify_example_staging" in settings
    assert "intermediate_dataset: ga4_verify_example_intermediate" in settings
    assert "marts_dataset: ga4_verify_example_marts" in settings
    assert "Do not add this public source to cost_gate_source_datasets" in settings
