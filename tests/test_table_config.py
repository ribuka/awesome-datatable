"""Tests that the table settings take their fields by keyword."""

from __future__ import annotations

import pytest

from awesome_datatable import ColumnConfig, TableConfig


def test_column_config_takes_only_the_name_by_position() -> None:
    """``name`` may be positional; every other field is keyword-only."""
    assert ColumnConfig("lot", label="Lot").label == "Lot"
    assert ColumnConfig(name="lot").name == "lot"
    with pytest.raises(TypeError):
        ColumnConfig("lot", "Lot")  # type: ignore[misc]


def test_table_config_takes_every_field_by_keyword() -> None:
    """A positional field of ``TableConfig`` is a ``TypeError``."""
    columns = (ColumnConfig("key"),)

    assert TableConfig(table_id="t", key="key", columns=columns, url="/t").table_id == "t"
    with pytest.raises(TypeError):
        TableConfig("t", "key", columns, "/t")  # type: ignore[misc]


def test_table_config_names_its_query_parameters() -> None:
    """Every query parameter name of a table starts with ``<table_id>.``."""
    config = TableConfig(table_id="t", key="key", columns=(), url="/t")

    assert config.parameter("min__count") == "t.min__count"
    assert config.parameter_names == {
        "sort": "t.sort",
        "order": "t.order",
        "absolute": "t.abs",
        "page": "t.page",
        "page_size": "t.page_size",
        "search": "t.search",
        "parts": "t.parts",
        "export_format": "t.export_format",
        "export_rows": "t.export_rows",
        "text": "t.q__",
        "equals": "t.eq__",
        "min": "t.min__",
        "max": "t.max__",
        "null": "t.null__",
    }


def test_table_config_names_its_choice_columns_in_order() -> None:
    """``choice_columns`` lists the columns with a ``"choice"`` filter in order."""
    config = TableConfig(
        table_id="t",
        key="key",
        columns=(
            ColumnConfig("key"),
            ColumnConfig("grade", filter="choice"),
            ColumnConfig("note", filter="text"),
            ColumnConfig("lot", filter="choice"),
        ),
        url="/t",
    )

    assert config.choice_columns == ["grade", "lot"]
