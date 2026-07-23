"""Unit tests for the YAML sensitivity-catalog repository (boundary validation)."""

from pathlib import Path

import pytest

from src.modules.inspection.infrastructure.yaml_catalog_repository import YamlCatalogRepository


def _write(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "catalog.yml"
    path.write_text(content, encoding="utf-8")
    return path


def test_shipped_template_catalog_loads_and_resolves() -> None:
    # Golden test: the template's own catalog (LOG-0011) must always be loadable.
    catalog = YamlCatalogRepository("catalog/ga4-sensitivity.yml").load()
    assert catalog.levels == ("high", "medium", "low")
    assert catalog.effective_level("user_id") == "high"
    assert catalog.effective_level("page_location") == "high"  # promoted key
    source = catalog.promotion_source("page_location")
    assert source is not None
    assert (source.field_path, source.key) == ("event_params", "page_location")
    assert catalog.overrides == {}


def test_version_one_promoted_event_param_is_read_as_structured_source(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "version: 1\nlevels: [high]\npromoted_event_params:\n  legacy_email: high\n",
    )

    catalog = YamlCatalogRepository(path).load()

    source = catalog.promotion_source("legacy_email")
    assert catalog.effective_level("legacy_email") == "high"
    assert source is not None
    assert (source.field_path, source.key) == ("event_params", "legacy_email")


def test_version_two_promoted_column_accepts_source_agnostic_paths(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "version: 2\n"
        "levels: [high]\n"
        "promoted_columns:\n"
        "  customer_email:\n"
        "    level: high\n"
        "    source:\n"
        "      field_path: custom_attributes\n"
        "      key: primary_email\n",
    )

    catalog = YamlCatalogRepository(path).load()

    source = catalog.promotion_source("customer_email")
    assert catalog.effective_level("customer_email") == "high"
    assert source is not None
    assert (source.field_path, source.key) == ("custom_attributes", "primary_email")


def test_version_two_missing_source_is_preserved_for_chk13(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "version: 2\nlevels: [high]\npromoted_columns:\n  customer_email:\n    level: high\n",
    )

    catalog = YamlCatalogRepository(path).load()

    assert catalog.effective_level("customer_email") == "high"
    assert catalog.promotion_source("customer_email") is None


@pytest.mark.parametrize(
    "content",
    [
        ("version: 1\nlevels: [high]\npromoted_columns:\n  customer_email:\n    level: high\n"),
        "version: 2\nlevels: [high]\npromoted_event_params:\n  customer_email: high\n",
    ],
)
def test_version_specific_promotion_section_is_enforced(tmp_path: Path, content: str) -> None:
    with pytest.raises(ValueError, match="version"):
        YamlCatalogRepository(_write(tmp_path, content)).load()


def test_version_two_requires_promoted_column_level(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "version: 2\npromoted_columns:\n  customer_email:\n    source: {}\nlevels: [high]\n",
    )

    with pytest.raises(ValueError, match="promoted_columns.*level"):
        YamlCatalogRepository(path).load()


@pytest.mark.parametrize(
    "source_yaml",
    [
        "source: event_params",
        "source:\n      field_path: 42\n      key: primary_email",
        "source:\n      field_path: custom_attributes\n      key: [primary_email]",
    ],
)
def test_version_two_rejects_invalid_source_shapes(tmp_path: Path, source_yaml: str) -> None:
    path = _write(
        tmp_path,
        "version: 2\n"
        "levels: [high]\n"
        "promoted_columns:\n"
        "  customer_email:\n"
        "    level: high\n"
        f"    {source_yaml}\n",
    )

    with pytest.raises(ValueError, match="promoted_columns.*source"):
        YamlCatalogRepository(path).load()


def test_override_wins_after_loading(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "version: 1\nlevels: [high, medium]\ncolumns:\n  user_pseudo_id: medium\n"
        "overrides:\n  user_pseudo_id: high\n",
    )
    assert YamlCatalogRepository(path).load().effective_level("user_pseudo_id") == "high"


def test_missing_sections_default_to_empty(tmp_path: Path) -> None:
    catalog = YamlCatalogRepository(_write(tmp_path, "levels: [high]\n")).load()
    assert catalog.effective_level("anything") is None


def test_non_mapping_yaml_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="must be a YAML mapping"):
        YamlCatalogRepository(_write(tmp_path, "- just\n- a list\n")).load()


def test_missing_levels_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="must declare 'levels'"):
        YamlCatalogRepository(_write(tmp_path, "columns:\n  user_id: high\n")).load()


def test_unknown_level_value_is_rejected_by_the_domain(tmp_path: Path) -> None:
    path = _write(tmp_path, "levels: [high]\ncolumns:\n  user_id: critical\n")
    with pytest.raises(ValueError, match="not one of the declared levels"):
        YamlCatalogRepository(path).load()


def test_unsupported_version_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unsupported catalog version"):
        YamlCatalogRepository(_write(tmp_path, "version: 3\nlevels: [high]\n")).load()


@pytest.mark.parametrize("version", ["true", "2.0", "'2'"])
def test_non_integer_version_is_rejected(tmp_path: Path, version: str) -> None:
    with pytest.raises(ValueError, match="unsupported catalog version"):
        YamlCatalogRepository(_write(tmp_path, f"version: {version}\nlevels: [high]\n")).load()


def test_missing_file_propagates(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        YamlCatalogRepository(tmp_path / "nope.yml").load()
