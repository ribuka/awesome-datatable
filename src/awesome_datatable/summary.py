"""What a data table shows over every row, whatever its state."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import polars as pl

from .config import TableConfig
from .counts import ColumnCounts, count_values
from .formatting import dtype_label
from .histograms import ColumnHistogram, count_histograms


@dataclass(frozen=True)
class TableSummary:
    """The parts of a table view that depend only on the frame.

    The column menus and headers show them for every state alike, so an
    application whose frame changes seldom can make one per frame and pass
    it to ``apply_state`` for each request.

    Attributes
    ----------
    schema : dict[str, pl.DataType]
        Column types of the frame.
    options : dict[str, list[str]]
        Values offered by each ``"choice"`` filter.
    counts : ColumnCounts
        Rows of each value of the ``"choice"`` columns and null values of the
        filtered columns, over every row.
    types : dict[str, str]
        Type of each shown column (``dtype_label``), keyed by column name.
    histograms : dict[str, ColumnHistogram]
        Distribution of each shown column over every row
        (``count_histograms``, every bin in the filter); empty unless
        ``TableConfig.histograms``.
    """

    schema: dict[str, pl.DataType]
    options: dict[str, list[str]]
    counts: ColumnCounts
    types: dict[str, str]
    histograms: dict[str, ColumnHistogram]


def summarize_table(
    frame: pl.DataFrame | pl.LazyFrame,
    config: TableConfig,
    options: Mapping[str, Sequence[str]] | None = None,
) -> TableSummary:
    """Count what a table shows over every row of its frame.

    Parameters
    ----------
    frame : pl.DataFrame | pl.LazyFrame
        Every row of the table in its default order.
    config : TableConfig
        Table settings.
    options : Mapping[str, Sequence[str]] | None, default None
        Values offered by each ``"choice"`` filter; the sorted distinct
        values of the frame if ``None``. A given value missing from the frame
        counts 0.

    Returns
    -------
    TableSummary
        The column types, choices, counts, and (with
        ``TableConfig.histograms``) histograms of the frame. The frame is
        collected once for the counts (which also give the choices) and, with
        histograms, twice more.
    """
    schema = dict(frame.lazy().collect_schema())
    counts = count_values(frame, config)
    return TableSummary(
        schema=schema,
        options=(
            {name: sorted(counts.values[name]) for name in config.choice_columns}
            if options is None
            else {name: list(values) for name, values in options.items()}
        ),
        counts=counts,
        types={column.name: dtype_label(schema[column.name]) for column in config.columns},
        histograms=count_histograms(frame, config, schema) if config.histograms else {},
    )
