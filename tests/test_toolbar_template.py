"""Tests for the toolbar of the ``fragment`` macro and the ``export_button`` macro."""

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


def test_fragment_without_toolbar_settings_has_no_toolbar(
    fragment: Render, config: TableConfig, frame: pl.DataFrame
) -> None:
    """By default the table has no search box, "Columns" menu, or chips."""
    view = apply_state(frame, parse_state({"t.eq__group": ["a"]}, config), config)

    page = fragment(config, view)

    assert not page.select(".dt-toolbar")
    assert not page.select(".dt-chips")
    assert not page.select("[data-dt-columns-menu]")


def test_fragment_shows_the_search_box_with_the_search(
    fragment: Render, config: TableConfig, frame: pl.DataFrame
) -> None:
    """The search box of the whole table is a query control kept across reloads."""
    searchable = replace(config, search=True)
    view = apply_state(frame, parse_state({"t.search": ["alp"]}, searchable), searchable)

    page = fragment(searchable, view)

    search = page.select_one("#t-search")
    assert (search.tag, search["type"]) == ("input", "search")
    assert (search["name"], search["value"], search["aria-label"]) == ("t.search", "alp", "Search")
    assert "data-dt-query" in search
    assert "hx-preserve" in search
    assert search.position < page.select_one("table.dt-table").position


def test_fragment_puts_the_chips_above_the_search_box_and_the_buttons_at_its_right(
    fragment: Render, config: TableConfig, frame: pl.DataFrame
) -> None:
    """The chips come first, then the search box, then the group of Columns, Pin columns, and Export."""
    full = replace(
        config, search=True, filter_chips=True, column_chooser=True, pin_toggle=True, export_url="/table/export"
    )
    view = apply_state(frame, parse_state({"t.eq__group": ["a"]}, full), full)
    search_only = replace(config, search=True)

    page = fragment(full, view)
    plain = fragment(search_only, apply_state(frame, TableState(), search_only))

    toolbar = page.select_one("div.dt-toolbar")
    search, actions = (child for child in toolbar.children if isinstance(child, Element))
    assert page.select_one('[data-dt-part="chips"]').position < toolbar.position
    assert search["id"] == "t-search"
    assert actions.classes == ["dt-toolbar-actions"]
    buttons = [button for button in actions.children if isinstance(button, Element) and button.tag == "button"]
    assert [button.classes[0] for button in buttons] == ["dt-columns-button", "dt-pin-button", "dt-export-button"]
    assert not plain.select(".dt-toolbar-actions")


def test_fragment_lists_the_filters_in_use_as_chips(
    fragment: Render, config: TableConfig, frame: pl.DataFrame
) -> None:
    """Each chip has a button naming the parameters it clears; no filter, no chips."""
    chipped = replace(config, filter_chips=True)
    state = parse_state({"t.eq__group": ["a", "b"], "t.min__score": ["1"]}, chipped)

    page = fragment(chipped, apply_state(frame, state, chipped))
    unfiltered = fragment(chipped, apply_state(frame, TableState(), chipped))

    chips = [
        (
            chip.select_one(".dt-chip-label").text,
            chip.select_one("button")["aria-label"],
            chip.select_one("button")["data-dt-remove-filter"],
        )
        for chip in page.select("li.dt-chip")
    ]
    assert chips == [
        ("group ∈ {a, b}", "Remove filter group ∈ {a, b}", '["t.eq__group"]'),
        ("score ≥ 1", "Remove filter score ≥ 1", '["t.min__score", "t.max__score"]'),
    ]
    assert not unfiltered.select(".dt-chips")


def _columns_menu(page: Element) -> Element:
    """Return the "Columns" menu of table ``t``."""
    return page.select_one("div#t-columns-menu")


def test_fragment_has_a_columns_menu_of_every_column(
    fragment: Render, config: TableConfig, frame: pl.DataFrame
) -> None:
    """The "Columns" menu lists every column; the first one cannot be hidden."""
    chooser = replace(config, column_chooser=True)

    page = fragment(chooser, apply_state(frame, TableState(), chooser))

    assert page.select_one("button.dt-columns-button")["popovertarget"] == "t-columns-menu"
    menu = _columns_menu(page)
    assert "popover" in menu
    assert "data-dt-menu" in menu
    assert "data-dt-columns-menu" in menu
    boxes = menu.select('input[type="checkbox"][data-dt-show-column]')
    assert [(box["data-dt-show-column"], "checked" in box, "disabled" in box) for box in boxes] == [
        (column.name, True, index == 0) for index, column in enumerate(config.columns)
    ]
    assert menu.select(".dt-choice-value")[0].text == "Key"


def test_columns_menu_resets_the_column_widths(
    fragment: Render, config: TableConfig, frame: pl.DataFrame
) -> None:
    """The "Columns" menu ends with "Reset column widths", disabled until the browser enables it."""
    chooser = replace(config, column_chooser=True)
    view = apply_state(frame, TableState(), chooser)

    page = fragment(chooser, view)
    plain = fragment(config, view)

    menu = _columns_menu(page)
    reset = menu.select_one("button[data-dt-reset-widths]")
    assert (reset["type"], reset.text, "disabled" in reset) == ("button", "Reset column widths", True)
    assert reset.position > menu.select_one("fieldset").position
    assert not plain.select("[data-dt-reset-widths]")


def _export_menu(page: Element) -> Element:
    """Return the "Export" menu of table ``t``."""
    return page.select_one("div#t-export-menu")


def _export_buttons(menu: Element) -> list[tuple[str | None, str | None, bool]]:
    """Return the format, the rows, and whether it is disabled, of each export button."""
    return [
        (button["data-dt-export"], button["data-dt-export-rows"], "disabled" in button)
        for button in menu.select("button[data-dt-export]")
    ]


def test_fragment_has_an_export_menu_of_the_filtered_and_selected_rows(
    fragment: Render, config: TableConfig, frame: pl.DataFrame
) -> None:
    """The "Export" menu offers CSV and Parquet for the filtered and the selected rows."""
    exporting = replace(config, export_url="/table/export")
    view = apply_state(frame, parse_state({"t.eq__group": ["a"]}, exporting), exporting)

    page = fragment(exporting, view, selected={"k2", "k3", "k4"})

    assert page.select(".dt-toolbar")
    assert page.select_one("button.dt-export-button")["popovertarget"] == "t-export-menu"
    menu = _export_menu(page)
    assert "data-dt-menu" in menu
    assert "data-dt-export-menu" in menu
    assert _export_buttons(menu) == [
        ("csv", "filtered", False), ("parquet", "filtered", False), ("csv", "selected", False), ("parquet", "selected", False)
    ]
    filtered, selected = menu.select(".dt-export-label")
    assert filtered.words == "Filtered rows 2"
    assert selected.words == "Selected rows 3"
    assert "data-dt-export-selected-count" in selected.select_one(".dt-count")
    parquet = menu.select('button[data-dt-export="parquet"]')[-1]
    assert (parquet["aria-label"], parquet.text) == ("Export selected rows as Parquet", "Parquet")
    assert not menu.select("[disabled]")


def test_export_button_starts_with_the_download_icon(
    render: Render, fragment: Render, config: TableConfig, frame: pl.DataFrame
) -> None:
    """A table's "Export" button is ``export_button``: the package's SVG icon and the text."""
    exporting = replace(config, export_url="/table/export")

    page = fragment(exporting, apply_state(frame, TableState(), exporting))

    button = page.select_one("button.dt-export-button")
    assert button == render('{{ export_button("t-export-menu") }}').select_one("button")
    assert (button["popovertarget"], button["aria-haspopup"]) == ("t-export-menu", "dialog")
    svg, text = button.children
    assert isinstance(svg, Element)
    assert (svg.tag, svg["viewbox"], svg["width"], svg["height"], svg["aria-hidden"]) == (
        "svg", "0 0 16 16", "16", "16", "true"
    )
    assert svg.select_one("path")["stroke"] == "currentColor"
    assert text == "Export"


def test_export_button_opens_the_given_menu(render: Render) -> None:
    """``export_button`` opens the menu it names, also one outside a table."""
    (button,) = (child for child in render('{{ export_button("run-export-menu") }}').children if isinstance(child, Element))

    assert button.tag == "button"
    assert button.attrs == {
        "type": "button", "class": "dt-export-button", "popovertarget": "run-export-menu", "aria-haspopup": "dialog"
    }


def test_fragment_export_menu_disables_rows_without_any(
    fragment: Render, config: TableConfig, frame: pl.DataFrame
) -> None:
    """Without a matching or a selected row, its buttons are disabled."""
    exporting = replace(config, export_url="/table/export")
    view = apply_state(frame, TableState(), exporting)
    empty = apply_state(frame, parse_state({"t.eq__group": ["z"]}, exporting), exporting)

    menu = _export_menu(fragment(exporting, view))
    none_matching = _export_menu(fragment(exporting, empty, selected=["k1"]))

    assert [(rows, disabled) for _, rows, disabled in _export_buttons(menu)] == [
        ("filtered", False), ("filtered", False), ("selected", True), ("selected", True)
    ]
    assert [(rows, disabled) for _, rows, disabled in _export_buttons(none_matching)] == [
        ("filtered", True), ("filtered", True), ("selected", False), ("selected", False)
    ]


def test_fragment_of_a_plain_table_exports_only_the_filtered_rows(fragment: Render, frame: pl.DataFrame) -> None:
    """A table without selection has no selected rows to export."""
    plain = TableConfig(
        table_id="t", key="key", columns=(ColumnConfig("key"),), url="/t", export_url="/t/export"
    )

    menu = _export_menu(fragment(plain, apply_state(frame, TableState(), plain)))

    assert [rows for _, rows, _ in _export_buttons(menu)] == ["filtered", "filtered"]


def test_fragment_without_export_has_no_export_menu(
    fragment: Render, config: TableConfig, frame: pl.DataFrame
) -> None:
    """Export is off by default, for example in a dialog of chosen rows."""
    page = fragment(config, apply_state(frame, TableState(), config))

    assert "Export" not in page.text
    assert not any(name.startswith("data-dt-export") for element in page.iter() for name in element.attrs)


def test_fragment_has_a_pin_toggle_off_by_default(
    fragment: Render, config: TableConfig, frame: pl.DataFrame
) -> None:
    """The "Pin columns" toggle is a button, not pressed until the browser shows the choice."""
    pinnable = replace(config, pin_toggle=True)
    view = apply_state(frame, TableState(), pinnable)

    page = fragment(pinnable, view)
    plain = fragment(config, view)

    toggle = page.select_one("button[data-dt-pin-toggle]")
    assert (toggle["type"], toggle["aria-pressed"]) == ("button", "false")
    assert toggle.children[-1] == "Pin columns"
    assert toggle in page.select_one(".dt-toolbar").select("button")
    assert not plain.select("[data-dt-pin-toggle]")
