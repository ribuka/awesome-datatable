"""Fixtures serving the demo app to a browser driven by Playwright."""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import Iterator
from contextlib import suppress
from dataclasses import replace

import pytest
import uvicorn
from demo_app import create_app, demo_config
from playwright.sync_api import ConsoleMessage, Error, Page, Route

from awesome_datatable import TableConfig

STARTUP_TIMEOUT_S = 30.0
SHUTDOWN_TIMEOUT_S = 30.0


@pytest.fixture
def table_config(request: pytest.FixtureRequest) -> TableConfig:
    """Return the settings of the demo app's table for a test.

    The closest ``table_config`` marker (of the test, else of its module)
    replaces fields of ``demo_config``, such as
    ``@pytest.mark.table_config(page_size=2, max_selected=2)``.

    Parameters
    ----------
    request : pytest.FixtureRequest
        Request of the test.

    Returns
    -------
    TableConfig
        ``demo_config`` with the marker's fields replaced.
    """
    marker = request.node.get_closest_marker("table_config")
    changes = {} if marker is None else marker.kwargs
    return replace(demo_config(), **changes)


@pytest.fixture
def server_url(table_config: TableConfig) -> Iterator[str]:
    """Serve the demo app with uvicorn in a background thread.

    The listening socket is bound before the server starts, so the port is
    reserved without a race.

    Parameters
    ----------
    table_config : TableConfig
        Settings of the served table.

    Yields
    ------
    str
        Base URL of the running server, whose page ``/`` shows the table;
        the server stops on exit.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(create_app(table_config), log_level="warning"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]})
    thread.start()
    try:
        deadline = time.monotonic() + STARTUP_TIMEOUT_S
        while not server.started:
            if not thread.is_alive() or time.monotonic() > deadline:
                pytest.fail("the demo app did not start")
            time.sleep(0.05)
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(SHUTDOWN_TIMEOUT_S)
        sock.close()


@pytest.fixture
def held_routes(page: Page) -> Iterator[list[Route]]:
    """Collect the routes a test holds, and pass on those left unhandled.

    Playwright keeps handling a held route until it is continued, fulfilled,
    aborted or passed on. A handling left pending is finished when the garbage
    collector closes it, possibly in a server thread, whose event loop then
    sends a message to the Playwright driver. That message races the Playwright
    event loop for the reply, so a reply can be lost and the session can hang.
    Each collected route is therefore passed on with ``fallback``, which does
    not fail even when the page has already aborted the request; a route the
    test has already handled is skipped.

    Parameters
    ----------
    page : Page
        Browser page of the test.

    Yields
    ------
    list[Route]
        Initially empty; the test appends the routes it holds.
    """
    routes: list[Route] = []
    yield routes
    for route in routes:
        # Raised only for a route that is already handled.
        with suppress(Error):
            route.fallback()


@pytest.fixture
def expected_console_errors() -> list[str]:
    """Return texts of console errors that a test expects to be logged.

    A test that makes a request fail on purpose appends a text contained in
    the error that the browser logs for it.

    Returns
    -------
    list[str]
        Initially empty.
    """
    return []


@pytest.fixture(autouse=True)
def no_console_errors(page: Page, expected_console_errors: list[str]) -> Iterator[None]:
    """Fail the test when the page logs an unexpected console error or throws.

    Console errors containing a text of ``expected_console_errors`` are
    allowed.

    Parameters
    ----------
    page : Page
        Browser page of the test.
    expected_console_errors : list[str]
        Texts of the allowed console errors.

    Yields
    ------
    None
        Control to the test; the collected errors are checked afterwards.
    """
    errors: list[str] = []

    def on_console(message: ConsoleMessage) -> None:
        """Record console messages of type ``error``."""
        if message.type == "error" and not any(
            text in message.text for text in expected_console_errors
        ):
            errors.append(f"console: {message.text} ({message.location['url']})")

    def on_page_error(error: Error) -> None:
        """Record uncaught exceptions."""
        errors.append(f"pageerror: {error.message}")

    page.on("console", on_console)
    page.on("pageerror", on_page_error)
    yield
    assert errors == []
