# awesome-datatable

A table of a polars `DataFrame` / `LazyFrame` that is filtered, sorted, and
paged on the server and shown with htmx.

- The package (`awesome_datatable`) imports only the standard library,
  polars, and Jinja2 (`tests/test_table_imports.py` checks this). It does not
  depend on a web framework, so any application that renders Jinja2
  templates can use it.
- In the browser it needs htmx (any 2.x) and `datatable.js` / `datatable.css`
  (the `assets` macro loads them).
- It loads no external resource: no script, stylesheet, font, icon, or image
  from a CDN or any other URL, so the tables work without a network. Its
  icons are inline SVG in the templates (drawn in `currentColor`); an icon or
  file added later is inline SVG or a file shipped in `static/`
  (`tests/test_no_external_resources.py` checks the `src` / `href`
  attributes, CSS `url(...)` and `@import`, and JS `import` and `fetch`).
- The examples below use FastAPI; any framework that serves static files
  and renders Jinja2 templates works the same way.

Update this document whenever the component gains a feature.

## Install

```sh
uv add "awesome-datatable @ git+https://github.com/ribuka/awesome-datatable.git"
```

## Development

```sh
uv sync
uv run -m ruff check .
uv run -m pytest
uv run -m pytest -m e2e -n logical   # browser tests (needs Chrome)
```

CI runs all three on every pull request to `main`; the browser tests run in
a job of their own (`e2e`).

Besides its default rules, ruff checks import order (`I`), pyupgrade (`UP`),
bugbear (`B`), NumPy-style docstrings (`D`), and type hints (`ANN`), as set in
`[tool.ruff.lint]` of `pyproject.toml` (`tests/test_lint_config.py`).

The browser tests (`tests/e2e/`, marked `e2e`, left out of a plain
`uv run -m pytest`) drive the installed Chrome with Playwright through
`datatable.js` and `datatable.css`. They use a demo app only for the tests
(`tests/e2e/demo_app.py`, Starlette): one page with a table of three files
and seven columns, its fragment and export routes, and htmx bundled in
`tests/e2e/demo_static/`. A test changes fields of the table's settings with
the `table_config` marker, such as
`@pytest.mark.table_config(page_size=2, max_selected=2)`. The development
dependencies (Starlette, uvicorn, Playwright, pytest-playwright,
pytest-xdist) are not dependencies of the package. Without Chrome installed,
run `uv run -m playwright install chrome` first.

## Layout

The paths are under `src/awesome_datatable/`.

| Path | Contents |
| --- | --- |
| `config.py` | `TableConfig` and `ColumnConfig`: what the application decides; `TableConfig.parameter` and `TableConfig.parameter_names` name the table's query parameters (`<table_id>.<name>`); `TableConfig.choice_columns` names the columns with a `"choice"` filter. |
| `state.py` | `TableState` and `parse_state`: query parameters → table state. |
| `query.py` | `apply_state`: table state + frame (+ its `TableSummary`) → `TableView` (rows of one page, the page and its size, matching keys, choices, counts, column types, filter chips, histograms); `matching_rows` (the filtered and sorted rows that the view and the export share), `filter_expression`, `search_columns`, and `search_terms`. A `LazyFrame` is collected only for the page's rows and for the matching keys (or their count). |
| `summary.py` | `TableSummary` and `summarize_table`: what the table shows over every row of the frame, whatever the state (column types, choices taken from the counts, counts, histograms), made once per frame; the frame is collected once for the counts and, with histograms, twice more. |
| `export.py` | `parse_export`: form fields → `ExportRequest`; `export_file`: the filtered or selected rows as an `ExportFile` (CSV or Parquet, its name and download headers); `export_rows`, `file_content`, `export_filename`, `parse_selection`. |
| `bounds.py` | `bound_condition`: a column compared with a lower or upper bound, exactly for integers. |
| `dtypes.py` | The tables of the polars types, in one place: `INTEGER_BITS` and `integer_range` (the width and range of each integer type, for `bounds.py`), `UNSIGNED_TYPES` (the unsigned type of each signed one, for the absolute sort in `query.py`), `SHORT_TYPE_NAMES` (the type names under the column names, for `formatting.py`), and `physical_type` (the integer type of a date or datetime, for `histograms.py`). |
| `histograms.py` | `count_histograms`: the distribution of each column under its name (`Histogram` of bins, or `TopValues`) over every row; `mark_histograms`: the bins and values a state's filters keep (`in_filter`); `integer_bins` and `float_bins`. |
| `chips.py` | `FilterChip` and `filter_chips`: the column filters in use as chips above the table. |
| `counts.py` | `ColumnCounts` and `count_values`: rows of each choice value and null values per filtered column, for the column menus; `value_counts` and `counts_by_value`: the rows of each value of a column as text, which `count_histograms` also uses for its top values. |
| `pagination.py` | `Page` and `paginate`: the page among the rows. |
| `formatting.py` | `format_value`: the cell text (`dt_cell` filter); `dtype_label`: the column type under each column name. |
| `parameter_names.py` | The query parameter names and column filter prefixes (`sort`, `q__`, and the others) and `PARAMETER_NAMES`, the one place that names them for the parsers, the templates (`dt_parameters`), and `datatable.js` (`data-dt-parameters`). |
| `parameters.py` | `parameter_lists`: request parameters (an object with `getlist`, or a mapping from each name to its values) → every value of each name as text, for `parse_state` and `parse_export`. |
| `environment.py` | `configure_environment`: registers the templates, the filter, and the versioned URLs of the static files (`dt_static_file_url`, under `static_url`), and the query parameter names (`dt_parameters`) with a Jinja2 environment; `STATIC_DIR`. |
| `templates/datatable/macros.html` | The `assets`, `container`, `fragment`, and `export_button` macros. |
| `static/datatable.js`, `static/datatable.css` | Browser behavior and look. `datatable.js` listens on the document once per event type and runs the handlers registered for that type in their order: `on` for an element in a table, found by its selector from the event's target, and `onTarget` for the event's own element, such as the container of an htmx event. |

## Use

The public API is what the package itself exports (`__all__` of
`__init__.py`): the settings, the parsers, `apply_state`,
`summarize_table`, the export functions, `configure_environment`,
`STATIC_DIR`, `MEDIA_TYPES`, `format_value`, and the types of their
arguments, results, and of the fields of `TableView`. Import them from the
package (`from awesome_datatable import ...`); the submodules are
internal and may change without notice, and only the package's own unit
tests import them.

1. Serve `STATIC_DIR` (with the web framework's own means) and configure
   the Jinja2 environment once with the URL it is served at, `static_url`
   (keyword-only and required, with or without a trailing `/`; a positional
   or missing one is a `TypeError`, so the URL never silently differs from
   the mount):

   ```python
   from awesome_datatable import STATIC_DIR, configure_environment

   app.mount("/datatable", StaticFiles(directory=STATIC_DIR), name="datatable")
   configure_environment(templates.env, static_url="/datatable")  # adds datatable/*.html and dt_cell
   ```

   Then load the stylesheet and the script in the page's `<head>` with the
   `assets` macro, before the page's own stylesheets (which may then set the
   `--dt-*` variables) and after htmx:

   ```jinja
   {% from "datatable/macros.html" import assets %}
   {{ assets() }}
   ```

   It writes a `<link rel="stylesheet">` and a `<script defer>`, each URL
   ending in `?v=` and the file's modification time, so a browser does not
   keep an older copy once the package is updated (installing it again
   changes the time). The application needs to know neither the names nor
   the number of the files. Being deferred, the script runs after the
   scripts in `<head>` that are not (htmx) and before deferred scripts and
   modules after it.

2. Describe the table. Every `TableConfig` argument and every
   `ColumnConfig` argument but `name` is keyword-only (a positional one is a
   `TypeError`), so that adding a setting never shifts the others:

   ```python
   config = TableConfig(
       table_id="files",              # container id, parameter prefix "files."
       key="stem",                    # row key; selections hold it as text
       columns=(
           ColumnConfig("stem", label="file", filter="text", frame_order=True,
                        title_column="path"),
           ColumnConfig("lot", filter="choice"),
           ColumnConfig("yield_pct", filter="number"),
           ColumnConfig("date", filter="datetime"),
           ColumnConfig("n_rows", label="rows"),   # sortable, no filter
       ),
       url="/catalog/files",          # returns the fragment
       method="get",                  # "post" sends the fields as a form body
       extra_inputs=(),               # ids of inputs outside the container sent too
       page_size=100,                 # rows per page at first
       page_sizes=(50, 200, 500),     # "Rows per page" choice; () for none
       selectable=True,
       selection_name="stems",        # name of the hidden selection input
       selection_form=None,           # its form attribute, if any
       select_all_label="Select all filtered files",
       default_sort="stem",
       max_selected=None,             # most selected rows; None for no limit
       search=True,                   # search box of the whole table
       filter_chips=True,             # chips of the filters in use
       column_chooser=True,           # "Columns" menu showing or hiding columns
       pin_toggle=True,               # "Pin columns" toggle pinning the left columns
       pin_preference=None,           # table id sharing its "Pin columns" choice
       histograms=True,               # distribution of each column in its header
       export_url="/catalog/files/export",  # "Export" menu; None for none
       export_name="catalog",         # exported files: catalog_<time>.csv
   )
   ```

3. Put the container in the page; it loads the fragment from `url`:

   ```jinja
   {% from "datatable/macros.html" import container %}
   {{ container(config, selected=selected, locked=false, triggers="catalog-updated from:body") }}
   ```

   `triggers` adds htmx triggers that reload the table. `locked` shows the
   selection with every checkbox disabled (the filters and pages still work).
   `selection_attributes` adds attributes to the hidden selection input, such
   as `{"data-changes": "..."}` for the form it joins (`selection_form`).
   To show the table without a second request, call the container with the
   first fragment (the view of `parse_state({}, config)`) as its block; it
   then does not load it again:

   ```jinja
   {% call container(config, selected=selected) %}{{ fragment(config, view, selected=selected) }}{% endcall %}
   ```

   Jinja2 macros cannot make their arguments keyword-only, so the macros
   keep this rule instead: a new argument is added at the end, and the order
   of the existing ones never changes. Callers pass every argument after
   the first by keyword (`selected=`, `locked=`, ...), except the `view` of
   `fragment`.

4. Answer the fragment request with a thin route:

   ```python
   try:
       state = parse_state(request.query_params, config)   # ValueError -> 400
   except ValueError as error:
       raise HTTPException(status_code=400, detail=str(error)) from error
   view = apply_state(frame, state, config, summary)  # frame: DataFrame or LazyFrame
   ```

   ```jinja
   {% from "datatable/macros.html" import fragment %}
   {{ fragment(config, view, selected=selected) }}
   ```

   `parse_state` and `parse_export` take the request's parameters as they
   are: any object whose `getlist` gives every value of a name, read through
   it first (Starlette's `QueryParams` and `FormData`, werkzeug's
   `MultiDict`; no web framework is imported), or a mapping from each name to
   its values (`parse_state({}, config)` for the first view, or tests). Each
   value is read as `str`.

   The frame is every row in its default order. `summary` is
   `summarize_table(frame, config, options)`: the column types, the choices
   of the `"choice"` filters (`options`, or without it the sorted distinct
   values of the frame), the counts beside them, the null counts, and the
   histograms, always over every row of the frame (not only the filtered
   ones); a given choice missing from the frame counts 0. None of it depends
   on the state, so keep the summary while the frame does not change, and
   only filtering, sorting, and paging run per request (for example, keep a
   frame and its summary in a cache until the data behind it changes).
   Without `summary`, `apply_state` makes it from the frame.

5. With `export_url`, answer the export (a form POST) with another thin route:

   ```python
   form = await request.form()
   try:
       export = parse_export(form, config)  # ValueError -> 400
   except ValueError as error:
       raise HTTPException(status_code=400, detail=str(error)) from error
   file = export_file(frame, export, config, datetime.now().astimezone())
   return Response(file.content, media_type=file.media_type, headers=file.headers)
   ```

   The fields are the table's query parameters (as for the fragment; `page`
   is ignored), `<table_id>.export_format` (`csv` or `parquet`),
   `<table_id>.export_rows` (`filtered` or `selected`), the selection
   input (`selection_name`, one JSON array), and the `extra_inputs`.
   `datatable.js` sends them.

6. To show other rows of the frame, such as the rows of keys chosen
   elsewhere in the page, keep what chooses them in inputs outside the
   container and name their ids in `extra_inputs`: every fragment request
   and the export send their names and values besides the table's query,
   and the routes read them and narrow the frame before `apply_state` and
   `export_file`. With `method="post"` the fragment requests are posts
   (`hx-post`), whose form body has no length limit (read the fields from
   `await request.form()`). After changing the inputs, dispatch
   `datatable:refresh` (bubbling) on the container: the whole fragment is
   loaded again from the first page with the applied query, so that the
   column menus show the values of the new rows.

7. A menu also works outside a table, such as an "Export" menu of the
   application's own. Put the button opening it and the menu in an element
   of class `dt-root` without `data-datatable` (which gives them the
   `--dt-*` variables and the look of the tables' buttons and menus), and
   open it with the `export_button` macro, or with any button whose
   `popovertarget` is the menu's `id`:

   ```jinja
   {% from "datatable/macros.html" import export_button %}
   <div class="dt-root">
     {{ export_button("run-export-menu") }}
     <div popover id="run-export-menu" class="dt-menu" role="dialog" aria-label="Export" data-dt-menu>
       <div class="dt-menu-section">...</div>
     </div>
   </div>
   ```

   - The menu is an element with `popover`, an `id`, and `data-dt-menu`
     (empty), of class `dt-menu`; the button opening it has
     `popovertarget` = that `id`. `export_button(menu_id)` draws the
     `Export` button of the tables (`.dt-export-button`: the download icon
     and `Export`, `aria-haspopup="dialog"`).
   - `datatable.js` places it as a column menu: under the button opening it,
     at its left edge, or above the button when there is no room below, and
     always at least 8 px inside the window; it follows the button while the
     page scrolls or the window resizes. It stays invisible until placed
     (`data-dt-placed`).
   - The browser closes it on a click outside it, and on Escape, after
     which the focus returns to its button; opening another menu closes it.
     The application closes it itself, when it is done, with
     `hidePopover()`.
   - Its contents are the application's: `.dt-menu-section` and the other
     menu classes give them the tables' look, and the application's own
     script handles its controls. Leave out the attributes that
     `datatable.js` handles inside a table (`data-dt-query`,
     `data-dt-export`, `data-dt-apply`, and the others of
     [Elements and classes](#elements-and-classes)).

## Columns

| `ColumnConfig` field | Meaning |
| --- | --- |
| `name` | Frame column. |
| `label` | Header text (default: `name`). |
| `filter` | `"text"` (a search: every whitespace-separated word as plain text, in any order and case), `"choice"` (the same search, above a list of values with their counts to check; a row must have any of the checked values), `"number"` / `"datetime"` (inclusive lower and upper bounds), or `None`. A column with a filter also has a null filter. Filters combine with AND. |
| `filter_label` | Accessible name of a text filter or of the value list of a choice filter (default: `Filter by <label>`). The search of a choice filter is named `Search <label>`; bounds are named `<label> lower` / `<label> upper`. |
| `sortable` | Whether the column menu sorts (default: `True`). Sorting puts nulls last and keeps the frame's order among ties. |
| `frame_order` | The frame's order is the column's ascending order (for example a key in natural order); sorting by it keeps or reverses the frame. |
| `title_column` | Frame column shown as the cell's tooltip. |

## Query parameters

Every parameter of a table is named `<table_id>.<name>`
(`TableConfig.parameter(name)`; `TableConfig.parameter_names` lists them all);
other parameters are ignored, so several tables can share a query string.
The names below are defined once in `parameter_names.py`, which the parsers,
the templates (`dt_parameters`), and `datatable.js` (`data-dt-parameters`)
share. `eq__<column>` is
repeated once per value; any other repeated parameter uses its last value.
Blank values are ignored. An unknown `<table_id>.*` parameter, a filter that
does not fit its column, or an unparsable value is a `ValueError`.

| Name | Value |
| --- | --- |
| `sort` | A sortable column (default: `default_sort`, or the frame's order). An empty value is the default. |
| `order` | `asc` (default) or `desc`. |
| `abs` | `1` sorts by the absolute values of the sort column (`TableState.absolute`), with null values last as in the plain sort; empty (default) sorts by the values. Only the columns of `absolute_sortable` (sortable, of a numeric type, not `frame_order`) use it; others ignore it. |
| `page` | 1-based page number; a page past the last shows the last. |
| `page_size` | Rows per page, one of `page_size_choices` (`page_sizes` and `page_size`; only with `page_sizes`); default `page_size`. |
| `parts` | `1` asks for only the parts that `datatable.js` swaps (`TableState.parts`): `fragment` then draws the `data-dt-part` elements and the headers' `aria-sort`, without the toolbar and the column menus. `datatable.js` sends it with its own reloads (`dt-reload`). |
| `search` | Search of the whole table (only with `search=True`): every whitespace-separated word, in any order, ignoring case, as plain text, must be in some shown `pl.String` column of the row (`search_columns`; each word in any of them). Other types, `title_column`, and columns of the frame that are not shown are not searched; nulls hold no word. |
| `q__<column>` | Search of a `"text"` or `"choice"` column: the value must contain every whitespace-separated word, in any order, ignoring case, as plain text (not a regular expression). `b01 lotA` matches `LotA_B01_run3`. |
| `eq__<column>` | A value of a `"choice"` column, repeated for several (`?t.eq__lot=A&t.eq__lot=B`); a row matches any of them (`is_in`). |
| `min__<column>`, `max__<column>` | Bounds of a `"number"` (an integer stays an `int` and is compared exactly with an integer column when it fits 64 bits; otherwise it is compared as a float, `±inf` past the float range) or `"datetime"` (ISO 8601, as `datetime-local` sends) column. |
| `null__<column>` | `is_null` (only the null values) or `is_not_null` (no null values) for any column with a filter. |

Null values never match a search, a value, or a bound, so setting one of
those already drops the nulls of the column: with `is_null` too, no row
matches, and `is_not_null` adds nothing. `is_null` alone lists the rows
without a value; `is_not_null` alone drops them.

The fragment carries these as inputs marked `data-dt-query` inside the
container; `datatable.js` puts their applied values in each request of the
container on `htmx:configRequest` (not htmx's `hx-include`, whose time grows
with the square of the inputs, and a column menu can hold thousands of
values). The table view, the
header checkbox's matching keys, the export, and anything else built on
`apply_state` filter and sort through the one `matching_rows`
(`filter_expression`, the search of the whole table included, and
`sort_frame`).

## Browser behavior and events

- Above the table, by the settings: the filter chips (`filter_chips`) on
  top, then a line (`.dt-toolbar`) with the search box, which fills the
  width left, and at its right end the `Columns`, `Pin columns`, and
  `Export` buttons (`.dt-toolbar-actions`).
  - `search`: a search box (`Search…`, named `Search`). Typing reloads the
    first page after 300 ms; the box keeps its text, focus, and caret across
    reloads (`hx-preserve`).
  - `column_chooser`: a `Columns` button opening a menu (a popover like the
    column menus) with a checkbox per column. Unchecking one hides its
    header and cells; the first column, which names the rows, is always
    shown. The hidden columns are kept in `localStorage` under
    `datatable:hidden-columns:<table_id>` (per browser and table id) and
    hidden again after every reload, before the rows are drawn, by a style
    sheet in the document head. Hidden columns still sort, filter, and are
    searched; the footer counts the shown columns. Without storage (a
    private window, for example) the choice lasts until the page is left.
  - `pin_toggle`: a `Pin columns` toggle button (`aria-pressed`, drawn as a
    switch) that pins the first column at the left, next to the checkbox
    column, while the table scrolls sideways (`position: sticky`,
    `.dt-pinned`); the header stays on top of them. The checkbox column of a
    selectable table stays at the left with or without the toggle. Pinning
    the first column is off until the toggle turns it on. Click, or Space /
    Enter on the focused button, switches it; it has no shortcut key of its
    own. The choice is kept in `localStorage` under
    `datatable:pinned-columns:<table_id>` (`true` or `false`; with
    `pin_preference`, under that table id instead, so that the table shares
    the choice of that table, and switching it updates every table in the page
    sharing the choice) and shown again
    after every reload (`data-dt-pinned` on the container, which the reloads
    keep, so the table does not jump). Without storage it lasts until the
    page is left, like the hidden columns. A table without the toggle pins
    only the checkbox column. Which columns are pinned is not configurable:
    the first column is the one naming the rows (such as the file name).
  - `filter_chips`: a chip per column filter in use, in column order:
    `name ~ "words"`, `lot ∈ {A, B}`, `temp ≥ 20` / `temp ≤ 30` /
    `20 ≤ temp ≤ 30` (both bounds are one chip), `lot is_null` /
    `lot is_not_null`. The column is named by its header. Its × button
    (named `Remove filter <chip>`) empties the search or bounds, unchecks the
    values, or sets the null filter back to Any, and reloads the first page.
    The search of the whole table has its box and no chip.
  - `export_url`: an `Export` button opening a menu (a popover like the
    column menus) with a `CSV` and a `Parquet` button for `Filtered rows`
    (every row matching the filters and the search, on all pages) and, in a
    selectable table, for `Selected rows` (every selected row, also those the
    filters hide), each with its row count; the buttons of rows without any
    are disabled, and the selected count follows the selection. A button
    posts the table's applied query (sort, search, and filters; not a draft
    in a column menu), the format, the rows, and the
    selection input's JSON array (one field, so the size of the selection is
    not bound by the limit on form fields) to `export_url` with `fetch`,
    and saves the answer under the name its `Content-Disposition` gives,
    then closes the menu. A failure shows `Export failed: <status>
    <reason>` (the JSON `detail` of the answer) in the menu, which stays
    open. The file holds the shown columns (`TableConfig.columns`, in display
    order, under their frame names; also those hidden by `Columns`, but not
    `title_column` or other frame columns) of those rows, in the table's sort
    order: a CSV in UTF-8 with a byte order mark (which Excel needs to read
    it as UTF-8), dates and datetimes in ISO 8601, and null as an empty
    field; or a Parquet file keeping the column types. It is named
    `<export_name>_<YYYYmmdd-HHMMSS>.csv` (or `.parquet`). Leave
    `export_url` unset where the rows need no export, such as a dialog
    choosing a few rows.
- Column widths (every table): the table has a fixed layout
  (`table-layout: fixed`), so the widths do not follow the values. Every
  column but the checkbox column (`--dt-check-width`) starts at
  `--dt-col-width`. A value (or a column name) wider than its column ends in
  `…`; with the pointer on it, its tooltip (`title`) shows it whole, except
  where the cell has the tooltip of `title_column`.
  - A thin line in the row lines' color (`--dt-border`) always separates
    the columns, in the header and the body; the last shown column has none
    (the table's box is its edge), and it is not doubled at the checkbox
    column or the pinned columns.
  - The right edge of each header is a handle (`[data-dt-resize]`, a
    focusable `separator` named `Resize column <label>`): on hover it shows
    the `col-resize` cursor; the column's line stays as it is on hover, on
    focus, and while dragged. Dragging it resizes the
    column, live while dragging; double-clicking it fits the column to its
    header (name and marks, type, histogram) and the values of the rows shown
    on the page; ←/→ while it is focused narrow or widen the column by 10 px.
    None of these opens the column menu, sorts, or selects a row.
  - A column is never narrower than `--dt-col-min-width` (by default the
    histogram's width plus the cell's left and right padding), and the
    handle never makes it narrower than `--dt-histogram-width` plus the
    cell's padding whatever the variable says, so the histogram and the
    column name's button (with its marks) stay in view; a narrow column
    shortens the name with `…`. The histograms keep their width
    (`--dt-histogram-width`) whatever the column's.
  - The widths set are kept in `localStorage` under
    `datatable:column-widths:<table_id>` (a JSON object of pixels by column
    name) and applied again after every reload (paging, filtering, sorting)
    before the rows are drawn, by a style sheet in the document head, like
    the hidden columns; without storage they last until the page is left.
  - `column_chooser` adds `Reset column widths` at the bottom of the
    `Columns` menu: it returns every column to `--dt-col-width` and forgets
    the widths. It is disabled while no column has a width of its own.
  - A resized pinned column stays pinned in place: the first column still
    starts after the checkbox column, and the columns right of it move with
    its width.
- Each header shows the column name, the sort mark (▲ / ▼), a funnel mark
  while a filter (values, bounds, search, or null filter) uses the column,
  and the column type under the name (`dtype_label`: polars' short names such
  as `str`, `cat`, `i64`, `f64`, `datetime[μs]`).
- `histograms`: under the type, the distribution of the column over every
  row of the frame (`count_histograms`), counted on the server and drawn
  without a script, so its shape stays the same while the filters change
  and reads as a base. Turn it off when every row of the frame is not a
  meaningful base (a table of rows the user chose, for example).
  - Integer (up to 64 bits), float, date, and datetime columns: an inline
    SVG histogram with the smallest and largest value under it. Integers,
    dates, and datetimes are binned by their integer value (a datetime in its
    time unit): one bin per value when the range has at most 20 values,
    otherwise at most 20 bins of `ceil(values / 20)` values. Floats get 20
    bins of equal width, half open but the last (one bin when every value is
    the same); NaN and infinite values are not counted. Bins that do not
    overlap the lower and upper bounds in use are faded (`dt-out`). Each bin's
    tooltip gives its first and last value and rows (`2 – 3: 4 rows`).
  - Categorical, enum, and boolean columns: the five most frequent values
    (ties by value) with bars as long as their rows relative to the first,
    and `Others` with the rows of the other values. Values not checked in
    the column's filter are faded. The search of a `"choice"` column fades
    nothing.
  - Nulls are not counted (the null filter shows them); a column without a
    non-null value, or of another type (text, for example), has none.
- Clicking the column name (or Enter / Space on it) opens the column menu,
  a popover (`popover`, `popovertarget`) holding the column's controls:
  sort (Asc, Desc, and, for a numeric column, an `Abs` checkbox), the filter (search, search above values
  with their counts, or lower and upper bounds), the null filter (a
  segmented control of the Any, Is null, and Is not null buttons, the chosen
  one `aria-pressed="true"`, with the null count; the choice is kept in the
  hidden query input `null__<column>`), "Copy column name" (the frame's
  column name), and under a column with filters the icon buttons `Apply` (a
  blue ✓, named `Apply filters`), `Cancel` (a gray ×), and `Clear` (a red
  trash can, named `Clear the filters of this column`), without a border or
  a background, each named by its `aria-label` and `title`. The buttons of a
  menu are a tenth lower than the page's. A click outside or Escape closes it and returns
  the focus to the column name; Tab moves from the name into the menu. The
  popover is in the top layer, so neither the scroll box nor a `<dialog>`
  clips it; `datatable.js` places it under the column name (above it, or
  shifted, when there is no room) and keeps it there while the page
  scrolls.
- The filters of a column menu (search, values, bounds, null filter) are a
  draft until applied: changing them reloads nothing.
  - While the draft differs from the applied filters, `Apply` is enabled
    (`data-dt-dirty` on the menu) and the menu shows `Unapplied changes`
    (a `status`) beside the buttons; otherwise `Apply` is disabled. A
    disabled button is faded.
  - `Apply`, or Enter in the search or a bound, reloads the first page once
    with the draft and closes the menu.
  - `Cancel`, Escape, a click outside, or opening another menu drops the
    draft and closes the menu; reopened, it shows the applied filters.
  - `Clear` removes every filter of the column (values, bounds, search, and
    null filter), reloads the first page, and closes the menu. It is
    disabled while the column has no filter applied.
  - A reload while a menu holds a draft (the search box or a page button
    reached with Tab, or a trigger of the page) sends the applied filters;
    the menu stays open with its draft, the focus (and caret) where they
    were. The header checkbox and the export use the applied filters too;
    a chip's × (reached with Tab) closes the menu, dropping the draft, and
    removes the applied filter.
- Sorting (Asc, Desc) and copying the name take effect at once
  and close the menu; Asc and Desc show the new sort mark and the pressed
  button before the rows arrive. There is no button back to the default
  order. While `Abs` is checked, Asc and Desc sort by the absolute values
  (`abs`); the box shows whether the column is sorted so. Checking or
  unchecking it on the sorted column sorts it again in the same direction
  and closes the menu; on another column it waits for Asc or Desc. The
  paging, the reloads, and the export keep the absolute sort, like the
  sort and its order. Outside the column menus, the search box of the whole
  table (after 300 ms), a chip's ×, and the `Columns` menu also take effect
  without Apply. Sorting or filtering returns to the first page. Reloads trigger
  `dt-reload` on the container.
- A reload of the table's own (`dt-reload`: sorting, filtering, paging, the
  search box, a chip, the rows per page) swaps only the parts of the fragment
  that change, marked `data-dt-part` (the rows, the footer, the matching
  keys, the sort and filter marks, the histograms, the sort buttons and
  `Clear` of the menus, the filtered count of `Export`, the chips, the limit
  notice, and the hidden sort / order / abs / page inputs), and the `aria-sort` of
  the headers. `datatable.js` swaps them itself from the response, so htmx
  neither cleans up nor processes the old and new rows, and the toolbar, the
  menus (an open one keeps its draft and focus), and the header cells stay.
  A focused control of a swapped part (a page button, for example) is
  focused again in the new part. The new rows show from the top of the
  scroll box (the sideways scroll stays); after a change of the rows per
  page, the row that began the page shown is at the top, under the header.
  These reloads ask for the parts only (`parts=1`), so the toolbar and the
  column menus (with every value of the `"choice"` filters) are neither
  drawn on the server nor sent and parsed again. A response whose parts do
  not fit the table (columns changed since) loads the whole fragment instead
  (`dt-refresh` on the container). A reload triggered by the page
  (`triggers`, such as a catalog update) swaps the whole fragment with htmx.
- The applied query (sort, order, absolute sort, page, rows per page, search,
  and filters) is kept in `sessionStorage` under
  `datatable:query:<path>#<table_id>` (per tab, page path, and table id)
  after each request of the table succeeds, with the columns of
  `TableConfig.query_columns` (`data-dt-query-columns`). A table shows the
  kept query again when the page is opened anew in that tab: a container
  that loads its first fragment (`load`, `intersect once`) asks for it at
  once, and a table drawn with the page loads it with `dt-refresh` (on
  `DOMContentLoaded`, before the page's scripts run on `pageshow`, or on
  `htmx:load` for a table put in the page later), or, while it sits in a
  `[hidden]` element, with its first whole load. While the columns differ
  from the kept ones, only the rows per page and the search are asked for. A
  failed request of the kept query forgets it and loads the table again
  with its applied query. Without storage the query lasts until the page is
  left.
- A table drawn with the page (the container called with its first
  fragment) gets the remembered hidden columns, pinning, and column widths
  and shows the selection as soon as `datatable.js` runs, and one that htmx
  puts in the page later on its `htmx:load`, as a whole swap does.
- While a reload is pending, the container has `aria-busy="true"` (set
  already in the click or key that reloads it) and `htmx-request`: after 0.1 s the rows fade and a spinner turns over the
  table, which keeps its height. Before the first fragment arrives, the
  spinner turns beside the container's "Loading…" (`.dt-loading`) instead.
  Both end with the request, also when it fails or is aborted.
  The spinner makes one turn in `--dt-spin-duration` (0.8 s); with
  `prefers-reduced-motion: reduce` it turns more slowly (1.6 s) instead of
  stopping, since a still spinner looks like a hung page.
- The values of a choice filter sit in a `<div>` (`.dt-choice-list`)
  inside the menu's `<fieldset class="dt-choices">`, not directly in it:
  Chrome parses a `<fieldset>` with many children in time quadratic in
  their number (20,000 values took 11 s; in a `<div>`, 0.1 s).
- Under the table, the footer shows "N rows, M columns" (the rows matching
  the filters and the shown columns), for a selectable table the selection
  count ("k selected", or "k / max selected" with `max_selected`) and Clear
  (which clears the whole selection, on every page and filter), "a–b of N",
  and with several pages the page controls: first, previous, next, and last
  page buttons around a page number input. Enter or leaving the input goes
  to the typed page (kept between 1 and the last page); a blank or invalid
  value puts the current page back. The number of rows per page is
  `page_size`; with `page_sizes`, `Rows per page` (a `select`) after the page
  controls chooses it among `page_size_choices` and reloads the page holding
  the first row shown. The choice is kept with the query (see above).
- The selection of a selectable table spans pages and filters. It is a JSON
  array in the hidden input `#<table_id>-selection` (named `selection_name`),
  outside the reloaded fragment, so a form or `hx-include` can send it as one
  field. Keys are the key column cast to polars `String` (`key_text`) for the
  row checkboxes, the header checkbox, and the selection alike, so keys of any
  type match; give the initial selection in the same form. A table without
  selection does not cast its keys (`data-dt-key` is `str()` of the value).
  The header checkbox selects or clears every row matching the applied
  filters (not a draft in a column menu) and shows all / some / none. A
  click anywhere in its cell toggles it once; while it is disabled (past the
  limit, or a locked table) a click in the cell does nothing.
- A click anywhere on a row toggles its checkbox, once (a click on the
  checkbox itself is not counted twice). Clicks on a link or another control
  in the row (`a`, `button`, `input`, `select`, `textarea`, `label`,
  `summary`, `[contenteditable]`, `[tabindex]`) and the end of a drag that
  selects text change nothing, and neither does a click on a row whose
  checkbox is disabled (every row of a locked table, and the unselected
  rows at the limit). A row that a click changes shows a pointer cursor; a
  selected row has its own background.
- Shift + click on a row or on its checkbox selects (or clears, following
  the clicked row's new state) every row shown from the row clicked before
  to this one. The range counts the rows of the current page in their shown
  order; when the row clicked before is not on it (after paging or
  filtering), only the clicked row changes. Shift + click does not select
  the text between the clicks.
- `max_selected` (a positive integer, on a selectable table only) limits the
  selection. When it is reached, the checkboxes of the unselected rows are
  disabled (selected rows can still be cleared) and the notice
  `[data-dt-limit]` above the table says so; both hold after paging,
  filtering, and sorting. The header checkbox is disabled while selecting
  every matching row would pass the limit; when they all fit, or when they
  are all selected (to clear them), it works as without a limit. A Shift +
  click range that would pass the limit changes nothing, and the row clicked
  before stays the start of the next range. An initial selection past the
  limit is kept and can only be reduced. One function in `datatable.js`
  (`canChange`) decides whether a change of the selection is allowed (row,
  range, header checkbox, and Clear), for a locked table too.
- Each change of the selection dispatches `datatable:selection-change` on the
  container. It bubbles; `event.detail.keys` holds the selected keys and
  `event.detail.max` the limit (`null` without one). The footer already
  shows the count, so a page needs the event only to act on the selection.
- A page that sets the selection input itself dispatches
  `datatable:selection-sync` on the container, and the checkboxes show the
  selection again.

## Elements and classes

Every class starts with `dt-`; ids and data attributes are scoped by the
container, so several tables can share a page.

| Selector | Element |
| --- | --- |
| `.dt-root[data-datatable]` | Container (`id` = `table_id`, `hx-get` or `hx-post` = `url`); `data-dt-extra-inputs` with the ids of `extra_inputs`; `data-dt-locked` when locked; `data-dt-pinned` while the left columns are pinned; `data-dt-max-selected` with the limit; `data-dt-export-url` with `export_url`; `data-dt-pin-preference` with `pin_preference`; `data-dt-query-columns` with `query_columns`; `data-dt-parameters` with `parameter_names` (a JSON object of the query parameter names, by which `datatable.js` finds and sends them); `aria-busy` and `htmx-request` while reloading. |
| `[data-dt-part]` | A part of the fragment swapped after the table's own reloads (`state`, `rows`, `footer`, `matching`, `chips`, `limit`, `export-filtered`, and per column `sort-<n>`, `filtered-<n>`, `histogram-<n>`, `sorts-<n>`, `clear-<n>`). |
| `.dt-state`, `.dt-chips-slot`, `.dt-filter-state` | Holders of the hidden sort / order / abs / page inputs, of the chips, and of a column's filter mark (no box of their own). |
| `.dt-scroll` / `.dt-table` | Scroll box with a fixed header / the table (`table-layout: fixed`). |
| `.dt-head`, `.dt-column[data-dt-column]`, `.dt-label` | Header line and the column name button opening the menu. |
| `.dt-resizer[data-dt-resize]` | Handle on the right edge of a header resizing its column (`role="separator"`, named `Resize column <label>`, `aria-valuenow` the width in pixels); `data-dt-resizing` while dragged, also on the container. |
| `[data-dt-reset-widths]` | `Reset column widths` button of the `Columns` menu. |
| `.dt-measure` | Copy of a cell's contents measured to fit its column (removed at once). |
| `.dt-sort-mark`, `.dt-menu-mark`, `.dt-filter-mark[data-dt-filtered]` | ▲ / ▼, the menu's ⋯, and the funnel of a filtered column. |
| `.dt-type` | Column type under the name. |
| `.dt-histogram[data-dt-histogram]`, `.dt-bins`, `.dt-bin`, `.dt-bin-bar`, `.dt-bin-hit`, `.dt-ticks` | A column's histogram: the SVG (`role="img"`, named `Histogram of <label>, <min> to <max>`), a bin (`<g>` with its `<title>`), its bar and its full-height hover area, and the smallest and largest value. |
| `.dt-top-values[data-dt-top-values]`, `.dt-top-value`, `.dt-top-bar`, `.dt-top-label`, `.dt-top-others` | Most frequent values (a list named `Most frequent values of <label>`), a value with its bar, text, and `.dt-count`, and the `Others` line. |
| `.dt-out` | A bin outside the bounds in use, or a value not checked, shown faded. |
| `.dt-toolbar`, `.dt-toolbar-actions` | Line above the table (under the chips) holding the search box, and the group of the `Columns`, `Pin columns`, and `Export` buttons at its right end. |
| `.dt-search` | Search box of the whole table (`id` `<table_id>-search`). |
| `.dt-columns-button`, `.dt-menu[data-dt-columns-menu]`, `[data-dt-show-column]` | `Columns` button, its menu (`id` `<table_id>-columns-menu`, named `Columns`), and the checkbox of each column. |
| `.dt-pin-button[data-dt-pin-toggle]`, `.dt-switch` | `Pin columns` toggle (`aria-pressed`) and its switch. |
| `.dt-export-button`, `.dt-menu[data-dt-export-menu]`, `.dt-export-rows`, `.dt-export-label`, `[data-dt-export][data-dt-export-rows]`, `[data-dt-export-selected-count]`, `.dt-export-error[data-dt-export-error]` | `Export` button (`export_button`: the download icon and `Export`), its menu (`id` `<table_id>-export-menu`, named `Export`), a group of rows (named `Filtered rows` / `Selected rows`) with its label and count, a download button (`csv` or `parquet`, `filtered` or `selected`, named `Export <rows> as <format>`), the selected count, and the failure notice (`role="alert"`). |
| `.dt-chips`, `.dt-chip`, `.dt-chip-label`, `[data-dt-remove-filter]` | List of the filters in use (named `Filters in use`), a chip, its text, and its × button (a JSON array of the parameter names it clears). |
| `.dt-menu[popover][data-dt-menu]` | A menu: a column's (`id` `<table_id>-menu-<n>`, `role="dialog"`, named `<label> menu`, `data-dt-menu` = the column name), the `Columns` or `Export` menu, or a menu outside a table (empty `data-dt-menu`; see [Use](#use) 7); `data-dt-placed` once placed. |
| `.dt-menu-section`, `.dt-sorts`, `.dt-filter`, `.dt-choices`, `.dt-choice-list`, `.dt-choice`, `.dt-count` | Menu parts: sort buttons (`[data-dt-sort][data-dt-order]`, `aria-pressed`) and the `Abs` checkbox (`.dt-sort-absolute`, `[data-dt-sort-absolute]` = the column name), the filter, the value list (its fieldset and the `<div>` holding the values), a value, and counts. |
| `.dt-nulls`, `.dt-nulls-label`, `[data-dt-null-value]`, `.dt-segmented`, `[data-dt-null]` | The null filter: its label with the null count, the hidden query input holding the choice, and the segmented control (`role="group"`) of its buttons (`aria-pressed`; `data-dt-null` is the value: empty, `is_null`, or `is_not_null`). |
| `.dt-filter-actions`, `.dt-draft-status[data-dt-draft-status]`, `.dt-icon-button`, `.dt-apply[data-dt-apply]`, `.dt-cancel[data-dt-cancel]`, `.dt-clear-filter[data-dt-clear-filter]` | Under the filters of a column menu: the notice of unapplied changes and the `Apply filters`, `Cancel`, and `Clear the filters of this column` icon buttons. |
| `[data-dt-copy]` | "Copy column name" button. |
| `.dt-check`, `[data-dt-check-all]`, `[data-dt-row-check]` | Selection checkboxes. |
| `.dt-pinned` | Cells of the checkbox column and the first column; the checkbox column (`.dt-check`) is always pinned at the left, the first column while the container has `data-dt-pinned`. |
| `.dt-limit[data-dt-limit]` | Notice that the selection limit is reached (`hidden` below it). |
| `tr[data-dt-key]` | Row with its key. |
| `.dt-footer` | Footer under the table. |
| `.dt-shape[data-dt-shape]`, `[data-dt-column-count]` | "N rows, M columns", and M (the shown columns). |
| `.dt-selection-state`, `.dt-selected-count[data-dt-selected-count]`, `[data-dt-clear]` | Selection count and the Clear button (selectable tables). |
| `.dt-pager`, `[data-dt-page-range][data-dt-start]`, `[data-dt-page]`, `.dt-page-jump`, `.dt-page-input[data-dt-page-input][data-dt-page-current]` | "a–b of N" (`data-dt-start` = a), the first / previous / next / last page buttons (named `First page` and so on), and the page number input. |
| `.dt-page-size`, `[data-dt-page-size]` | `Rows per page` and its `select` (with `page_sizes`). |

## CSS variables

Set them on `.dt-root` (or an ancestor) to change the look. The defaults
follow `prefers-color-scheme`; `data-dt-theme="light"` or `"dark"` on the
container or an ancestor fixes the scheme.

| Variable | Use |
| --- | --- |
| `--dt-fg`, `--dt-muted` | Text, and headers / the footer texts / locked rows / the limit notice. |
| `--dt-border` | Lines between rows and between columns, and box borders. |
| `--dt-bg` | Background of the pinned cells, which cover the cells scrolled under them. |
| `--dt-header-bg`, `--dt-row-hover-bg`, `--dt-row-selected-bg` | Header, hovered row, and selected row backgrounds. |
| `--dt-accent`, `--dt-accent-soft` | Sort and filter marks, the chosen sort and null filter in a menu, the `Apply` icon, and the `Pin columns` switch while on; the background of the chosen null filter. |
| `--dt-danger` | The `Clear` icon of a column menu. |
| `--dt-radius` | Box corner radius. |
| `--dt-font`, `--dt-font-size` | Font family and table font size. |
| `--dt-cell-padding` | Cell padding. |
| `--dt-check-width` | Width of the checkbox column, where the pinned first column starts. |
| `--dt-col-width` | Width of every other column until it is resized (default `12rem`). |
| `--dt-col-min-width` | Narrowest width of a column (default `--dt-histogram-width` plus `1.5rem`, the left and right padding of the default `--dt-cell-padding`); never below the histogram and the cell's padding. |
| `--dt-max-height` | Height of the scroll box (about the header and 12 rows). |
| `--dt-filter-max-width` | Width limit of the filter inputs. |
| `--dt-mono-font` | Font of the column types. |
| `--dt-menu-bg`, `--dt-menu-shadow`, `--dt-menu-max-width` | Menu background, shadow, and width limit. |
| `--dt-search-width` | Narrowest width of the search box, which fills the width left, before the buttons move to the next line. |
| `--dt-chip-bg` | Background of the filter chips. |
| `--dt-histogram-width`, `--dt-histogram-height` | Width of a histogram or of the top values (fixed, whatever the column's width), and height of a histogram's bars. |
| `--dt-histogram-fg`, `--dt-histogram-out-opacity` | Color of the bars, and opacity of the faded ones. |

Buttons and inputs otherwise take the page's own styles.
