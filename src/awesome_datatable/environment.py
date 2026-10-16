"""Registering the data table templates with a Jinja2 environment."""

from __future__ import annotations

from functools import partial
from pathlib import Path

from jinja2 import ChoiceLoader, Environment, FileSystemLoader

from .formatting import format_value

TEMPLATES_DIR = Path(__file__).parent / "templates"
# Holds datatable.js and datatable.css; the application serves it.
STATIC_DIR = Path(__file__).parent / "static"


def static_file_url(static_url: str, name: str) -> str:
    """Return the URL of a file of ``STATIC_DIR`` with its version.

    The URL carries ``?v=`` with the file's modification time, so a browser
    that kept an older copy of the file loads the new one once the package
    is updated (installing it again changes the time).

    Parameters
    ----------
    static_url : str
        URL where the application serves ``STATIC_DIR``, with or without a
        trailing ``/``.
    name : str
        Name of the file in ``STATIC_DIR``.

    Returns
    -------
    str
        ``<static_url>/<name>?v=<modification time in nanoseconds>``.
    """
    version = (STATIC_DIR / name).stat().st_mtime_ns
    return f"{static_url.rstrip('/')}/{name}?v={version}"


def configure_environment(environment: Environment, *, static_url: str) -> None:
    """Make the data table templates and filters available to an environment.

    The templates are found as ``datatable/<name>.html`` after the
    environment's own templates, and the ``dt_cell`` filter formats cell
    values with ``format_value``. The global ``dt_static_file_url`` gives the
    versioned URL of a file of ``STATIC_DIR`` under ``static_url``, which
    the ``assets`` macro uses.

    Parameters
    ----------
    environment : Environment
        Environment that renders the application's pages; it is changed in
        place.
    static_url : str
        URL where the application serves ``STATIC_DIR``, such as
        ``"/datatable"``, with or without a trailing ``/``. It has no
        default, so that it cannot differ from the application's mount
        unnoticed.
    """
    loader = FileSystemLoader(TEMPLATES_DIR)
    environment.loader = (
        loader if environment.loader is None else ChoiceLoader([environment.loader, loader])
    )
    environment.filters["dt_cell"] = format_value
    environment.globals["dt_static_file_url"] = partial(static_file_url, static_url)
