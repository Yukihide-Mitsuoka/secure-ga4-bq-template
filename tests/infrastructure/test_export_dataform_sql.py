import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[2]
SCRIPT = ROOT / "scripts" / "export_dataform_sql.py"
PROFILE = ROOT / "profiles" / "dataform-bigquery"
SKELETON = PROFILE / "skeleton"


def _run(tmp_path: Path, graph: object) -> subprocess.CompletedProcess[str]:
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(graph), encoding="utf-8")
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--input",
            str(graph_path),
            "--output-dir",
            str(tmp_path / "compiled"),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )


def test_exports_tables_assertions_and_operations_as_regular_sql(tmp_path: Path) -> None:
    graph = {
        "graphErrors": {},
        "tables": [
            {
                "target": {"database": "project", "schema": "marts", "name": "orders"},
                "query": "select * from source",
            }
        ],
        "assertions": [
            {
                "target": {"database": "project", "schema": "checks", "name": "not_null"},
                "query": "select 1 where false",
            }
        ],
        "operations": [
            {
                "target": {"database": "project", "schema": "ops", "name": "refresh"},
                "queries": ["select 1", "select 2"],
            }
        ],
    }

    result = _run(tmp_path, graph)

    assert result.returncode == 0, result.stderr
    output = tmp_path / "compiled"
    assert (output / "tables" / "project__marts__orders.sql").read_text() == (
        "select * from source\n"
    )
    assert (output / "assertions" / "project__checks__not_null.sql").is_file()
    assert (output / "operations" / "project__ops__refresh__01.sql").is_file()
    assert (output / "operations" / "project__ops__refresh__02.sql").is_file()


def test_compilation_errors_fail_without_replacing_existing_output(tmp_path: Path) -> None:
    output = tmp_path / "compiled"
    output.mkdir()
    existing = output / "keep.txt"
    existing.write_text("keep", encoding="utf-8")

    result = _run(tmp_path, {"graphErrors": {"compilationErrors": [{"message": "bad"}]}})

    assert result.returncode == 1
    assert "contains compilation errors" in result.stderr
    assert existing.read_text(encoding="utf-8") == "keep"


def test_unmarked_output_directory_is_never_deleted(tmp_path: Path) -> None:
    output = tmp_path / "compiled"
    output.mkdir()
    existing = output / "keep.txt"
    existing.write_text("keep", encoding="utf-8")

    result = _run(tmp_path, {"graphErrors": {}, "tables": [{"query": "select 1"}]})

    assert result.returncode == 1
    assert "refusing to replace unmarked output directory" in result.stderr
    assert existing.read_text(encoding="utf-8") == "keep"


def test_dataform_toolchain_and_security_override_are_lockfile_pinned() -> None:
    package = json.loads((SKELETON / "package.json").read_text(encoding="utf-8"))
    lock = json.loads((SKELETON / "package-lock.json").read_text(encoding="utf-8"))

    assert package["dependencies"]["@dataform/core"] == "3.0.61"
    assert package["devDependencies"]["@dataform/cli"] == "3.0.61"
    assert package["overrides"]["parse-duration"] == "2.1.3"
    assert lock["packages"]["node_modules/parse-duration"]["version"] == "2.1.3"


def test_dataform_profile_uses_lockfile_mode_and_exports_cost_gate_sql() -> None:
    settings = (SKELETON / "workflow_settings.yaml").read_text(encoding="utf-8")
    makefile = (PROFILE / "Makefile").read_text(encoding="utf-8")

    assert "dataformCoreVersion:" not in settings
    assert "compile-cost-gate:" in makefile
    assert "npm ci --ignore-scripts" in makefile
    assert "npx --no-install dataform compile --json" in makefile
    assert "scripts/export_dataform_sql.py" in makefile
