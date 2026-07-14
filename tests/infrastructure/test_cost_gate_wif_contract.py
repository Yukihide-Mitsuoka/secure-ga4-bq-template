from pathlib import Path

ROOT = Path(__file__).parents[2]
ENV = ROOT / "infra" / "envs" / "dev"


def _terraform() -> str:
    source = "\n".join(path.read_text(encoding="utf-8") for path in sorted(ENV.glob("*.tf")))
    return " ".join(source.split())


def test_cost_gate_wif_is_bound_to_the_trusted_reusable_workflow() -> None:
    terraform = _terraform()

    assert 'resource "google_iam_workload_identity_pool_provider" "cost_gate"' in terraform
    assert '"attribute.repository_id" = "assertion.repository_id"' in terraform
    assert '"attribute.job_workflow_ref" = "assertion.job_workflow_ref"' in terraform
    assert "attribute.repository_id ==" in terraform
    assert "attribute.job_workflow_ref ==" in terraform
    assert "/attribute.job_workflow_ref/${var.cost_gate_workflow_ref}" in terraform


def test_cost_gate_identity_has_only_job_and_dataset_read_roles() -> None:
    terraform = _terraform()

    assert 'resource "google_service_account" "cost_gate"' in terraform
    assert 'resource "google_project_iam_member" "cost_gate_job_user"' in terraform
    assert 'role = "roles/bigquery.jobUser"' in terraform
    assert 'resource "google_bigquery_dataset_iam_member" "cost_gate_reader"' in terraform
    assert 'role = "roles/bigquery.dataViewer"' in terraform
    assert 'resource "google_project_iam_member" "cost_gate_data_viewer"' not in terraform


def test_cost_gate_configuration_and_outputs_are_separate() -> None:
    terraform = _terraform()

    for name in (
        "github_repository_id",
        "github_workload_identity_pool_id",
        "cost_gate_provider_id",
        "cost_gate_service_account_id",
        "cost_gate_workflow_ref",
        "cost_gate_source_datasets",
    ):
        assert f'variable "{name}"' in terraform

    assert "pool_id = var.github_workload_identity_pool_id" in terraform
    assert 'output "cost_gate_workload_identity_provider"' in terraform
    assert 'output "cost_gate_sa_email"' in terraform
