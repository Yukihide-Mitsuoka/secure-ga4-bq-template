from __future__ import annotations

from src.modules.reporting.domain.model import CHECK_IDS
from src.modules.reporting.domain.remediation import REMEDIATION_RECIPES


def test_recipe_registry_covers_every_supported_check_once() -> None:
    assert set(REMEDIATION_RECIPES) == CHECK_IDS
    assert len({recipe.recipe_id for recipe in REMEDIATION_RECIPES.values()}) == len(CHECK_IDS)
