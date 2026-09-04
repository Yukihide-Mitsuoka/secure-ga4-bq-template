from pathlib import Path

from scripts.pr_repository_role import resolve_role

ROOT = Path(__file__).parents[2]


def test_secure_ga4_is_resolved_as_a_consumer_leaf() -> None:
    assert resolve_role(ROOT, "Yukihide-Mitsuoka/secure-ga4-bq-template") == "consumer"
