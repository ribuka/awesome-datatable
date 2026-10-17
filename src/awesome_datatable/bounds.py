"""Comparing a column with the lower and upper bounds of its filter."""

from __future__ import annotations

import math

import polars as pl

from .dtypes import integer_range
from .state import Bound


def bound_condition(name: str, bound: Bound, dtype: pl.DataType, *, lower: bool) -> pl.Expr:
    """Return the condition that a column is on the inner side of a bound.

    Parameters
    ----------
    name : str
        Column name.
    bound : Bound
        Bound from ``parse_state``; not ``None``.
    dtype : pl.DataType
        Type of the column.
    lower : bool
        Whether the bound is the lower one (``>=``) or the upper one (``<=``).

    Returns
    -------
    pl.Expr
        Inclusive comparison of the column with the bound. An ``int`` bound
        is compared exactly with an integer column: inside the column type's
        range, as a literal of that type; outside it, every non-null value is
        on the inner side of the bound or none is. Against other columns an
        ``int`` bound is compared as a float (``±inf`` past the float range).
    """
    column = pl.col(name)
    if isinstance(bound, int):
        if dtype.is_integer():
            smallest, largest = integer_range(dtype)
            if smallest <= bound <= largest:
                literal = pl.lit(bound, dtype=dtype)
            else:
                # Every value is above a bound below the type, and below one
                # above it; null values match no filter.
                return column.is_not_null() if (bound < smallest) == lower else pl.lit(False)
        else:
            try:
                literal = pl.lit(float(bound))
            except OverflowError:
                literal = pl.lit(math.inf if bound > 0 else -math.inf)
    else:
        literal = pl.lit(bound)
    return column >= literal if lower else column <= literal

