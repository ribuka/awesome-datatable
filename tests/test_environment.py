"""Tests for configuring a Jinja2 environment and loading the static files."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from jinja2 import Environment, select_autoescape

from awesome_datatable import STATIC_DIR, configure_environment
from awesome_datatable import environment as environment_module


def _assets(static_url: str) -> str:
    """Render the ``assets`` macro in an environment configured with ``static_url``."""
    environment = Environment(autoescape=select_autoescape(["html"]))
    configure_environment(environment, static_url=static_url)
    template = environment.from_string('{% from "datatable/macros.html" import assets %}{{ assets() }}')
    return template.render()


def _version(name: str) -> int:
    """Return the version that a URL of a static file carries."""
    return (STATIC_DIR / name).stat().st_mtime_ns


@pytest.mark.parametrize("static_url", ["/datatable", "/datatable/"])
def test_assets_load_the_stylesheet_and_the_deferred_script(static_url: str) -> None:
    """``assets`` loads both files under ``static_url``, with or without its trailing slash."""
    assert _assets(static_url) == (
        f'<link rel="stylesheet" href="/datatable/datatable.css?v={_version("datatable.css")}">\n'
        f'<script src="/datatable/datatable.js?v={_version("datatable.js")}" defer></script>'
    )


def test_asset_urls_follow_the_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A file changed (as by installing the package again) gets another URL at the next page."""
    for name in ("datatable.css", "datatable.js"):
        (tmp_path / name).write_text("", encoding="utf-8")
    monkeypatch.setattr(environment_module, "STATIC_DIR", tmp_path)
    before = _assets("/datatable")

    css = tmp_path / "datatable.css"
    os.utime(css, ns=(css.stat().st_atime_ns, css.stat().st_mtime_ns + 1_000_000_000))

    after = _assets("/datatable")
    assert f'datatable.css?v={css.stat().st_mtime_ns}"' in after
    assert f'datatable.css?v={css.stat().st_mtime_ns}"' not in before
    assert after.splitlines()[1] == before.splitlines()[1]


def test_static_url_is_required() -> None:
    """Without ``static_url`` the environment is not configured."""
    with pytest.raises(TypeError):
        configure_environment(Environment())  # type: ignore[call-arg]


def test_static_url_is_keyword_only() -> None:
    """``static_url`` passed by position is a ``TypeError``."""
    with pytest.raises(TypeError):
        configure_environment(Environment(), "/datatable")  # type: ignore[misc]
