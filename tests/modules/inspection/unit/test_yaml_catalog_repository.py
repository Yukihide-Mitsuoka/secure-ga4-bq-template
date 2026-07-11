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
    assert catalog.overrides == {}


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
        YamlCatalogRepository(_write(tmp_path, "version: 2\nlevels: [high]\n")).load()


def test_missing_file_propagates(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        YamlCatalogRepository(tmp_path / "nope.yml").load()
