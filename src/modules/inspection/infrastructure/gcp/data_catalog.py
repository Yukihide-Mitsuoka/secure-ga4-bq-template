"""TaxonomyPort implementation over datacatalog v1.

Read-only: taxonomies.list + policyTags.list per taxonomy (CHK-05's input).
Tag display names travel along so orphan-tag findings stay human-readable.
"""

from __future__ import annotations

from typing import Any

from src.modules.inspection.domain.snapshot import PolicyTag, Taxonomy
from src.modules.inspection.infrastructure.gcp.pagination import paginate


class DataCatalogTaxonomyAdapter:
    def __init__(self, data_catalog_service: Any) -> None:
        self._service = data_catalog_service

    def list_taxonomies(self, project_id: str, location: str) -> tuple[Taxonomy, ...]:
        taxonomies_resource = self._service.projects().locations().taxonomies()
        normalized_location = location.lower()
        parent = f"projects/{project_id}/locations/{normalized_location}"
        result: list[Taxonomy] = []
        for page in paginate(
            lambda token: taxonomies_resource.list(parent=parent, pageToken=token)
        ):
            for entry in page.get("taxonomies") or []:
                name = str(entry["name"])
                result.append(
                    Taxonomy(
                        name=name,
                        display_name=str(entry.get("displayName", "")),
                        location=normalized_location,
                        policy_tags=self._policy_tags(taxonomies_resource, name),
                    )
                )
        return tuple(result)

    @staticmethod
    def _policy_tags(taxonomies_resource: Any, taxonomy_name: str) -> tuple[PolicyTag, ...]:
        tags: list[PolicyTag] = []
        for page in paginate(
            lambda token: taxonomies_resource.policyTags().list(
                parent=taxonomy_name, pageToken=token
            )
        ):
            for tag in page.get("policyTags") or []:
                tags.append(
                    PolicyTag(name=str(tag["name"]), display_name=str(tag.get("displayName", "")))
                )
        return tuple(tags)
