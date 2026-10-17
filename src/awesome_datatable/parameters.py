"""The request parameters that the parsers read, with every value of each name."""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from typing import Protocol, runtime_checkable


@runtime_checkable
class MultiValueParameters(Protocol):
    """Request parameters that hold every value of each name.

    Starlette's ``QueryParams`` and ``FormData`` and werkzeug's
    ``MultiDict`` have this shape; no web framework is imported.
    """

    def __iter__(self) -> Iterator[str]:
        """Return an iterator over the parameter names."""
        ...

    def getlist(self, key: str) -> Sequence[object]:
        """Return every value of one parameter name."""
        ...


type Parameters = MultiValueParameters | Mapping[str, Sequence[str]]


def parameter_lists(parameters: Parameters) -> dict[str, list[str]]:
    """Return every value of each request parameter as text.

    Parameters
    ----------
    parameters : Parameters
        Parameters with ``getlist`` (read through it first, since Starlette's
        ``QueryParams`` is also a ``Mapping[str, str]`` of the last values),
        or a mapping from each name to its values.

    Returns
    -------
    dict[str, list[str]]
        Every value of each name, each converted with ``str``.
    """
    if isinstance(parameters, MultiValueParameters):
        return {key: [str(value) for value in parameters.getlist(key)] for key in parameters}
    return {key: [str(value) for value in values] for key, values in parameters.items()}


def last_value(values: Sequence[str], default: str = "") -> str:
    """Return the last value of a parameter, which the parsers read.

    Parameters
    ----------
    values : Sequence[str]
        Every value of the parameter.
    default : str, optional
        Value returned for a parameter without any value.

    Returns
    -------
    str
        The last value, or ``default``.
    """
    return values[-1] if values else default


def last_choice[T: str](values: Sequence[str], allowed: tuple[T, ...], error: str) -> T:
    """Return the last value of a parameter that must be one of ``allowed``.

    Parameters
    ----------
    values : Sequence[str]
        Every value of the parameter; a missing one reads as ``""``.
    allowed : tuple[T, ...]
        Values it may have, stripped; include ``""`` to allow a blank one.
    error : str
        Start of the error message, followed by the value.

    Returns
    -------
    T
        The stripped value.

    Raises
    ------
    ValueError
        If the stripped value is not in ``allowed``.
    """
    text = last_value(values).strip()
    for value in allowed:
        if text == value:
            return value
    raise ValueError(f"{error}: {text!r}")
