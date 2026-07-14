"""Unit tests for the Data Catalog taxonomy adapter (nested pagination)."""

from typing import Any

from src.modules.inspection.infrastructure.gcp.data_catalog import DataCatalogTaxonomyAdapter


class FakeRequest:
    def __init__(self, response: dict[str, Any]) -> None:
        self._response = response

    def execute(self) -> dict[str, Any]:
        return self._response


class FakePolicyTagsResource:
    def __init__(self, pages_by_parent: dict[str, list[dict[str, Any]]]) -> None:
        self._pages_by_parent = pages_by_parent

    def list(self, parent: str, pageToken: str | None = None) -> FakeRequest:  # noqa: N803
        pages = self._pages_by_parent.get(parent, [{}])
        return FakeRequest(pages[0 if pageToken is None else int(pageToken)])


class FakeTaxonomiesResource:
    def __init__(
        self,
        taxonomy_pages: list[dict[str, Any]],
        tag_pages_by_parent: dict[str, list[dict[str, Any]]],
    ) -> None:
        self._taxonomy_pages = taxonomy_pages
        self._policy_tags = FakePolicyTagsResource(tag_pages_by_parent)
        self.listed_parents: list[str] = []

    def list(self, parent: str, pageToken: str | None = None) -> FakeRequest:  # noqa: N803
        self.listed_parents.append(parent)
        return FakeRequest(self._taxonomy_pages[0 if pageToken is None else int(pageToken)])

    def policyTags(self) -> FakePolicyTagsResource:  # noqa: N802
        return self._policy_tags


class FakeDataCatalogService:
    def __init__(self, taxonomies: FakeTaxonomiesResource) -> None:
        self._taxonomies = taxonomies

    def projects(self) -> "FakeDataCatalogService":
        return self

    def locations(self) -> "FakeDataCatalogService":
        return self

    def taxonomies(self) -> FakeTaxonomiesResource:
        return self._taxonomies


TAXONOMY = "projects/p/locations/asia-northeast1/taxonomies/1"


def test_taxonomies_and_their_tags_are_collected_across_pages() -> None:
    taxonomies = FakeTaxonomiesResource(
        taxonomy_pages=[
            {"taxonomies": [{"name": TAXONOMY, "displayName": "ga4-sensitivity"}]},
        ],
        tag_pages_by_parent={
            TAXONOMY: [
                {
                    "policyTags": [{"name": f"{TAXONOMY}/policyTags/1", "displayName": "high"}],
                    "nextPageToken": "1",
                },
                {"policyTags": [{"name": f"{TAXONOMY}/policyTags/2", "displayName": "medium"}]},
            ]
        },
    )
    result = DataCatalogTaxonomyAdapter(FakeDataCatalogService(taxonomies)).list_taxonomies(
        "p", "asia-northeast1"
    )
    assert len(result) == 1
    taxonomy = result[0]
    assert taxonomy.name == TAXONOMY
    assert taxonomy.display_name == "ga4-sensitivity"
    assert taxonomy.location == "asia-northeast1"
    assert [(t.name, t.display_name) for t in taxonomy.policy_tags] == [
        (f"{TAXONOMY}/policyTags/1", "high"),
        (f"{TAXONOMY}/policyTags/2", "medium"),
    ]


def test_location_without_taxonomies_yields_empty() -> None:
    taxonomies = FakeTaxonomiesResource(taxonomy_pages=[{}], tag_pages_by_parent={})
    adapter = DataCatalogTaxonomyAdapter(FakeDataCatalogService(taxonomies))
    assert adapter.list_taxonomies("p", "asia-northeast1") == ()


def test_us_multiregion_is_lowercased_for_data_catalog_api() -> None:
    taxonomies = FakeTaxonomiesResource(taxonomy_pages=[{}], tag_pages_by_parent={})
    adapter = DataCatalogTaxonomyAdapter(FakeDataCatalogService(taxonomies))

    assert adapter.list_taxonomies("p", "US") == ()
    assert taxonomies.listed_parents == ["projects/p/locations/us"]


def test_taxonomy_with_no_tags_still_appears() -> None:
    # CHK-05 needs the taxonomy itself even when every tag is missing/orphaned.
    taxonomies = FakeTaxonomiesResource(
        taxonomy_pages=[{"taxonomies": [{"name": TAXONOMY}]}],
        tag_pages_by_parent={TAXONOMY: [{}]},
    )
    result = DataCatalogTaxonomyAdapter(FakeDataCatalogService(taxonomies)).list_taxonomies(
        "p", "asia-northeast1"
    )
    assert result[0].policy_tags == ()
    assert result[0].display_name == ""
