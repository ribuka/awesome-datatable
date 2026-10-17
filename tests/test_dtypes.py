"""Tests for the tables of the polars types."""

from __future__ import annotations

import polars as pl
import pytest

from awesome_datatable.dtypes import (
    INTEGER_BITS,
    SHORT_TYPE_NAMES,
    UNSIGNED_TYPES,
    integer_range,
    physical_type,
)


@pytest.mark.parametrize(
    ("dtype", "expected"),
    [
        (pl.Int8(), (-128, 127)),
        (pl.Int64(), (-(2**63), 2**63 - 1)),
        (pl.Int128(), (-(2**127), 2**127 - 1)),
        (pl.UInt8(), (0, 255)),
        (pl.UInt128(), (0, 2**128 - 1)),
    ],
)
def test_integer_range_is_the_inclusive_range_of_the_type(
    dtype: pl.DataType, expected: tuple[int, int]
) -> None:
    """The range of an integer type is what polars itself allows."""
    assert integer_range(dtype) == expected


def test_integer_bits_cover_every_integer_type() -> None:
    """Every polars integer type has a width, and it matches its range."""
    for kind, bits in INTEGER_BITS.items():
        dtype = kind()
        assert dtype.is_integer()
        smallest, largest = integer_range(dtype)
        assert pl.Series([smallest, largest], dtype=dtype).to_list() == [smallest, largest]
        assert largest - smallest == 2**bits - 1


def test_unsigned_types_hold_the_absolute_value_of_the_smallest_value() -> None:
    """Each signed type maps to the unsigned type of the same width."""
    assert set(UNSIGNED_TYPES) == {kind for kind in INTEGER_BITS if kind().is_signed_integer()}
    for signed, unsigned in UNSIGNED_TYPES.items():
        assert INTEGER_BITS[signed] == INTEGER_BITS[unsigned]
        assert -integer_range(signed())[0] == integer_range(unsigned())[1] // 2 + 1


def test_short_type_names_name_every_integer_type() -> None:
    """The column type labels cover every integer type."""
    assert set(INTEGER_BITS) <= set(SHORT_TYPE_NAMES)


@pytest.mark.parametrize(
    ("dtype", "expected"),
    [
        (pl.Date(), pl.Int32()),
        (pl.Datetime("ms"), pl.Int64()),
        (pl.Datetime("ns", "UTC"), pl.Int64()),
        (pl.Int16(), pl.Int16()),
        (pl.Float64(), pl.Float64()),
    ],
)
def test_physical_type_is_the_integer_type_of_dates_and_datetimes(
    dtype: pl.DataType, expected: pl.DataType
) -> None:
    """Dates and datetimes are stored as integers; other types are themselves."""
    assert physical_type(dtype) == expected
