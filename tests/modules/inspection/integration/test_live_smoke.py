"""Live read-only smoke test — runs only when INSPECT_LIVE_PROJECT is set.

Not a substitute for unit coverage: this exercises the real ADC → discovery →
adapters → use case → writers path against a real project, end to end, with
zero mutations and zero query jobs (ADR-0003). CI never sets the env var, so
this skips there; run it locally against the FR-8 verification environment.
"""

import os
from pathlib import Path

import pytest

_PROJECT = os.environ.get("INSPECT_LIVE_PROJECT")

pytestmark = pytest.mark.skipif(
    not _PROJECT,
    reason="set INSPECT_LIVE_PROJECT (and optionally INSPECT_LIVE_LOCATION) to run",
)


def test_live_end_to_end_read_only(tmp_path: Path) -> None:
    from src.modules.inspection.application.collect_snapshot import CollectSnapshot
    from src.modules.inspection.application.run_inspection import RunInspection
    from src.modules.inspection.domain.params import InspectionParams
    from src.modules.inspection.infrastructure.gcp.bigquery_metadata import (
        BigQueryMetadataAdapter,
    )
    from src.modules.inspection.infrastructure.gcp.client import build_gcp_services
    from src.modules.inspection.infrastructure.gcp.data_catalog import (
        DataCatalogTaxonomyAdapter,
    )
    from src.modules.inspection.infrastructure.gcp.logging_config import LoggingConfigAdapter
    from src.modules.inspection.infrastructure.gcp.resource_manager import (
        ResourceManagerIamAdapter,
    )
    from src.modules.inspection.infrastructure.json_report_writer import JsonReportWriter
    from src.modules.inspection.infrastructure.system_clock import SystemClock
    from src.modules.inspection.infrastructure.yaml_catalog_repository import (
        YamlCatalogRepository,
    )

    assert _PROJECT is not None
    params = InspectionParams(
        project_id=_PROJECT,
        expected_location=os.environ.get("INSPECT_LIVE_LOCATION", "asia-northeast1"),
    )
    services = build_gcp_services()
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
    assert report.project_id == _PROJECT
    written = JsonReportWriter().write(report, tmp_path)
    assert written.exists() and written.stat().st_size > 0
