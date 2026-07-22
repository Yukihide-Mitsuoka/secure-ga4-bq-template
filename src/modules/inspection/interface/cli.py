"""`ga4-bq-inspect` — the on-demand, read-only inspection CLI (design §6).

Boundary rules live here (COD-011): argument parsing, params-file validation
errors → exit 2 with a message. Findings themselves never fail the run
(exit 0); `--fail-on` optionally gates CI on a severity floor (exit 1).
Auth is Application Default Credentials — `gcloud auth application-default
login` locally, WIF-minted on CI, identical code path.

Invoke via `make inspect PARAMS=<file>` (the canonical entry, CLAUDE.md §11)
or `uv run python -m src.modules.inspection.interface.cli ...`.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from src.modules.inspection.application.collect_snapshot import CollectSnapshot
from src.modules.inspection.application.run_inspection import RunInspection
from src.modules.inspection.domain.finding import Severity
from src.modules.inspection.domain.report import Report
from src.modules.inspection.infrastructure.csv_report_writer import CsvReportWriter
from src.modules.inspection.infrastructure.gcp.bigquery_metadata import BigQueryMetadataAdapter
from src.modules.inspection.infrastructure.gcp.client import GcpServices, build_gcp_services
from src.modules.inspection.infrastructure.gcp.data_catalog import DataCatalogTaxonomyAdapter
from src.modules.inspection.infrastructure.gcp.logging_config import LoggingConfigAdapter
from src.modules.inspection.infrastructure.gcp.resource_manager import ResourceManagerIamAdapter
from src.modules.inspection.infrastructure.json_report_writer import JsonReportWriter
from src.modules.inspection.infrastructure.markdown_report_writer import MarkdownReportWriter
from src.modules.inspection.infrastructure.system_clock import SystemClock
from src.modules.inspection.infrastructure.yaml_catalog_repository import YamlCatalogRepository
from src.modules.inspection.infrastructure.yaml_params_repository import YamlParamsRepository

_SEVERITY_RANK = {severity.value: rank for rank, severity in enumerate(Severity)}


def main(
    argv: Sequence[str] | None = None,
    *,
    services_factory: Callable[[], GcpServices] = build_gcp_services,
) -> int:
    args = _parser().parse_args(argv)

    try:
        params = YamlParamsRepository().load(args.params)
    except (ValueError, FileNotFoundError) as error:
        print(f"ga4-bq-inspect: invalid params: {error}", file=sys.stderr)
        return 2

    services = services_factory()
    runner = RunInspection(
        collector=CollectSnapshot(
            bigquery=BigQueryMetadataAdapter(services.bigquery),
            iam=ResourceManagerIamAdapter(services.resource_manager),
            taxonomies=DataCatalogTaxonomyAdapter(services.data_catalog),
            logging_config=LoggingConfigAdapter(services.logging),
            clock=SystemClock(),
        ),
        catalog_repository=YamlCatalogRepository(params.catalog_path),
    )
    report = runner.handle(params)

    out_dir = Path(args.out_dir) / report.project_id / report.captured_at.strftime("%Y%m%dT%H%M%SZ")
    json_path = JsonReportWriter().write(report, out_dir)
    CsvReportWriter().write(report, out_dir)
    MarkdownReportWriter().write(report, out_dir)

    counts = report.severity_counts()
    summary = ", ".join(f"{s.value}={counts.get(s.value, 0)}" for s in Severity)
    print(f"inspected {report.project_id}: {len(report.findings)} findings ({summary})")
    print(f"report: {json_path.parent}")

    if args.fail_on is not None and _breaches_floor(report, args.fail_on):
        print(f"failing: findings at or above --fail-on {args.fail_on}", file=sys.stderr)
        return 1
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ga4-bq-inspect",
        description="Read-only FR-4 inspection: 11 deterministic checkpoints, zero query jobs.",
    )
    parser.add_argument("--params", required=True, help="engagement parameters YAML (FR-7)")
    parser.add_argument("--out-dir", default="reports", help="report root (default: reports)")
    parser.add_argument(
        "--fail-on",
        choices=[s.value for s in Severity],
        default=None,
        help="exit 1 if any finding is at or above this severity (CI gate)",
    )
    return parser


def _breaches_floor(report: Report, floor: str) -> bool:
    floor_rank = _SEVERITY_RANK[floor]
    return any(_SEVERITY_RANK[f.severity.value] <= floor_rank for f in report.findings)


if __name__ == "__main__":
    raise SystemExit(main())
