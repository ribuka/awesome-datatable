"""Tests that the data table's public API is its package and only what applications use."""

from __future__ import annotations

import ast
from pathlib import Path

from flat_pca.webui import datatable

REPOSITORY = Path(__file__).parents[3]
PACKAGE = "flat_pca.webui.datatable"
# Unit tests of the package's internals, the only importers of its submodules.
INTERNAL_TESTS = REPOSITORY / "tests" / "webui" / "datatable"
PUBLIC_API = {
    # What flat-pca uses.
    "ColumnConfig",
    "TableConfig",
    "FilterKind",
    "TableState",
    "TableSummary",
    "TableView",
    "ExportFile",
    "ExportFormat",
    "STATIC_DIR",
    "MEDIA_TYPES",
    "configure_environment",
    "parse_state",
    "parse_export",
    "parse_selection",
    "apply_state",
    "summarize_table",
    "export_file",
    "export_filename",
    "file_content",
    "format_value",
    # Types of the arguments and results above and of the fields of TableView.
    "Page",
    "ColumnCounts",
    "ColumnHistogram",
    "Histogram",
    "HistogramBin",
    "TopValues",
    "TopValue",
    "FilterChip",
    "ExportRequest",
    "ExportRows",
    "RequestMethod",
    "NullFilter",
}


def _module_name(path: Path) -> str:
    """Return the dotted module name of a Python file of ``src`` or ``tests``."""
    parts = path.relative_to(REPOSITORY).with_suffix("").parts
    parts = parts[1:] if parts[0] == "src" else parts
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def _imported_names(path: Path) -> set[str]:
    """Return the absolute names of the modules a file imports and of what it imports from them."""
    name = _module_name(path)
    package = name if path.name == "__init__.py" else name.rpartition(".")[0]
    modules: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package.rsplit(".", node.level - 1)[0] if node.level > 1 else package
                module = f"{base}.{node.module}" if node.module else base
            else:
                module = node.module or ""
            modules.add(module)
            modules.update(f"{module}.{alias.name}" for alias in node.names)
    return modules


def test_all_is_the_public_api() -> None:
    """``__all__`` holds exactly what applications use and the types they meet."""
    assert set(datatable.__all__) == PUBLIC_API
    assert all(hasattr(datatable, name) for name in datatable.__all__)


def test_internals_are_not_exported() -> None:
    """The byte order mark and the templates directory stay inside the package."""
    assert not hasattr(datatable, "UTF8_BOM")
    assert not hasattr(datatable, "TEMPLATES_DIR")


def test_only_the_internal_tests_import_the_submodules() -> None:
    """The rest of flat-pca imports the data table only from its package."""
    package_dir = Path(datatable.__file__).parent
    submodules = {path.stem for path in package_dir.glob("*.py")} - {"__init__"}
    paths = [
        path
        for root in ("src", "tests")
        for path in (REPOSITORY / root).rglob("*.py")
        if not path.is_relative_to(package_dir) and not path.is_relative_to(INTERNAL_TESTS)
    ]

    offenders = {
        path.relative_to(REPOSITORY).as_posix(): sorted(
            name
            for name in _imported_names(path)
            if name.startswith(PACKAGE + ".")
            and name.removeprefix(PACKAGE + ".").split(".")[0] in submodules
        )
        for path in paths
    }

    assert {path: modules for path, modules in offenders.items() if modules} == {}
