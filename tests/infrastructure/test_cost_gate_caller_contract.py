from pathlib import Path

ROOT = Path(__file__).parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "bq-cost-gate.yml"
TERRAFORM_VARIABLES = ROOT / "infra" / "envs" / "dev" / "cost_gate_variables.tf"
SMOKE_SQL = ROOT / "tests" / "fixtures" / "bq-cost-gate" / "smoke.sql"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_cost_gate_caller_is_opt_in_and_uses_the_trusted_release() -> None:
    workflow = _read(WORKFLOW)
    terraform = _read(TERRAFORM_VARIABLES)

    assert "on:\n  pull_request:" in workflow
    assert "if: vars.BQ_COST_GATE_ENABLED == 'true'" in workflow
    assert "bq-cost-gate.yml@39358e9d0ad17c508dfef5d55a2c3004b0f61227 # v2.0.2" in workflow
    assert "bq-cost-gate.yml@refs/tags/v2.0.2" in terraform
    assert "contents: read" in workflow
    assert "id-token: write" in workflow


def test_cost_gate_caller_uses_only_its_dedicated_identity() -> None:
    workflow = _read(WORKFLOW)

    assert "wif_provider: ${{ vars.COST_GATE_WIF_PROVIDER }}" in workflow
    assert "service_account: ${{ vars.COST_GATE_SA }}" in workflow
    assert "${{ vars.WIF_PROVIDER }}" not in workflow
    assert "${{ vars.DEPLOYER_SA }}" not in workflow
    assert "${{ vars.INSPECTOR_SA }}" not in workflow


def test_cost_gate_caller_exposes_compile_and_budget_inputs() -> None:
    workflow = _read(WORKFLOW)

    assert "sql_glob: ${{ vars.BQ_COST_GATE_SQL_GLOB }}" in workflow
    assert "compile_command: ${{ vars.BQ_COST_GATE_COMPILE_COMMAND }}" in workflow
    assert "project_id: ${{ vars.GCP_PROJECT_ID }}" in workflow
    assert (
        "default_max_bytes: ${{ vars.BQ_COST_GATE_DEFAULT_MAX_BYTES || '100000000000' }}"
        in workflow
    )
    assert "budgets_file: ${{ vars.BQ_COST_GATE_BUDGETS_FILE }}" in workflow


def test_cost_gate_smoke_query_needs_no_source_dataset() -> None:
    sql = _read(SMOKE_SQL)

    assert sql.strip() == "SELECT 1 AS cost_gate_smoke;"
