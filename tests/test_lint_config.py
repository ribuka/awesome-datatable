"""Tests that ruff enforces the docstring and type hint rules of AGENTS.md."""

from __future__ import annotations

import tomllib
from pathlib import Path

PYPROJECT = Path(__file__).parents[1] / "pyproject.toml"
# Rule groups ruff must check besides its defaults: isort, pyupgrade,
# bugbear, pydocstyle, and annotations.
REQUIRED_RULES = {"I", "UP", "B", "D", "ANN"}


def _lint_settings() -> dict:
    """Return the ``[tool.ruff.lint]`` table of ``pyproject.toml``."""
    with PYPROJECT.open("rb") as file:
        return tomllib.load(file)["tool"]["ruff"]["lint"]


def test_ruff_selects_the_required_rules() -> None:
    """Ruff checks imports, upgrades, bugbear, docstrings, and type hints."""
    settings = _lint_settings()
    selected = set(settings.get("select", [])) | set(settings.get("extend-select", []))
    assert REQUIRED_RULES <= selected


def test_ruff_checks_numpy_docstrings() -> None:
    """Docstrings are checked against the NumPy convention."""
    assert _lint_settings()["pydocstyle"]["convention"] == "numpy"
