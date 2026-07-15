from __future__ import annotations

from src.modules.reporting.domain.model import CHECK_IDS
from src.modules.reporting.domain.remediation import REMEDIATION_RECIPES


def test_recipe_registry_covers_every_supported_check_once() -> None:
    assert set(REMEDIATION_RECIPES) == CHECK_IDS
    assert len({recipe.recipe_id for recipe in REMEDIATION_RECIPES.values()}) == len(CHECK_IDS)


def test_recipes_require_review_inputs_and_never_apply_or_destroy() -> None:
    for recipe in REMEDIATION_RECIPES.values():
        assert recipe.required_inputs
        assert recipe.validation_steps
        example = recipe.example or ""
        assert "terraform apply" not in example
        assert "terraform destroy" not in example


def test_chk12_recipe_is_manual_and_non_applying() -> None:
    recipe = REMEDIATION_RECIPES["CHK-12"]

    assert recipe.recipe_id == "MART_DESCRIPTION_V1"
    assert recipe.kind == "manual"
    assert recipe.example is None
