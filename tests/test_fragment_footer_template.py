"""Tests for the pages, the footer, and the selection limit of the ``fragment`` macro."""

from __future__ import annotations

from dataclasses import replace

import polars as pl
from html_tree import Element, Render

from awesome_datatable import (
    ColumnConfig,
    TableConfig,
    TableState,
    apply_state,
    parse_state,
)


def _page_button(page: Element, label: str) -> Element:
    """Return the pager button labelled ``label``."""
    return page.select_one(f'nav.dt-pager button[aria-label="{label}"]')


def test_fragment_moves_between_pages(fragment: Render, config: TableConfig, frame: pl.DataFrame) -> None:
    """Several pages have first, previous, next, last, and a page number input."""
    first = fragment(config, apply_state(frame, TableState(sort_by="key"), config))
    last = fragment(config, apply_state(frame, TableState(sort_by="key", page=2), config))

    assert first.select_one("[data-dt-page-range]").words == "1–2 of 4"
    buttons = [
        (button["aria-label"], button["data-dt-page"], "disabled" in button)
        for button in first.select("nav.dt-pager button[data-dt-page]")
    ]
    assert buttons == [
        ("First page", "1", True), ("Previous page", "0", True), ("Next page", "2", False), ("Last page", "2", False)
    ]
    jump = first.select_one(".dt-page-jump")
    number = jump.select_one("input[data-dt-page-input]")
    assert {name: number[name] for name in ("type", "min", "max", "step", "value", "aria-label")} == {
        "type": "number", "min": "1", "max": "2", "step": "1", "value": "1", "aria-label": "Page number"
    }
    assert number["data-dt-page-current"] == "1"
    assert jump.words == "Page of 2"
    assert last.select_one("[data-dt-page-range]").words == "3–4 of 4"
    assert "disabled" not in _page_button(last, "First page")
    assert "disabled" in _page_button(last, "Last page")
    assert last.select_one("input[data-dt-page-input]")["value"] == "2"


def test_fragment_of_one_page_has_no_page_controls(
    fragment: Render, config: TableConfig, frame: pl.DataFrame
) -> None:
    """One page shows only "a–b of N", and no rows "0 of 0"."""
    single = replace(config, page_size=10)
    every = apply_state(frame, TableState(), single)
    none = apply_state(frame, parse_state({"t.q__name": ["zzz"]}, single), single)

    one_page = fragment(single, every).select_one(".dt-footer")
    empty = fragment(single, none).select_one(".dt-footer")

    assert one_page.select_one("[data-dt-page-range]").words == "1–4 of 4"
    assert not one_page.select("[data-dt-page]")
    assert not one_page.select("[data-dt-page-input]")
    assert empty.select_one("[data-dt-page-range]").words == "0 of 0"
    assert empty.select_one("[data-dt-shape]").words == "0 rows, 7 columns"
    assert empty.select_one("[data-dt-column-count]").text == "7"


def test_fragment_footer_shows_the_shape_and_the_selection(
    fragment: Render, config: TableConfig, frame: pl.DataFrame
) -> None:
    """The footer has the matching rows and columns, the count, and Clear."""
    state = parse_state({"t.eq__group": ["a"]}, config)
    view = apply_state(frame, state, config)
    limited = replace(config, max_selected=3)

    some = fragment(config, view, selected=["k2", "k3"]).select_one(".dt-footer")
    none = fragment(config, view, selected=[]).select_one(".dt-footer")
    with_limit = fragment(limited, apply_state(frame, state, limited), selected=["k2", "k3"]).select_one(".dt-footer")

    shape = some.select_one("span.dt-shape[data-dt-shape]")
    assert shape.words == "2 rows, 7 columns"
    assert shape.select_one("span[data-dt-column-count]").text == "7"
    assert some.select_one("span.dt-selected-count[data-dt-selected-count]").text == "2 selected"
    clear = some.select_one("button[data-dt-clear]")
    assert (clear["type"], clear.text, "disabled" in clear) == ("button", "Clear", False)
    assert "disabled" in none.select_one("button[data-dt-clear]")
    assert none.select_one("[data-dt-selected-count]").text == "0 selected"
    assert with_limit.select_one("[data-dt-selected-count]").text == "2 / 3 selected"


def test_fragment_offers_the_rows_per_page(fragment: Render, config: TableConfig, frame: pl.DataFrame) -> None:
    """With page sizes, the footer chooses the rows per page and notes the first row shown."""
    choosing = replace(config, page_sizes=(3, 10))
    view = apply_state(frame, parse_state({"t.page_size": ["3"], "t.page": ["2"]}, choosing), choosing)

    footer = fragment(choosing, view).select_one(".dt-footer")
    plain = fragment(config, view)

    sizes = footer.select_one('select[name="t.page_size"]')
    assert "data-dt-query" in sizes
    assert "data-dt-page-size" in sizes
    assert [(option["value"], "selected" in option) for option in sizes.select("option")] == [
        ("2", False), ("3", True), ("10", False)
    ]
    page_range = footer.select_one("[data-dt-page-range]")
    assert (page_range["data-dt-start"], page_range.words) == ("4", "4–4 of 4")
    assert not plain.select("[data-dt-page-size]")


def _row_check(page: Element, key: str) -> Element:
    """Return the row checkbox of ``key``."""
    return page.select_one(f'input[type="checkbox"][value="{key}"]')


def _header_check(page: Element) -> Element:
    """Return the header checkbox."""
    return page.select_one("input[data-dt-check-all]")


def _limit_notice(page: Element) -> Element:
    """Return the limit notice."""
    return page.select_one("p[data-dt-limit]")


def test_fragment_without_limit_shows_no_limit_state(
    fragment: Render, config: TableConfig, frame: pl.DataFrame
) -> None:
    """A table without a limit has no notice and no disabled checkboxes."""
    view = apply_state(frame, TableState(sort_by="key"), config)

    page = fragment(config, view, selected={"k1"})

    assert not page.select("[data-dt-limit]")
    assert "disabled" not in _row_check(page, "k2")
    assert "disabled" not in _header_check(page)


def test_fragment_below_the_limit_allows_selecting(
    fragment: Render, config: TableConfig, frame: pl.DataFrame
) -> None:
    """Below the limit the rows can be checked and the notice is hidden."""
    limited = replace(config, max_selected=2)
    state = parse_state({"t.eq__group": ["b"]}, limited)
    view = apply_state(frame, state, limited)

    page = fragment(limited, view, selected=["k1"])

    notice = _limit_notice(page)
    assert "hidden" in notice
    assert notice.text.startswith("The limit of 2 selected rows is reached")
    assert "disabled" not in _row_check(page, "k2")
    assert "disabled" not in _header_check(page)


def test_fragment_at_the_limit_disables_unselected_rows(
    fragment: Render, config: TableConfig, frame: pl.DataFrame
) -> None:
    """At the limit unselected rows are disabled, selected ones not, and the notice shows."""
    limited = replace(config, max_selected=2)
    view = apply_state(frame, TableState(sort_by="key"), limited)

    page = fragment(limited, view, selected=["k1", "k3"])

    assert "hidden" not in _limit_notice(page)
    assert "checked" in _row_check(page, "k1")
    assert "disabled" not in _row_check(page, "k1")
    assert "disabled" in _row_check(page, "k2")
    assert "disabled" in _header_check(page)


def test_fragment_header_checkbox_follows_the_limit(
    fragment: Render, config: TableConfig, frame: pl.DataFrame
) -> None:
    """The header is disabled only when selecting every matching row passes the limit."""
    limited = replace(config, max_selected=3)
    every = apply_state(frame, TableState(sort_by="key"), limited)
    group_a = apply_state(frame, parse_state({"t.eq__group": ["a"]}, limited), limited)

    over = fragment(limited, every, selected=["k1"])
    fits = fragment(limited, group_a, selected=["k2"])
    all_selected = fragment(limited, group_a, selected=["k1", "k2", "k3", "k4"])

    assert "disabled" in _header_check(over)
    assert "disabled" not in _header_check(fits)
    assert "disabled" not in _header_check(all_selected)


def test_fragment_counts_keys_differing_only_in_case(fragment: Render) -> None:
    """Keys differing only in case count as separate rows against the limit."""
    frame = pl.DataFrame({"k": ["A", "a", "z"]})
    config = TableConfig(
        table_id="c", key="k", columns=(ColumnConfig("k"),), url="/", selectable=True, max_selected=2
    )
    view = apply_state(frame, TableState(), config)

    full = fragment(config, view, selected=["A", "a"])
    single = replace(config, max_selected=1)
    one = fragment(single, apply_state(frame.head(2), TableState(), single), selected=[])

    assert "hidden" not in _limit_notice(full)
    assert "disabled" in _row_check(full, "z")
    assert "disabled" in _header_check(one)
