"""Tests for the source of ``datatable.js``."""

from __future__ import annotations

import re

from awesome_datatable import STATIC_DIR


def test_script_names_no_query_parameter_itself() -> None:
    """datatable.js builds no ``<table_id>.<name>``; it reads the names from the container."""
    script = (STATIC_DIR / "datatable.js").read_text(encoding="utf-8")

    assert "${root.id}." not in script
    assert "root.dataset.dtParameters" in script


def test_script_listens_to_each_htmx_event_once() -> None:
    """datatable.js has one handler per htmx event, so their order is in the code."""
    script = (STATIC_DIR / "datatable.js").read_text(encoding="utf-8")
    events = re.findall(r'(?:listen|on|onTarget)\("(htmx:\w+)"', script)

    assert "htmx:beforeSwap" in events
    assert "htmx:afterRequest" in events
    assert len(events) == len(set(events))


def test_script_listens_on_the_document_in_one_place() -> None:
    """datatable.js adds its document listeners only in its dispatcher (``listen``)."""
    script = (STATIC_DIR / "datatable.js").read_text(encoding="utf-8")

    assert script.count("document.addEventListener(") == 1


def test_script_names_the_trigger_events_once() -> None:
    """datatable.js writes the names of its trigger events only in their constants."""
    script = (STATIC_DIR / "datatable.js").read_text(encoding="utf-8")

    assert script.count('"dt-reload"') == 1
    assert script.count('"dt-refresh"') == 1
