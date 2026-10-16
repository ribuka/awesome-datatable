"""Opening and closing the column menus of a data table in browser tests."""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect


def open_column_menu(table: Locator, header: str) -> Locator:
    """Open the menu of a column by clicking its name.

    Parameters
    ----------
    table : Locator
        Data table container (``[data-datatable]``), or an element holding it.
    header : str
        Header text of the column.

    Returns
    -------
    Locator
        The open menu.
    """
    table.get_by_role("button", name=header, exact=True).click()
    menu = column_menu(table, header)
    expect(menu).to_be_visible()
    return menu


def column_menu(table: Locator, header: str) -> Locator:
    """Return the menu of a column, open or not.

    Parameters
    ----------
    table : Locator
        Data table container, or an element holding it.
    header : str
        Header text of the column.

    Returns
    -------
    Locator
        The menu (``[data-dt-menu]``) named ``"<header> menu"``.
    """
    return table.locator(f'[data-dt-menu][aria-label="{header} menu"]')


def apply_column_menu(menu: Locator) -> None:
    """Apply the draft filters of an open column menu, which closes it.

    Parameters
    ----------
    menu : Locator
        The open menu, with filters changed from those applied.
    """
    apply_button(menu).click()
    expect(menu).to_be_hidden()


def close_column_menu(page: Page, menu: Locator) -> None:
    """Close an open column menu with Escape.

    Parameters
    ----------
    page : Page
        Browser page.
    menu : Locator
        The open menu.
    """
    page.keyboard.press("Escape")
    expect(menu).to_be_hidden()


def apply_button(menu: Locator) -> Locator:
    """Return the Apply icon button of a column menu.

    Parameters
    ----------
    menu : Locator
        A column menu with filters.

    Returns
    -------
    Locator
        The button named ``Apply filters`` (``[data-dt-apply]``).
    """
    return menu.locator("[data-dt-apply]")


def cancel_button(menu: Locator) -> Locator:
    """Return the Cancel icon button of a column menu.

    Parameters
    ----------
    menu : Locator
        A column menu with filters.

    Returns
    -------
    Locator
        The button named ``Cancel`` (``[data-dt-cancel]``).
    """
    return menu.locator("[data-dt-cancel]")


def clear_filter_button(menu: Locator) -> Locator:
    """Return the Clear icon button of a column menu.

    Parameters
    ----------
    menu : Locator
        A column menu with filters.

    Returns
    -------
    Locator
        The button named ``Clear the filters of this column``
        (``[data-dt-clear-filter]``).
    """
    return menu.locator("[data-dt-clear-filter]")


def null_filter_button(menu: Locator, label: str) -> Locator:
    """Return a button of the null filter of a column menu.

    Parameters
    ----------
    menu : Locator
        A column menu with filters.
    label : str
        ``Any``, ``Is null``, or ``Is not null``.

    Returns
    -------
    Locator
        The button of the segmented control, pressed (``aria-pressed``)
        while chosen.
    """
    return menu.locator(".dt-segmented").get_by_role("button", name=label, exact=True)


def choose_null_filter(menu: Locator, label: str) -> None:
    """Choose a value of the null filter of an open column menu, as a draft.

    Parameters
    ----------
    menu : Locator
        The open menu.
    label : str
        ``Any``, ``Is null``, or ``Is not null``.
    """
    button = null_filter_button(menu, label)
    button.click()
    expect(button).to_have_attribute("aria-pressed", "true")
