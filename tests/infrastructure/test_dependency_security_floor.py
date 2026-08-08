import tomllib
from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_cryptography_transitive_dependency_uses_the_patched_security_floor() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    constraints = project["tool"]["uv"]["constraint-dependencies"]
    cryptography = next(package for package in lock["package"] if package["name"] == "cryptography")

    assert "cryptography>=50.0.0" in constraints
    assert tuple(int(part) for part in cryptography["version"].split(".")) >= (50, 0, 0)
