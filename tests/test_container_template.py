"""Tests for the ``container`` macro rendered without a web framework."""

from __future__ import annotations

import json
from dataclasses import replace

import polars as pl
from html_tree import Element, Render

from awesome_datatable import ColumnConfig, TableConfig, TableState, apply_state


def test_container_loads_the_fragment_and_keeps_the_selection(render: Render, config: TableConfig) -> None:
    """The container reloads itself; the selection input sits outside it."""
    page = render(
        '{{ container(config, selected=["k1"], locked=true, triggers="data-changed from:body") }}',
        config=config,
    )

    container, selection = (child for child in page.children if isinstance(child, Element))
    assert container["id"] == "t"
    assert container["hx-get"] == "/table"
    assert container["hx-trigger"] == "load, dt-reload, dt-refresh, data-changed from:body"
    assert container["data-dt-selection"] == "t-selection"
    assert "data-dt-locked" in container
    assert selection.tag == "input"
    assert selection.attrs == {"type": "hidden", "id": "t-selection", "name": "keys", "value": '["k1"]'}


def test_container_posts_with_the_extra_inputs(render: Render) -> None:
    """A POST table loads its fragment with hx-post and names the inputs its requests send."""
    config = TableConfig(
        table_id="p", key="k", columns=(), url="/p", method="post", extra_inputs=("a", "b")
    )

    container = render("{{ container(config) }}", config=config).select_one("#p")

    assert container["hx-post"] == "/p"
    assert "hx-get" not in container
    assert container["data-dt-extra-inputs"] == "a b"


def test_container_names_the_columns_its_query_can_name(render: Render) -> None:
    """The container carries each column's name, filter, and sortability, for its kept query."""
    config = TableConfig(
        table_id="p",
        key="k",
        columns=(ColumnConfig("k", filter="text"), ColumnConfig("n", sortable=False)),
        url="/p",
    )

    container = render("{{ container(config) }}", config=config).select_one("#p")

    assert json.loads(container["data-dt-query-columns"] or "") == [["k", "text", True], ["n", None, False]]


def test_container_names_the_query_parameters_for_the_script(render: Render, config: TableConfig) -> None:
    """The container gives datatable.js every query parameter name of the table."""
    container = render("{{ container(config) }}", config=config).select_one("#t")

    assert json.loads(container["data-dt-parameters"] or "") == config.parameter_names


def test_container_of_a_plain_table_has_no_selection(render: Render) -> None:
    """A table without selection has no selection input."""
    config = TableConfig(table_id="p", key="k", columns=(), url="/p")

    page = render("{{ container(config) }}", config=config)

    container = page.select_one("#p")
    assert "data-dt-selection" not in container
    assert "data-dt-extra-inputs" not in container
    assert not page.select('input[type="hidden"]')


def test_container_carries_the_selection_limit(render: Render, config: TableConfig) -> None:
    """The container names the limit only when the table has one."""
    unlimited = render("{{ container(config) }}", config=config).select_one("#t")
    limited = render("{{ container(config) }}", config=replace(config, max_selected=2)).select_one("#t")

    assert "data-dt-max-selected" not in unlimited
    assert limited["data-dt-max-selected"] == "2"


def test_container_carries_the_export_url(render: Render, config: TableConfig) -> None:
    """A table with export names the URL that answers it; one without has none."""
    exported = render("{{ container(config) }}", config=replace(config, export_url="/table/export"))
    plain = render("{{ container(config) }}", config=config)

    assert exported.select_one("#t")["data-dt-export-url"] == "/table/export"
    assert "data-dt-export-url" not in plain.select_one("#t")


def test_container_carries_the_shared_pin_preference(render: Render, config: TableConfig) -> None:
    """A table sharing another table's "Pin columns" choice names that table; others name none."""
    shared = render("{{ container(config) }}", config=replace(config, pin_preference="files"))
    plain = render("{{ container(config) }}", config=config)

    assert shared.select_one("#t")["data-dt-pin-preference"] == "files"
    assert "data-dt-pin-preference" not in plain.select_one("#t")


def test_container_called_with_a_block_holds_it_and_does_not_load(
    render: Render, config: TableConfig, frame: pl.DataFrame
) -> None:
    """A container given its first fragment shows it and only reloads on later triggers."""
    view = apply_state(frame, TableState(), config)

    page = render(
        '{% call container(config, triggers="data-changed from:body") %}'
        "{{ fragment(config, view) }}{% endcall %}",
        config=config,
        view=view,
    )

    container = page.select_one("#t")
    assert container["hx-trigger"] == "dt-reload, dt-refresh, data-changed from:body"
    assert "Loading" not in page.text
    assert container.select('tr[data-dt-key="k1"]')
    assert not container.select("#t-selection")
    assert page.select_one("#t-selection")
