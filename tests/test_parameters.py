"""Tests that the parsers read parameters with ``getlist`` and mappings alike."""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence

import pytest

from flat_pca.webui.datatable import TableConfig, parse_export, parse_state
from flat_pca.webui.datatable.parameters import parameter_lists

QUERY = {
    "t.sort": ["score"],
    "t.order": ["desc"],
    "t.eq__group": ["a", "b"],
    "t.page": ["1", "2"],
    "t.min__count": ["2"],
}
EXPORT = {
    **QUERY,
    "t.export_format": ["parquet"],
    "t.export_rows": ["selected"],
    "keys": ['["k1", "k3"]'],
}


class LastValues(Mapping[str, str]):
    """Parameters shaped like Starlette's ``QueryParams``.

    As a mapping they hold the last value of each name; ``getlist`` gives
    every value.
    """

    def __init__(self, values: Mapping[str, Sequence[object]]) -> None:
        """Keep every value of each name."""
        self._values = {key: list(raw) for key, raw in values.items()}

    def __getitem__(self, key: str) -> str:
        """Return the last value of a name as text."""
        return str(self._values[key][-1])

    def __iter__(self) -> Iterator[str]:
        """Return an iterator over the names."""
        return iter(self._values)

    def __len__(self) -> int:
        """Return the number of names."""
        return len(self._values)

    def getlist(self, key: str) -> list[object]:
        """Return every value of a name."""
        return self._values.get(key, [])


class MultiValues:
    """Parameters shaped like werkzeug's ``MultiDict``: names and ``getlist`` only."""

    def __init__(self, values: Mapping[str, Sequence[object]]) -> None:
        """Keep every value of each name."""
        self._values = {key: list(raw) for key, raw in values.items()}

    def __iter__(self) -> Iterator[str]:
        """Return an iterator over the names."""
        return iter(self._values)

    def getlist(self, key: str) -> list[object]:
        """Return every value of a name."""
        return self._values.get(key, [])


class Text:
    """A value that is not a ``str`` but reads as one, like an uploaded file's name."""

    def __init__(self, text: str) -> None:
        """Keep the text."""
        self.text = text

    def __str__(self) -> str:
        """Return the text."""
        return self.text


@pytest.mark.parametrize("shape", [LastValues, MultiValues])
def test_parameter_lists_read_every_value_through_getlist(
    shape: type[LastValues | MultiValues],
) -> None:
    """``getlist`` comes first, so a mapping of the last values loses none."""
    assert parameter_lists(shape(QUERY)) == QUERY


def test_parameter_lists_read_values_as_text() -> None:
    """Values that are not ``str`` are converted with ``str``, in either shape."""
    values = {"t.q__name": [Text("alp")]}

    assert parameter_lists(MultiValues(values)) == {"t.q__name": ["alp"]}
    assert parameter_lists(values) == {"t.q__name": ["alp"]}  # type: ignore[arg-type]


@pytest.mark.parametrize("shape", [LastValues, MultiValues])
def test_parse_state_reads_getlist_like_a_mapping(
    config: TableConfig, shape: type[LastValues | MultiValues]
) -> None:
    """``parse_state`` gives the same state for both shapes."""
    assert parse_state(shape(QUERY), config) == parse_state(QUERY, config)
    assert parse_state(shape(QUERY), config).equals == {"group": ("a", "b")}


@pytest.mark.parametrize("shape", [LastValues, MultiValues])
def test_parse_export_reads_getlist_like_a_mapping(
    config: TableConfig, shape: type[LastValues | MultiValues]
) -> None:
    """``parse_export`` gives the same request for both shapes."""
    assert parse_export(shape(EXPORT), config) == parse_export(EXPORT, config)
    assert parse_export(shape(EXPORT), config).selected == ("k1", "k3")
