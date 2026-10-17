"""Tests for the element tree that the template tests read rendered HTML with."""

from __future__ import annotations

import pytest
from html_tree import Element, parse_html

HTML = """
<div id="a" class="box wide" data-x="1 2">
  <input type="checkbox" checked>
  <p class="note">One &amp; <b>two</b></p>
  <svg viewBox="0 0 1 1"><path d="M0 0"/></svg>
</div>
<p class="note" data-x="3">Three</p>
"""


def test_parse_html_keeps_attributes_text_and_order() -> None:
    """Void and self-closing elements have no children; references are unescaped; names are lowercase."""
    root = parse_html(HTML)

    box, outside = (child for child in root.children if isinstance(child, Element))
    assert (box.tag, box["id"], box.classes) == ("div", "a", ["box", "wide"])
    checkbox = box.select_one("input")
    assert checkbox.attrs == {"type": "checkbox", "checked": None}
    assert checkbox.children == []
    assert box.select_one("p").text == "One & two"
    assert box.select_one("svg")["viewbox"] == "0 0 1 1"
    assert box.select_one("path").children == []
    assert outside.words == "Three"
    assert box.position < checkbox.position < outside.position


def test_select_matches_tags_classes_ids_attributes_and_descendants() -> None:
    """A selector matches compound parts and descendants, in document order."""
    root = parse_html(HTML)

    assert [element.text for element in root.select("p.note")] == ["One & two", "Three"]
    assert [element.tag for element in root.select("#a .note b")] == ["b"]
    assert [element.tag for element in root.select("[data-x]")] == ["div", "p"]
    assert [element.tag for element in root.select('[data-x="1 2"] input[checked]')] == ["input"]
    assert root.select('[data-x="1"]') == []
    assert "checked" in root.select_one("input")


def test_select_one_needs_exactly_one_match() -> None:
    """``select_one`` fails on no match and on several matches."""
    root = parse_html(HTML)

    with pytest.raises(AssertionError):
        root.select_one("table")
    with pytest.raises(AssertionError):
        root.select_one("p")


def test_elements_are_equal_by_their_markup() -> None:
    """Elements with the same tag, attributes, and children are equal wherever they are."""
    first, second = parse_html('<b class="x">1</b><b class="x">1</b>').select("b")
    other = parse_html('<b class="y">1</b>').select_one("b")

    assert first == second
    assert first != other


@pytest.mark.parametrize("html", ["<div><p></div>", "<div>", "</p>"])
def test_parse_html_rejects_misnested_markup(html: str) -> None:
    """An end tag must close the innermost open element, and every element must be closed."""
    with pytest.raises(AssertionError):
        parse_html(html)
