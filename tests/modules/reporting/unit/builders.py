from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def artifact_data() -> dict[str, Any]:
    return {
        "meta": {
            "project_id": "secret-project",
            "captured_at": "2026-07-12T00:00:00+00:00",
            "params": {"catalog_path": "/private/catalog.yml"},
        },
        "coverage": {"datasets": 1, "tables": 1, "columns": 2, "skipped": []},
        "findings": [
            {
                "check_id": "CHK-03",
                "severity": "HIGH",
                "resource": "projects/secret-project/datasets/customer_mart",
                "observed": "user:private@example.com has roles/bigquery.dataOwner",
                "expected": "Dataset-scoped access",
                "rule_ref": "FR-4#3",
                "remediation_hint": "Replace the broad role with a dataset role.",
            }
        ],
    }


def write_artifact(path: Path, data: dict[str, Any] | None = None) -> Path:
    path.write_text(json.dumps(data or artifact_data()), encoding="utf-8")
    return path
