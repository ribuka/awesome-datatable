"""Tests for what a data table counts over every row of its frame."""

from __future__ import annotations

from dataclasses import replace

import polars as pl
import pytest

from awesome_datatable import (
    TableConfig,
    TableState,
    apply_state,
    parse_state,
    summarize_table,
)
from awesome_datatable.counts import counts_by_value, value_counts
from awesome_datatable.histograms import count_histograms, mark_histograms


def test_summary_holds_the_types_choices_counts_and_histograms(
    frame: pl.DataFrame, config: TableConfig
) -> None:
    """The summary counts every row once, whatever the state."""
    config = replace(config, histograms=True)

    summary = summarize_table(frame, config)

    assert summary.schema == dict(frame.schema)
    assert summary.types["count"] == "i64"
    assert summary.options == {"group": ["a", "b"]}
    assert summary.counts.values == {"group": {"a": 2, "b": 1}}
    assert summary.counts.nulls["count"] == 1
    assert list(summary.histograms) == ["count", "score", "when"]
    assert all(b.in_filter for b in summary.histograms["count"].bins)


@pytest.mark.parametrize(("histograms", "collects"), [(False, 1), (True, 3)])
def test_summary_collects_the_frame_once_for_counts_and_choices(
    frame: pl.DataFrame,
    config: TableConfig,
    monkeypatch: pytest.MonkeyPatch,
    histograms: bool,
    collects: int,
) -> None:
    """The choices come from the counts; histograms add their own two queries."""
    config = replace(config, histograms=histograms)
    calls: list[pl.LazyFrame] = []
    collect = pl.LazyFrame.collect

    def counted(self: pl.LazyFrame, *args: object, **kwargs: object) -> pl.DataFrame:
        calls.append(self)
        return collect(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(pl.LazyFrame, "collect", counted)

    summary = summarize_table(frame.lazy(), config)

    assert len(calls) == collects
    assert summary.options == {"group": ["a", "b"]}


def test_apply_state_takes_the_menus_from_a_given_summary(
    frame: pl.DataFrame, config: TableConfig
) -> None:
    """A kept summary is used as it is, so the frame is not counted again."""
    config = replace(config, histograms=True)
    summary = summarize_table(frame, config, {"group": ("a", "b", "z")})
    state = parse_state({"t.min__count": ["3"]}, config)

    view = apply_state(frame.head(1), state, config, summary)

    assert view.page.total == 1
    assert view.options == {"group": ["a", "b", "z"]}
    assert view.counts == summary.counts
    assert view.types == summary.types
    assert view.histograms == mark_histograms(
        count_histograms(frame, config), state, frame.schema
    )


def test_marking_counted_histograms_fades_what_the_state_leaves_out(
    frame: pl.DataFrame, config: TableConfig
) -> None:
    """Counting once and marking each state fades the bins and values outside it."""
    state = parse_state(
        {"t.min__count": ["2"], "t.max__score": ["1"], "t.eq__group": ["a"]}, config
    )
    counted = count_histograms(frame, config)

    marked = mark_histograms(counted, state, frame.schema)

    assert list(marked) == list(counted)
    assert [b.in_filter for b in marked["count"].bins] == [False, True, True]
    assert mark_histograms(counted, TableState(), frame.schema) == counted


def test_apply_state_pages_by_the_chosen_page_size(
    frame: pl.DataFrame, config: TableConfig
) -> None:
    """A page size in the state replaces the table's."""
    config = replace(config, page_sizes=(3,))

    default = apply_state(frame, TableState(), config)
    chosen = apply_state(frame, parse_state({"t.page_size": ["3"]}, config), config)

    assert (default.page_size, default.page.count, len(default.rows)) == (2, 2, 2)
    assert (chosen.page_size, chosen.page.count, len(chosen.rows)) == (3, 2, 3)


def test_value_counts_count_the_non_null_values_as_text() -> None:
    """``counts_by_value`` reads back the rows of each value from ``value_counts``."""
    frame = pl.DataFrame({"n": [1, 2, 1, None]})

    pairs = frame.select(value_counts("n")).item().to_list()

    assert counts_by_value(pairs) == {"1": 2, "2": 1}
