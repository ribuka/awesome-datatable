"""Tests that the data table's public API is its package and only what applications use."""

from __future__ import annotations

import awesome_datatable

PUBLIC_API = {
    # What applications use.
    "ColumnConfig",
    "TableConfig",
    "FilterKind",
    "TableState",
    "TableSummary",
    "TableView",
    "ExportFile",
    "ExportFormat",
    "STATIC_DIR",
    "MEDIA_TYPES",
    "configure_environment",
    "parse_state",
    "parse_export",
    "parse_selection",
    "apply_state",
    "summarize_table",
    "export_file",
    "export_filename",
    "file_content",
    "format_value",
    # Types of the arguments and results above and of the fields of TableView.
    "Page",
    "ColumnCounts",
    "ColumnHistogram",
    "Histogram",
    "HistogramBin",
    "TopValues",
    "TopValue",
    "FilterChip",
    "ExportRequest",
    "ExportRows",
    "RequestMethod",
    "NullFilter",
}


def test_all_is_the_public_api() -> None:
    """``__all__`` holds exactly what applications use and the types they meet."""
    assert set(awesome_datatable.__all__) == PUBLIC_API
    assert all(hasattr(awesome_datatable, name) for name in awesome_datatable.__all__)


def test_internals_are_not_exported() -> None:
    """The byte order mark and the templates directory stay inside the package."""
    assert not hasattr(awesome_datatable, "UTF8_BOM")
    assert not hasattr(awesome_datatable, "TEMPLATES_DIR")
