"""A polars table filtered, sorted, and paged on the server and shown with htmx.

The package depends only on polars and Jinja2 (and htmx in the browser), so
any web application can use it; see ``README.md`` for its use. Its public
API is what this module exports; the submodules are internal.
"""

from .chips import FilterChip
from .config import ColumnConfig, FilterKind, RequestMethod, TableConfig
from .counts import ColumnCounts
from .environment import STATIC_DIR, configure_environment
from .export import (
    MEDIA_TYPES,
    ExportFile,
    ExportFormat,
    ExportRequest,
    ExportRows,
    export_file,
    export_filename,
    file_content,
    parse_export,
    parse_selection,
)
from .formatting import format_value
from .histograms import ColumnHistogram, Histogram, HistogramBin, TopValue, TopValues
from .pagination import Page
from .query import TableView, apply_state
from .state import NullFilter, TableState, parse_state
from .summary import TableSummary, summarize_table

__all__ = [
    "MEDIA_TYPES",
    "STATIC_DIR",
    "ColumnConfig",
    "ColumnCounts",
    "ColumnHistogram",
    "ExportFile",
    "ExportFormat",
    "ExportRequest",
    "ExportRows",
    "FilterChip",
    "FilterKind",
    "Histogram",
    "HistogramBin",
    "NullFilter",
    "Page",
    "RequestMethod",
    "TableConfig",
    "TableState",
    "TableSummary",
    "TableView",
    "TopValue",
    "TopValues",
    "apply_state",
    "configure_environment",
    "export_file",
    "export_filename",
    "file_content",
    "format_value",
    "parse_export",
    "parse_selection",
    "parse_state",
    "summarize_table",
]
