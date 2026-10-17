"""Tables of the polars types: their widths, names, and related types."""

from __future__ import annotations

import polars as pl

# The width of each polars integer type.
INTEGER_BITS: dict[type[pl.DataType], int] = {
    pl.Int8: 8,
    pl.Int16: 16,
    pl.Int32: 32,
    pl.Int64: 64,
    pl.Int128: 128,
    pl.UInt8: 8,
    pl.UInt16: 16,
    pl.UInt32: 32,
    pl.UInt64: 64,
    pl.UInt128: 128,
}

# The unsigned type of each signed integer type, which holds the absolute value
# of its smallest value (``-128`` of ``pl.Int8`` is ``128`` of ``pl.UInt8``).
UNSIGNED_TYPES: dict[type[pl.DataType], type[pl.DataType]] = {
    pl.Int8: pl.UInt8,
    pl.Int16: pl.UInt16,
    pl.Int32: pl.UInt32,
    pl.Int64: pl.UInt64,
    pl.Int128: pl.UInt128,
}

# Short names of the polars types without parameters, as polars prints them
# over a frame's columns.
SHORT_TYPE_NAMES: dict[type[pl.DataType], str] = {
    pl.String: "str",
    pl.Categorical: "cat",
    pl.Enum: "enum",
    pl.Boolean: "bool",
    pl.Int8: "i8",
    pl.Int16: "i16",
    pl.Int32: "i32",
    pl.Int64: "i64",
    pl.Int128: "i128",
    pl.UInt8: "u8",
    pl.UInt16: "u16",
    pl.UInt32: "u32",
    pl.UInt64: "u64",
    pl.UInt128: "u128",
    pl.Float32: "f32",
    pl.Float64: "f64",
    pl.Date: "date",
    pl.Time: "time",
    pl.Binary: "binary",
    pl.Null: "null",
    pl.Object: "object",
}

# The integer type each temporal type with a histogram is stored as.
PHYSICAL_TYPES: dict[type[pl.DataType], type[pl.DataType]] = {
    pl.Date: pl.Int32,
    pl.Datetime: pl.Int64,
}


def integer_range(dtype: pl.DataType) -> tuple[int, int]:
    """Return the smallest and largest value of an integer type.

    Parameters
    ----------
    dtype : pl.DataType
        Integer type, signed or unsigned, of 8 to 128 bits.

    Returns
    -------
    tuple[int, int]
        Inclusive range of the type.
    """
    bits = INTEGER_BITS[dtype.base_type()]
    if dtype.is_signed_integer():
        return -(2 ** (bits - 1)), 2 ** (bits - 1) - 1
    return 0, 2**bits - 1


def physical_type(dtype: pl.DataType) -> pl.DataType:
    """Return the integer type a date or datetime column is stored as.

    Parameters
    ----------
    dtype : pl.DataType
        Polars type of the column.

    Returns
    -------
    pl.DataType
        ``pl.Int32`` for ``pl.Date``, ``pl.Int64`` for ``pl.Datetime``, and
        ``dtype`` itself for other types.
    """
    physical = PHYSICAL_TYPES.get(dtype.base_type())
    return dtype if physical is None else physical()
