"""Registering the data table templates with a Jinja2 environment."""

from __future__ import annotations

from pathlib import Path

from jinja2 import ChoiceLoader, Environment, FileSystemLoader

from .formatting import format_value

TEMPLATES_DIR = Path(__file__).parent / "templates"
# Holds datatable.js and datatable.css; the application serves it.
STATIC_DIR = Path(__file__).parent / "static"


def configure_environment(environment: Environment, export_icon: str = "") -> None:
    """Make the data table templates and filters available to an environment.

    The templates are found as ``datatable/<name>.html`` after the
    environment's own templates, and the ``dt_cell`` filter formats cell
    values with ``format_value``. The global ``dt_export_icon`` holds
    ``export_icon``.

    Parameters
    ----------
    environment : Environment
        Environment that renders the application's pages; it is changed in
        place.
    export_icon : str, default ""
        HTML of an icon put before the text of every table's "Export"
        button, such as an icon font's element (inserted as is, so it must be
        trusted markup); empty for none. The application draws it with its
        own icons, so the package depends on no icon set.
    """
    loader = FileSystemLoader(TEMPLATES_DIR)
    environment.loader = (
        loader if environment.loader is None else ChoiceLoader([environment.loader, loader])
    )
    environment.filters["dt_cell"] = format_value
    environment.globals["dt_export_icon"] = export_icon
