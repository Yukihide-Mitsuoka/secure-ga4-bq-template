"""Discovery-client bootstrap: the only place credentials are resolved.

Application Default Credentials keep the CLI contract (design §6): `gcloud
auth application-default login` locally, WIF-minted credentials on CI — same
code. The requested scope is read-only cloud-platform as belt-and-braces on
top of the bq-inspector-role custom role (FR-6): even a mis-granted identity
cannot mutate anything through these clients.

googleapiclient is untyped; adapters receive the service objects as `Any`
and translate responses into the typed domain models, so the untyped surface
ends at this package boundary (COD-041).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import google.auth
from googleapiclient.discovery import build

_READ_ONLY_SCOPE = "https://www.googleapis.com/auth/cloud-platform.read-only"


@dataclass(frozen=True)
class GcpServices:
    """The four discovery services the collection ports need (ADR-0003)."""

    bigquery: Any
    resource_manager: Any
    data_catalog: Any
    logging: Any


def build_gcp_services() -> GcpServices:
    credentials, _ = google.auth.default(scopes=[_READ_ONLY_SCOPE])

    def _service(api: str, version: str) -> Any:
        # cache_discovery=False: the legacy file cache is oauth2client-era and
        # only produces warnings under google-auth credentials.
        return build(api, version, credentials=credentials, cache_discovery=False)

    return GcpServices(
        bigquery=_service("bigquery", "v2"),
        resource_manager=_service("cloudresourcemanager", "v3"),
        data_catalog=_service("datacatalog", "v1"),
        logging=_service("logging", "v2"),
    )
