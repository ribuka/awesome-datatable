"""A Starlette app serving one data table to the E2E tests.

It is only for the tests (the README's examples are separate): one page with
the table of ``demo_config`` over ``demo_frame``, its fragment route, its
export route, the package's static files, and the bundled htmx.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs

import polars as pl
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import HTMLResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from awesome_datatable import (
    STATIC_DIR,
    ColumnConfig,
    TableConfig,
    TableSummary,
    apply_state,
    configure_environment,
    export_file,
    parse_export,
    parse_state,
    summarize_table,
)

DEMO_DIR = Path(__file__).parent
TABLE_URL = "/files"
EXPORT_URL = "/files/export"
DATATABLE_STATIC_URL = "/datatable"


def demo_frame() -> pl.DataFrame:
    """Return the rows of the demo table, in the natural order of their keys.

    Returns
    -------
    pl.DataFrame
        Three files ``run-1``, ``run-2``, and ``run-10`` (``stem``, with their
        ``path``), the category ``lot`` (``A``, ``B``, null), the datetime
        ``date`` and the float ``yield_pct`` (both null for ``run-10``), and
        the integers ``n_steps``, ``n_segments``, and ``n_rows``.
    """
    return pl.DataFrame(
        {
            "stem": ["run-1", "run-2", "run-10"],
            "path": ["data/run-1.parquet", "data/run-2.parquet", "data/sub/run-10.parquet"],
            "lot": pl.Series(["A", "B", None], dtype=pl.Categorical()),
            "date": pl.Series(["2026-01-02 03:04:05", "2026-02-03 04:05:06", None]).str.to_datetime(
                "%Y-%m-%d %H:%M:%S", time_unit="us"
            ),
            "yield_pct": pl.Series([91.5, 88.0, None], dtype=pl.Float64()),
            "n_steps": [2, 2, 2],
            "n_segments": [3, 3, 3],
            "n_rows": [7, 7, 7],
        }
    )


def demo_config() -> TableConfig:
    """Return the settings of the demo table.

    Returns
    -------
    TableConfig
        The table ``files`` of seven columns (the key ``stem`` shown as
        ``file`` with its path as the tooltip, the filtered ``lot``,
        ``date``, and ``yield_pct``, and three integer columns), with
        selectable rows, the search, the filter chips, the "Columns" menu,
        the "Pin columns" toggle, the histograms, and the "Export" menu,
        100 rows per page.
    """
    return TableConfig(
        table_id="files",
        key="stem",
        columns=(
            ColumnConfig("stem", label="file", filter="text", frame_order=True, title_column="path"),
            ColumnConfig("lot", filter="choice"),
            ColumnConfig("date", filter="datetime"),
            ColumnConfig("yield_pct", filter="number"),
            ColumnConfig("n_steps", label="Steps"),
            ColumnConfig("n_segments", label="(Step, Sequence)s"),
            ColumnConfig("n_rows", label="rows"),
        ),
        url=TABLE_URL,
        page_size=100,
        page_sizes=(50, 100, 200, 500, 1000),
        selectable=True,
        selection_name="stems",
        select_all_label="Select all filtered files",
        default_sort="stem",
        search=True,
        filter_chips=True,
        column_chooser=True,
        pin_toggle=True,
        histograms=True,
        export_url=EXPORT_URL,
        export_name="catalog",
    )


def _templates(request: Request) -> Jinja2Templates:
    """Return the templates of the app serving a request."""
    return request.app.state.templates


def _config(request: Request) -> TableConfig:
    """Return the table settings of the app serving a request."""
    return request.app.state.config


def _summary(request: Request) -> TableSummary:
    """Return the summary of the demo frame for the app serving a request."""
    return request.app.state.summary


def page(request: Request) -> HTMLResponse:
    """Render the page holding the table with its first fragment.

    Parameters
    ----------
    request : Request
        Current request.

    Returns
    -------
    HTMLResponse
        The page, its table in the default state.
    """
    config = _config(request)
    view = apply_state(request.app.state.frame, parse_state({}, config), config, _summary(request))
    return _templates(request).TemplateResponse(
        request, "page.html", {"table": config, "view": view}
    )


def fragment(request: Request) -> HTMLResponse:
    """Render one state of the table, read from the query parameters.

    Parameters
    ----------
    request : Request
        Current request.

    Returns
    -------
    HTMLResponse
        The table's fragment.

    Raises
    ------
    HTTPException
        With status 400 if the query parameters are invalid.
    """
    config = _config(request)
    try:
        state = parse_state(request.query_params, config)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    view = apply_state(request.app.state.frame, state, config, _summary(request))
    return _templates(request).TemplateResponse(
        request, "fragment.html", {"table": config, "view": view}
    )


async def export(request: Request) -> Response:
    """Download the filtered or the selected rows of the table.

    Parameters
    ----------
    request : Request
        Current request, whose URL-encoded form body holds the export
        fields that ``datatable.js`` sends.

    Returns
    -------
    Response
        The file of ``export_file`` as an attachment.

    Raises
    ------
    HTTPException
        With status 400 if the form fields are invalid.
    """
    config = _config(request)
    form = parse_qs((await request.body()).decode(), keep_blank_values=True)
    try:
        parsed = parse_export(form, config)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    file = export_file(request.app.state.frame, parsed, config, datetime.now().astimezone())
    return Response(file.content, media_type=file.media_type, headers=file.headers)


def create_app(config: TableConfig) -> Starlette:
    """Create the demo app showing ``demo_frame`` with a table's settings.

    Parameters
    ----------
    config : TableConfig
        Settings of the table, ``demo_config`` or a variant of it.

    Returns
    -------
    Starlette
        The app serving the page at ``/``, the fragment at ``TABLE_URL``, the
        export at ``EXPORT_URL``, ``STATIC_DIR`` at ``DATATABLE_STATIC_URL``,
        and htmx under ``/static``.
    """
    templates = Jinja2Templates(directory=DEMO_DIR / "demo_templates")
    configure_environment(templates.env, static_url=DATATABLE_STATIC_URL)
    app = Starlette(
        routes=[
            Route("/", page),
            Route(TABLE_URL, fragment),
            Route(EXPORT_URL, export, methods=["POST"]),
            Mount(DATATABLE_STATIC_URL, StaticFiles(directory=STATIC_DIR)),
            Mount("/static", StaticFiles(directory=DEMO_DIR / "demo_static")),
        ]
    )
    frame = demo_frame()
    app.state.templates = templates
    app.state.config = config
    app.state.frame = frame
    app.state.summary = summarize_table(frame, config)
    return app
