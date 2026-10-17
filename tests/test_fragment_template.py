"""Tests for the headers, menus, and rows of the ``fragment`` macro."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime

import polars as pl
import pytest
from html_tree import Element, Render
from jinja2 import Environment

from awesome_datatable import (
    ColumnConfig,
    TableConfig,
    TableState,
    apply_state,
    parse_state,
    summarize_table,
)


def _header(page: Element, column: str) -> Element:
    """Return the header cell of ``column``."""
    (cell,) = [cell for cell in page.select("th") if cell.select(f'button[data-dt-column="{column}"]')]
    return cell


def _head(page: Element, column: str) -> Element:
    """Return the name, sort mark, and filter mark of ``column`` in its header cell."""
    return _header(page, column).select_one(".dt-head")


def _menu(page: Element, column: str) -> Element:
    """Return the column menu of ``column``."""
    return page.select_one(f'div[data-dt-menu="{column}"]')


def _input(page: Element, name: str) -> Element:
    """Return the only input named ``name``."""
    return page.select_one(f'input[name="{name}"]')


def _values(elements: list[Element], name: str) -> list[str | None]:
    """Return attribute ``name`` of each element."""
    return [element[name] for element in elements]


def test_fragment_names_its_query_controls_by_the_parameter_names(
    environment: Environment, fragment: Render, config: TableConfig, frame: pl.DataFrame
) -> None:
    """Every query control of the fragment takes its name from ``dt_parameters``."""
    renamed = {key: f"x{name}" for key, name in environment.globals["dt_parameters"].items()}
    environment.globals["dt_parameters"] = renamed
    shown = replace(config, search=True, page_sizes=(5,))
    view = apply_state(frame, parse_state({}, shown), shown)

    page = fragment(shown, view)

    names = {element["name"] for element in page.select("[name]")}
    assert names
    assert all((name or "").startswith("t.x") for name in names)
    assert {"t.xsort", "t.xorder", "t.xabs", "t.xpage", "t.xpage_size", "t.xsearch"} <= names
    assert {"t.xq__name", "t.xeq__group", "t.xmin__count", "t.xmax__when", "t.xnull__name"} <= names


def test_fragment_shows_controls_rows_and_pages(fragment: Render, config: TableConfig, frame: pl.DataFrame) -> None:
    """The fragment names its controls by the table and marks the sort and selection."""
    state = parse_state({"t.sort": ["score"], "t.order": ["desc"], "t.eq__group": ["a"]}, config)
    view = apply_state(frame, state, config)

    page = fragment(config, view, selected={"k4"})

    hidden = page.select_one("[data-dt-part=\"state\"]").select('input[type="hidden"][data-dt-query]')
    assert [(element["name"], element["value"]) for element in hidden] == [
        ("t.sort", "score"), ("t.order", "desc"), ("t.abs", ""), ("t.page", "1")
    ]
    assert json.loads(page.select_one("script[data-dt-matching]").text) == ["k4", "k1"]
    assert _values(page.select("[aria-sort]"), "aria-sort") == ["descending"]
    assert page.select_one("[data-dt-check-all]")["aria-label"] == "Select all filtered rows"
    assert _input(page, "t.q__name")
    choices = page.select('input[name="t.eq__group"]')
    assert [(element["value"], "checked" in element) for element in choices] == [("a", True), ("b", False)]
    assert _input(page, "t.min__count")["type"] == "number"
    assert _input(page, "t.max__when")["type"] == "datetime-local"
    assert not page.select('[data-dt-sort="note"]')
    rows = page.select("tbody tr")
    assert _values(rows, "data-dt-key") == ["k4", "k1"]
    assert ["checked" in row.select_one("[data-dt-row-check]") for row in rows] == [True, False]
    first = rows[0].select("td")[1]
    assert (first.classes, first["title"], first.text) == (["dt-pinned"], "fourth", "k4")
    assert [cell.text for cell in rows[1].select("td")][-2] == "2026-01-01 00:00:00"
    assert page.select_one("[data-dt-page-range]").words == "1–2 of 2"
    assert not page.select("[data-dt-page]")


def test_fragment_opens_a_menu_from_each_column_name(
    fragment: Render, config: TableConfig, frame: pl.DataFrame
) -> None:
    """Each header holds its name, sort mark, and type; the controls are in its menu."""
    state = parse_state({"t.sort": ["count"], "t.order": ["asc"]}, config)
    view = apply_state(frame, state, config)

    page = fragment(config, view)

    for index, column in enumerate(config.columns, start=1):
        header = _header(page, column.name)
        menu = _menu(page, column.name)
        assert header.select_one("button.dt-column")["popovertarget"] == f"t-menu-{index}"
        assert header.select_one(".dt-label").text == column.header
        assert header.select_one(".dt-type").text == view.types[column.name]
        assert header.select("[data-dt-query]") == menu.select("[data-dt-query]")
        assert menu["id"] == f"t-menu-{index}"
        assert menu["aria-label"] == f"{column.header} menu"
        assert menu.select_one("[data-dt-copy]")["data-dt-copy"] == column.name
        assert bool(menu.select("[data-dt-sort]")) == column.sortable
        assert bool(menu.select(f'input[name="t.null__{column.name}"]')) == (column.filter is not None)
    assert _header(page, "when").select_one(".dt-type").text == "datetime[μs]"
    mark = _head(page, "count").select_one(".dt-sort-mark")
    assert (mark["data-dt-part"], mark.text) == ("sort-4", "▲")
    sorts = _menu(page, "count").select("[data-dt-order]")
    assert [(button["data-dt-order"], button["aria-pressed"]) for button in sorts] == [
        ("asc", "true"), ("desc", "false")
    ]
    assert "Clear sort" not in page.text
    absolute = _menu(page, "count").select_one("label.dt-sort-absolute")
    assert absolute.words == "Abs"
    assert "checked" not in absolute.select_one('input[data-dt-sort-absolute="count"]')


def test_fragment_offers_the_absolute_sort_of_numeric_columns(
    fragment: Render, config: TableConfig, frame: pl.DataFrame
) -> None:
    """Only numeric columns have Abs, checked on the column sorted by absolute values."""
    state = parse_state({"t.sort": ["score"], "t.order": ["desc"], "t.abs": ["1"]}, config)
    view = apply_state(frame, state, config)

    page = fragment(config, view)

    assert _input(page, "t.abs")["value"] == "1"
    assert "checked" in _menu(page, "score").select_one('[data-dt-sort-absolute="score"]')
    assert "checked" not in _menu(page, "count").select_one('[data-dt-sort-absolute="count"]')
    for name in ("key", "name", "group", "when", "note"):
        assert not _menu(page, name).select("[data-dt-sort-absolute]")


def _null_choice(menu: Element) -> tuple[str | None, str | None]:
    """Return the hidden null filter value of a menu and its pressed button's value."""
    hidden = menu.select_one("input[data-dt-null-value]")
    (pressed,) = menu.select('[data-dt-null][aria-pressed="true"]')
    return hidden["value"], pressed["data-dt-null"]


def test_fragment_draws_the_null_filter_as_a_segmented_control(
    fragment: Render, config: TableConfig, frame: pl.DataFrame
) -> None:
    """The null filter is a group of Any / Is null / Is not null buttons named by its label."""
    view = apply_state(frame, parse_state({"t.null__group": ["is_null"]}, config), config)

    page = fragment(config, view)

    group = _menu(page, "group")
    label = group.select_one(".dt-nulls-label")
    assert label.words.startswith("Null values")
    segmented = group.select_one(".dt-segmented")
    assert (segmented["role"], segmented["aria-labelledby"]) == ("group", label["id"])
    buttons = segmented.select("button[data-dt-null]")
    assert [(button["data-dt-null"], button["aria-pressed"], button.text) for button in buttons] == [
        ("", "false", "Any"), ("is_null", "true", "Is null"), ("is_not_null", "false", "Is not null")
    ]
    assert not page.select('input[type="radio"]')


def test_fragment_shows_choice_and_null_counts_and_filter_marks(
    fragment: Render, config: TableConfig, frame: pl.DataFrame
) -> None:
    """Menus count values and nulls; filtered columns carry a mark in the header."""
    state = parse_state(
        {"t.eq__group": ["b", "gone"], "t.null__when": ["is_not_null"], "t.q__name": ["a"]}, config
    )
    view = apply_state(frame, state, config, summarize_table(frame, config, {"group": ["a", "b"]}))

    page = fragment(config, view)

    group = _menu(page, "group")
    values = [
        (
            choice.select_one("input")["value"],
            "checked" in choice.select_one("input"),
            choice.select_one(".dt-choice-value").text,
            choice.select_one(".dt-count").text,
        )
        for choice in group.select(".dt-choices label.dt-choice")
    ]
    assert values == [("a", False, "a", "2"), ("b", True, "b", "1"), ("gone", True, "gone", "0")]
    assert group.select_one(".dt-nulls-label").words == "Null values 1"
    assert _null_choice(_menu(page, "when")) == ("is_not_null", "is_not_null")
    assert _null_choice(_menu(page, "count")) == ("", "")
    marked = [column.name for column in config.columns if _head(page, column.name).select("[data-dt-filtered]")]
    assert marked == ["name", "group", "when"]


def test_fragment_puts_a_search_above_the_values_of_a_choice_column(
    fragment: Render, config: TableConfig, frame: pl.DataFrame
) -> None:
    """A choice menu searches its values above the list; the search alone marks the column."""
    view = apply_state(frame, parse_state({"t.q__group": ["A"]}, config), config)

    page = fragment(config, view)

    group = _menu(page, "group")
    search = _input(group, "t.q__group")
    assert (search["type"], search["value"], search["aria-label"]) == ("text", "A", "Search group")
    assert search["id"] == "t-filter-q-3"
    assert "data-dt-query" in search
    assert "hx-preserve" in search
    assert search.position < group.select_one("fieldset.dt-choices").position
    assert _head(page, "group").select("[data-dt-filtered]")
    assert "disabled" not in group.select_one("[data-dt-clear-filter]")


def test_fragment_puts_the_values_of_a_choice_column_in_a_div_of_the_fieldset(
    fragment: Render, config: TableConfig, frame: pl.DataFrame
) -> None:
    """The values sit in a div of the fieldset, which Chrome parses fast however many they are."""
    view = apply_state(frame, parse_state({}, config), config)

    page = fragment(config, view)

    fieldset = _menu(page, "group").select_one("fieldset.dt-choices")
    legend, choices = (child for child in fieldset.children if isinstance(child, Element))
    assert legend.tag == "legend"
    assert (choices.tag, choices.classes) == ("div", ["dt-choice-list"])
    labels = [child for child in choices.children if isinstance(child, Element)]
    assert all(label.tag == "label" and label.classes == ["dt-choice"] for label in labels)
    assert _values(choices.select('input[name="t.eq__group"]'), "value") == ["a", "b"]


def test_fragment_puts_apply_cancel_and_clear_under_the_filters(
    fragment: Render, config: TableConfig, frame: pl.DataFrame
) -> None:
    """A menu with filters ends in Apply (disabled until a draft differs), Cancel, and Clear (disabled while unfiltered)."""
    state = parse_state({"t.eq__group": ["b"]}, config)
    view = apply_state(frame, state, config)

    page = fragment(config, view)

    for column in config.columns:
        menu = _menu(page, column.name)
        if column.filter is None:
            assert not menu.select("[data-dt-apply]")
            assert not menu.select("[data-dt-cancel]")
            assert not menu.select("[data-dt-clear-filter]")
            assert not menu.select("[data-dt-draft-status]")
            continue
        apply = menu.select_one("[data-dt-apply]")
        cancel = menu.select_one("[data-dt-cancel]")
        clear = menu.select_one("[data-dt-clear-filter]")
        assert (apply["title"], apply["aria-label"], "disabled" in apply) == ("Apply filters", "Apply filters", True)
        assert (cancel["title"], cancel["aria-label"], "disabled" in cancel) == ("Cancel", "Cancel", False)
        assert clear["aria-label"] == clear["title"] == "Clear the filters of this column"
        status = menu.select_one("[data-dt-draft-status]")
        assert ("hidden" in status, status.text) == (True, "Unapplied changes")
        assert menu.select_one("[data-dt-copy]").position < apply.position < cancel.position < clear.position
    assert "disabled" not in _menu(page, "group").select_one("[data-dt-clear-filter]")
    assert "disabled" in _menu(page, "when").select_one("[data-dt-clear-filter]")


def test_fragment_lists_the_rows_of_every_filter_for_the_header_checkbox(
    fragment: Render, config: TableConfig, frame: pl.DataFrame
) -> None:
    """The header checkbox gets every filtered row, beyond the shown page."""
    state = parse_state(
        {"t.eq__group": ["a", "b"], "t.null__count": ["is_not_null"], "t.q__name": ["A"]}, config
    )
    view = apply_state(frame, state, config)

    page = fragment(config, view)

    matching = page.select_one("script[data-dt-matching]")
    assert matching["type"] == "application/json"
    assert json.loads(matching.text) == ["k1", "k4"]


def test_fragment_of_a_plain_table_has_no_selection_state(fragment: Render, frame: pl.DataFrame) -> None:
    """A table without selection shows its shape but no count, and pins its first column."""
    config = TableConfig(
        table_id="p", key="key", columns=(ColumnConfig("key"), ColumnConfig("name")), url="/p"
    )
    view = apply_state(frame, TableState(), config)

    page = fragment(config, view)

    assert page.select_one("[data-dt-shape]").words == "4 rows, 2 columns"
    assert not page.select("[data-dt-selected-count]")
    assert not page.select("[data-dt-clear]")
    assert not page.select(".dt-check")
    assert [cell.tag for cell in page.select(".dt-pinned")] == ["th"] + ["td"] * 4
    assert all(cell.attrs == {"class": "dt-pinned"} for cell in page.select("td.dt-pinned"))
    assert [cell.text for cell in page.select("td.dt-pinned")] == ["k1", "k2", "k3", "k4"]


def test_fragment_pins_the_checkbox_and_first_columns(
    fragment: Render, config: TableConfig, frame: pl.DataFrame
) -> None:
    """The checkbox column and the first column are pinned in the header and every row."""
    view = apply_state(frame, TableState(sort_by="key"), config)

    page = fragment(config, view)

    check, first = page.select("thead th")[:2]
    assert check.classes == ["dt-check", "dt-pinned"]
    assert check.select("input[data-dt-check-all]")
    assert (first.classes, first["aria-sort"]) == (["dt-pinned"], "ascending")
    assert first.select('button[data-dt-column="key"]')
    for row in page.select("tbody tr"):
        cells = row.select("td")
        assert [cell.classes for cell in cells[:3]] == [["dt-check", "dt-pinned"], ["dt-pinned"], []]
        assert "title" in cells[1]
    assert len(page.select(".dt-pinned")) == 2 + 2 * 2


def test_fragment_row_checkboxes_use_the_matching_key_text(fragment: Render) -> None:
    """A datetime key has the same text in the row checkbox and the matching keys."""
    frame = pl.DataFrame({"when": [datetime.fromisoformat("2026-01-01")]})
    config = TableConfig(
        table_id="d", key="when", columns=(ColumnConfig("when"),), url="/", selectable=True
    )
    view = apply_state(frame, TableState(), config)

    page = fragment(config, view)

    (key,) = view.matching_keys
    (row,) = page.select("tbody tr")
    assert row["data-dt-key"] == key
    assert row.select_one("[data-dt-row-check]")["value"] == key


def test_fragment_has_a_resize_handle_on_every_column_header(
    fragment: Render, config: TableConfig, frame: pl.DataFrame
) -> None:
    """Each column header but the checkbox column's ends in a focusable handle naming its column."""
    view = apply_state(frame, TableState(), config)

    page = fragment(config, view)

    check, *headers = page.select("thead th")
    assert not check.select(".dt-resizer")
    for header, column in zip(headers, config.columns, strict=True):
        handle = [child for child in header.children if isinstance(child, Element)][-1]
        assert handle.classes == ["dt-resizer"]
        assert (handle["role"], handle["aria-orientation"]) == ("separator", "vertical")
        assert handle["aria-label"] == f"Resize column {column.header}"
        assert handle["tabindex"] == "0"
        assert handle["data-dt-resize"] == column.name


def _histogram(page: Element, column: str) -> Element:
    """Return the histogram (or top values) under the header of ``column``."""
    (histogram,) = _header(page, column).select("div.dt-histogram") + _header(page, column).select("ul.dt-top-values")
    return histogram


def test_fragment_draws_histograms_under_the_column_types(
    fragment: Render, config: TableConfig, frame: pl.DataFrame
) -> None:
    """Number and datetime headers get an SVG histogram; bins outside the bounds fade."""
    config = replace(config, histograms=True)
    state = parse_state({"t.min__count": ["2"]}, config)
    view = apply_state(frame, state, config)

    page = fragment(config, view)

    count = _histogram(page, "count")
    svg = count.select_one("svg")
    assert svg["viewbox"] == "0 0 30 32"
    assert svg["aria-label"] == "Histogram of count, 1 to 3"
    bins = count.select("g.dt-bin")
    assert [("dt-out" in group.classes, group.select_one("title").text) for group in bins] == [
        (True, "1: 1 row"), (False, "2: 1 row"), (False, "3: 1 row")
    ]
    bars = count.select("rect.dt-bin-bar")
    assert [(bar["y"], bar["width"], bar["height"]) for bar in bars] == [("0.00", "8", "32.00")] * 3
    assert [tick.text for tick in count.select(".dt-ticks span")] == ["1", "3"]
    when = _histogram(page, "when")
    titles = [title.text for title in when.select("g.dt-bin title")]
    assert len(titles) == 20
    assert titles[0] == "2026-01-01 00:00:00 – 2026-01-03 23:24:00: 1 row"
    assert any(title.endswith("0 rows") for title in titles)
    assert [tick.text for tick in when.select(".dt-ticks span")] == ["2026-01-01 00:00:00", "2026-03-01 12:00:00"]
    for column in ("key", "name", "group", "note"):
        assert not _header(page, column).select(".dt-histogram")


def test_fragment_shows_the_top_values_of_category_columns(
    fragment: Render, config: TableConfig, frame: pl.DataFrame
) -> None:
    """A categorical header lists its values with bars; unchecked values fade."""
    config = replace(config, histograms=True)
    frame = frame.with_columns(pl.col("group").cast(pl.Categorical))
    state = parse_state({"t.eq__group": ["b"]}, config)
    view = apply_state(frame, state, config)

    page = fragment(config, view)

    group = _histogram(page, "group")
    assert group["aria-label"] == "Most frequent values of group"
    values = [
        (
            "dt-out" in item.classes,
            item["title"],
            item.select_one(".dt-top-bar")["style"],
            item.select_one(".dt-top-label").text,
            item.select_one(".dt-count").text,
        )
        for item in group.select("li.dt-top-value")
    ]
    assert values == [(True, "a: 2 rows", "width: 100.0%", "a", "2"), (False, "b: 1 row", "width: 50.0%", "b", "1")]
    assert not group.select(".dt-top-others")


def test_fragment_counts_the_other_values_of_category_columns(fragment: Render) -> None:
    """Values past the five most frequent are counted together as Others."""
    config = TableConfig(
        table_id="t", key="key", columns=(ColumnConfig("lot"),), url="/t", histograms=True
    )
    lots = ["a", "a", "b", "c", "d", "e", "f", "g"]
    frame = pl.DataFrame(
        {"key": [str(i) for i in range(len(lots))], "lot": lots},
        schema_overrides={"lot": pl.Categorical},
    )
    view = apply_state(frame, TableState(), config)

    page = fragment(config, view)

    group = _histogram(page, "lot")
    assert len(group.select(".dt-top-bar")) == 5
    others = group.select_one("li.dt-top-others")
    assert others.classes == ["dt-top-value", "dt-top-others"]
    assert others["title"] == "Other values: 2 rows"
    assert (others.select_one(".dt-top-label").text, others.select_one(".dt-count").text) == ("Others", "2")
    assert not others.select(".dt-top-bar")


def test_fragment_without_histograms_draws_none(fragment: Render, config: TableConfig, frame: pl.DataFrame) -> None:
    """Histograms are off by default."""
    view = apply_state(frame, TableState(), config)

    page = fragment(config, view)

    assert not page.select(".dt-histogram")
    assert not page.select(".dt-top-values")


def test_fragment_marks_the_parts_that_a_reload_swaps(
    fragment: Render, config: TableConfig, frame: pl.DataFrame
) -> None:
    """Rows, footer, keys, marks, histograms, and chips are parts; the toolbar and menus are not."""
    config = replace(
        config, histograms=True, filter_chips=True, max_selected=3, export_url="/table/export"
    )
    view = apply_state(frame, TableState(), config)

    page = fragment(config, view)

    parts = _values(page.select("[data-dt-part]"), "data-dt-part")
    assert sorted(parts) == sorted(
        [
            "state", "chips", "matching", "limit", "rows", "footer", "export-filtered",
            *(f"sort-{index}" for index in range(1, 8)),
            *(f"sorts-{index}" for index in range(1, 7)),
            *(f"filtered-{index}" for index in range(1, 8)),
            *(f"clear-{index}" for index in range(2, 7)),
            *(f"histogram-{index}" for index in (4, 5, 6)),
        ]
    )
    assert len(parts) == len(set(parts))
    assert page.select_one('[data-dt-part="rows"]').tag == "tbody"


def test_fragment_of_the_parts_draws_only_the_swapped_parts(
    fragment: Render, config: TableConfig, frame: pl.DataFrame
) -> None:
    """With ``parts``, the same parts and headers come without the toolbar and the menus."""
    config = replace(
        config, histograms=True, filter_chips=True, max_selected=3, export_url="/table/export",
        search=True, column_chooser=True,
    )
    parameters = {"t.eq__group": ["a"], "t.sort": ["count"], "t.order": ["desc"]}
    whole = fragment(config, apply_state(frame, parse_state(parameters, config), config))
    view = apply_state(frame, parse_state({**parameters, "t.parts": ["1"]}, config), config)

    page = fragment(config, view, selected=["k1"])

    parts = _values(page.select("[data-dt-part]"), "data-dt-part")
    assert parts
    assert sorted(parts) == sorted(_values(whole.select("[data-dt-part]"), "data-dt-part"))
    assert len(page.select("th")) == len(whole.select("th"))
    assert _values(page.select("[aria-sort]"), "aria-sort") == ["descending"]
    assert not page.select("[data-dt-menu]")
    assert not page.select(".dt-toolbar")
    assert not page.select('[name="t.eq__group"]')
    assert page.select_one('[data-dt-part="rows"]').tag == "tbody"
    assert "checked" in page.select_one('tr[data-dt-key="k1"] [data-dt-row-check]')


@pytest.mark.parametrize("selectable", [True, False])
def test_fragment_draws_the_same_header_cells_with_and_without_parts(
    fragment: Render, config: TableConfig, frame: pl.DataFrame, selectable: bool
) -> None:
    """Both headers have a cell per column, after the checkbox cell of a selectable table."""
    config = replace(config, selectable=selectable)
    parameters = {"t.sort": ["count"], "t.order": ["desc"]}
    whole, parts = (
        fragment(config, apply_state(frame, parse_state(query, config), config)).select_one("thead")
        for query in (parameters, {**parameters, "t.parts": ["1"]})
    )

    cells = len(config.columns) + selectable
    assert len(whole.select("th")) == len(parts.select("th")) == cells
    assert _values(whole.select("[aria-sort]"), "aria-sort") == ["descending"]
    assert _values(parts.select("[aria-sort]"), "aria-sort") == ["descending"]
    assert bool(whole.select("[data-dt-check-all]")) is selectable
    assert not parts.select("[data-dt-check-all]")
    first = whole.select("th")[selectable]
    assert first.attrs == {"class": "dt-pinned"}


def test_choice_filter_names_only_the_choice_columns(
    fragment: Render, config: TableConfig, frame: pl.DataFrame
) -> None:
    """Only the checkboxes of a choice column carry the ``eq__`` parameter."""
    view = apply_state(frame, parse_state({}, config), config)

    page = fragment(config, view)

    names = {element["name"] for element in page.select("[name]")}
    assert {name for name in names if (name or "").startswith("t.eq__")} == {"t.eq__group"}
