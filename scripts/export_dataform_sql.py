#!/usr/bin/env python3
"""Export executable queries from a Dataform compiled graph for BigQuery dry runs."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

MARKER = ".generated-by-dataform-cost-gate"


def _slug(value: object) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value)).strip("._")
    return normalized or "unnamed"


def _action_name(action: dict[str, Any], fallback: str) -> str:
    target = action.get("target")
    if isinstance(target, dict):
        parts = [target.get("database"), target.get("schema"), target.get("name")]
        present = [_slug(part) for part in parts if part]
        if present:
            return "__".join(present)
    return _slug(action.get("fileName", fallback))


def _required_query(action: dict[str, Any], kind: str, name: str) -> str:
    query = action.get("query")
    if not isinstance(query, str) or not query.strip():
        raise ValueError(f"{kind} {name} has no executable query")
    return query.rstrip() + "\n"


def _actions(graph: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = graph.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"compiled graph field {key!r} must be a list of objects")
    return value


def collect_queries(graph: dict[str, Any]) -> list[tuple[Path, str]]:
    graph_errors = graph.get("graphErrors", {})
    if not isinstance(graph_errors, dict):
        raise ValueError("compiled graph field 'graphErrors' must be an object")
    if any(graph_errors.values()):
        raise ValueError("Dataform compiled graph contains compilation errors")

    queries: list[tuple[Path, str]] = []
    for kind in ("tables", "assertions"):
        for index, action in enumerate(_actions(graph, kind), start=1):
            if action.get("disabled") is True:
                continue
            name = _action_name(action, f"{kind}-{index}")
            queries.append((Path(kind) / f"{name}.sql", _required_query(action, kind, name)))

    for index, action in enumerate(_actions(graph, "operations"), start=1):
        if action.get("disabled") is True:
            continue
        name = _action_name(action, f"operation-{index}")
        statements = action.get("queries")
        if not isinstance(statements, list) or not statements:
            raise ValueError(f"operation {name} has no executable queries")
        for statement_index, statement in enumerate(statements, start=1):
            if not isinstance(statement, str) or not statement.strip():
                raise ValueError(f"operation {name} query {statement_index} is empty")
            path = Path("operations") / f"{name}__{statement_index:02d}.sql"
            queries.append((path, statement.rstrip() + "\n"))

    if not queries:
        raise ValueError("Dataform compiled graph contains no executable SQL")

    paths = [path for path, _ in queries]
    if len(paths) != len(set(paths)):
        raise ValueError("Dataform compiled graph produces duplicate SQL output paths")
    return sorted(queries, key=lambda item: item[0].as_posix())


def prepare_output(output_dir: Path, workspace: Path) -> Path:
    workspace = workspace.resolve()
    output_dir = output_dir.resolve()
    try:
        relative = output_dir.relative_to(workspace)
    except ValueError as exc:
        raise ValueError("output directory must stay inside the workspace") from exc
    if not relative.parts:
        raise ValueError("output directory must not be the workspace root")

    if output_dir.exists():
        marker = output_dir / MARKER
        if not marker.is_file():
            raise ValueError(f"refusing to replace unmarked output directory: {relative}")
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    (output_dir / MARKER).write_text("generated; safe to replace\n", encoding="ascii")
    return output_dir


def export_graph(input_path: Path, output_dir: Path, workspace: Path) -> int:
    if input_path.is_symlink() or not input_path.is_file():
        raise ValueError("compiled graph input must be a regular non-symlink file")
    loaded = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("compiled graph root must be an object")

    queries = collect_queries(loaded)
    destination = prepare_output(output_dir, workspace)
    for relative_path, query in queries:
        path = destination / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(query, encoding="utf-8")
    return len(queries)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Dataform compile --json output")
    parser.add_argument("--output-dir", required=True, type=Path, help="Generated SQL directory")
    args = parser.parse_args()

    try:
        count = export_graph(args.input, args.output_dir, Path.cwd())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"exported {count} Dataform SQL file(s) to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
