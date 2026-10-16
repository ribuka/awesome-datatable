"""Tests that the data table's templates, stylesheet, and script load no external resource.

Only the places that load a URL are read (HTML ``src`` / ``href``
attributes, CSS ``url(...)`` and ``@import``, JS ``import`` and ``fetch``),
not every ``//`` of a file, which also starts a JS comment.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from flat_pca.webui.datatable import STATIC_DIR

PACKAGE_DIR = STATIC_DIR.parent
EXTERNAL = re.compile(r"\s*(?:https?:)?//", re.IGNORECASE)
PATTERNS = {
    ".html": (re.compile(r"""\b(?:src|href)\s*=\s*["']?([^"'\s>]*)""", re.IGNORECASE),),
    ".css": (
        re.compile(r"""\burl\(\s*["']?([^"')]*)""", re.IGNORECASE),
        # `@import url(...)` is read as a url() above.
        re.compile(r"""@import\s+["']([^"']*)""", re.IGNORECASE),
    ),
    ".js": (
        re.compile(r"""\bimport\s*\(\s*[`"']([^`"']*)"""),
        re.compile(r"""\bimport\s+[`"']([^`"']*)"""),
        re.compile(r"""\bfrom\s+[`"']([^`"']*)"""),
        re.compile(r"""\bfetch\s*\(\s*[`"']([^`"']*)"""),
    ),
}


def external_urls(text: str, suffix: str) -> list[str]:
    """Return the external URLs that a file's text loads.

    Parameters
    ----------
    text : str
        Text of a template (``.html``), a stylesheet (``.css``), or a script
        (``.js``).
    suffix : str
        The file's suffix, which chooses the places read.

    Returns
    -------
    list[str]
        The loaded URLs that start with ``http://``, ``https://``, or ``//``.
    """
    return [
        match.group(1)
        for pattern in PATTERNS[suffix]
        for match in pattern.finditer(text)
        if EXTERNAL.match(match.group(1))
    ]


def _package_files() -> list[Path]:
    """Return the templates, stylesheets, and scripts of the package."""
    return sorted(path for path in PACKAGE_DIR.rglob("*") if path.suffix in PATTERNS)


def test_package_has_templates_stylesheets_and_scripts() -> None:
    """Every kind of file read below is found."""
    assert {path.suffix for path in _package_files()} == set(PATTERNS)


@pytest.mark.parametrize("path", _package_files(), ids=lambda path: path.relative_to(PACKAGE_DIR).as_posix())
def test_file_loads_no_external_resource(path: Path) -> None:
    """No template, stylesheet, or script of the package loads a URL of another host."""
    assert external_urls(path.read_text(encoding="utf-8"), path.suffix) == []


@pytest.mark.parametrize(
    ("text", "suffix", "found"),
    [
        ('<script src="https://cdn.example.com/a.js"></script>', ".html", ["https://cdn.example.com/a.js"]),
        ("<link rel=stylesheet href=//cdn.example.com/a.css>", ".html", ["//cdn.example.com/a.css"]),
        ('<img src="http://example.com/a.png">', ".html", ["http://example.com/a.png"]),
        ('<a href="#top">top</a><use href="#icon"/>', ".html", []),
        ('@font-face { src: url("https://fonts.example.com/a.woff2"); }', ".css", ["https://fonts.example.com/a.woff2"]),
        ("@import url(//cdn.example.com/a.css);", ".css", ["//cdn.example.com/a.css"]),
        ('@import "https://cdn.example.com/a.css";', ".css", ["https://cdn.example.com/a.css"]),
        ('background: url("data:image/svg+xml,...");', ".css", []),
        ('import { a } from "https://cdn.example.com/a.js";', ".js", ["https://cdn.example.com/a.js"]),
        ('import "//cdn.example.com/a.js";', ".js", ["//cdn.example.com/a.js"]),
        ("await import(`https://cdn.example.com/a.js`);", ".js", ["https://cdn.example.com/a.js"]),
        ('fetch("https://api.example.com/rows");', ".js", ["https://api.example.com/rows"]),
        ("// A comment: see https://example.com\nfetch(url, { method: \"POST\" });", ".js", []),
    ],
)
def test_external_urls_finds_the_loaded_urls(text: str, suffix: str, found: list[str]) -> None:
    """The check finds a loaded external URL and ignores local URLs and comments."""
    assert external_urls(text, suffix) == found
