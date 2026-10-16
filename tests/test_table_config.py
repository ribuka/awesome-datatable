"""Tests that the table settings take their fields by keyword."""

from __future__ import annotations

import pytest

from flat_pca.webui.datatable import ColumnConfig, TableConfig


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
