"""Fixtures of the data table tests: a small frame of every column type and its templates."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

import polars as pl
import pytest
from html_tree import Element, Render, parse_html
from jinja2 import Environment, select_autoescape

from awesome_datatable import (
    ColumnConfig,
    TableConfig,
    TableView,
    configure_environment,
)


@pytest.fixture
def frame() -> pl.DataFrame:
    """Return rows with text, category, integer, float, and datetime columns.

    Every column but ``key`` and ``name`` has a null value.
    """
    return pl.DataFrame(
        {
            "key": ["k1", "k2", "k3", "k4"],
            "name": ["Alpha", "beta", "Gamma", "alphabet"],
            "group": ["a", "b", None, "a"],
            "count": [3, None, 1, 2],
            "score": [0.5, 2.25, None, 1.0],
            "when": [
                datetime.fromisoformat("2026-01-01"),
                datetime.fromisoformat("2026-03-01T12:00"),
                datetime.fromisoformat("2026-02-01"),
                None,
            ],
            "note": ["first", None, "third", "fourth"],
        },
        schema_overrides={"count": pl.Int64},
    )


@pytest.fixture
def config() -> TableConfig:
    """Return a selectable table over every column of ``frame``."""
    return TableConfig(
        table_id="t",
        key="key",
        columns=(
            ColumnConfig("key", label="Key", frame_order=True, title_column="note"),
            ColumnConfig("name", filter="text"),
            ColumnConfig("group", filter="choice"),
            ColumnConfig("count", filter="number"),
            ColumnConfig("score", filter="number"),
            ColumnConfig("when", filter="datetime"),
            ColumnConfig("note", sortable=False),
        ),
        url="/table",
        page_size=2,
        selectable=True,
        selection_name="keys",
        default_sort="key",
    )


@pytest.fixture
def environment() -> Environment:
    """Return a bare Jinja2 environment with the data table templates."""
    environment = Environment(autoescape=select_autoescape(["html"]))
    configure_environment(environment, static_url="/datatable")
    return environment


@pytest.fixture
def render(environment: Environment) -> Render:
    """Return a function that renders one macro call of ``datatable/macros.html`` and parses it.

    The function takes the call, such as ``"{{ fragment(config, view) }}"``,
    and the template context as keyword arguments.
    """

    def render(call: str, **context: object) -> Element:
        """Render ``call`` with ``context`` and return the parsed HTML."""
        template = environment.from_string(
            '{% from "datatable/macros.html" import container, export_button, fragment %}' + call
        )
        return parse_html(template.render(**context))

    return render


@pytest.fixture
def fragment(render: Render) -> Render:
    """Return a function that renders ``fragment(config, view, selected)`` and parses it.

    The function takes the config, the view, and optionally the selected keys.
    """

    def fragment(config: TableConfig, view: TableView, selected: Iterable[str] = ()) -> Element:
        """Render the fragment of ``view`` with ``selected`` checked."""
        return render(
            "{{ fragment(config, view, selected=selected) }}", config=config, view=view, selected=selected
        )

    return fragment
