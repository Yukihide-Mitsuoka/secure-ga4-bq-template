from pathlib import Path

ROOT = Path(__file__).parents[2]
WIF = ROOT / "infra" / "envs" / "dev" / "wif.tf"


def test_inspector_role_cannot_create_bigquery_jobs() -> None:
    terraform = WIF.read_text(encoding="utf-8")

    assert "permissions = [" in terraform
    assert '"bigquery.jobs.create"' not in terraform
