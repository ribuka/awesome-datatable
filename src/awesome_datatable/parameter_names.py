"""The names of a data table's query parameters, shared with its template and script.

A table's parameters are named ``<table_id>.<name>``
(``TableConfig.parameter``). The parsers read these names, the
``macros.html`` template gets them as the ``dt_parameters`` global
(``configure_environment``), and ``datatable.js`` reads them, prefixed, from
the container's ``data-dt-parameters`` (``TableConfig.parameter_names``).
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

SORT_PARAMETER = "sort"
ORDER_PARAMETER = "order"
ABSOLUTE_PARAMETER = "abs"
PAGE_PARAMETER = "page"
PAGE_SIZE_PARAMETER = "page_size"
SEARCH_PARAMETER = "search"
PARTS_PARAMETER = "parts"
EXPORT_FORMAT_PARAMETER = "export_format"
EXPORT_ROWS_PARAMETER = "export_rows"
# Prefixes of the column filters, followed by the column name.
TEXT_PREFIX = "q__"
EQUALS_PREFIX = "eq__"
MIN_PREFIX = "min__"
MAX_PREFIX = "max__"
NULL_PREFIX = "null__"

# Every parameter name or column filter prefix, without the table's prefix,
# by the key that the template and the script use.
PARAMETER_NAMES: Mapping[str, str] = MappingProxyType(
    {
        "sort": SORT_PARAMETER,
        "order": ORDER_PARAMETER,
        "absolute": ABSOLUTE_PARAMETER,
        "page": PAGE_PARAMETER,
        "page_size": PAGE_SIZE_PARAMETER,
        "search": SEARCH_PARAMETER,
        "parts": PARTS_PARAMETER,
        "export_format": EXPORT_FORMAT_PARAMETER,
        "export_rows": EXPORT_ROWS_PARAMETER,
        "text": TEXT_PREFIX,
        "equals": EQUALS_PREFIX,
        "min": MIN_PREFIX,
        "max": MAX_PREFIX,
        "null": NULL_PREFIX,
    }
)
