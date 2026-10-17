"""A small element tree of rendered HTML, built with ``html.parser``, for the template tests."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from html.parser import HTMLParser

VOID_TAGS = frozenset(
    {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
)
"""Tags that have no end tag and no children."""

# A compound selector of a selector, a space inside a quoted value included.
_COMPOUNDS = re.compile(r'(?:[^\s"]|"[^"]*")+')
# A tag name and its class, id, and attribute parts.
_COMPOUND = re.compile(r"([\w-]*)((?:[.#][\w-]+|\[[\w-]+(?:=\"[^\"]*\")?\])*)")
# One ``.class``, ``#id``, ``[attr]``, or ``[attr="value"]`` part.
_PART = re.compile(r"([.#])([\w-]+)|\[([\w-]+)(?:=\"([^\"]*)\")?\]")


@dataclass(eq=False)
class Element:
    """An element of rendered HTML with its attributes and children.

    Attributes
    ----------
    tag : str
        The lowercase tag name; ``""`` for the root of a parsed document.
    attrs : dict[str, str | None]
        The attributes, unescaped; a boolean attribute has the value ``None``.
    children : list[Element | str]
        The child elements and the text between them, in document order.
    position : int
        The order of the start tag in the document, for comparing positions.
    """

    tag: str
    attrs: dict[str, str | None] = field(default_factory=dict)
    children: list[Element | str] = field(default_factory=list)
    position: int = 0

    def __eq__(self, other: object) -> bool:
        """Return whether ``other`` has the same tag, attributes, and children.

        Parameters
        ----------
        other : object
            The object to compare with.

        Returns
        -------
        bool
            Whether both are elements of the same markup, wherever they are.
        """
        if not isinstance(other, Element):
            return NotImplemented
        return (self.tag, self.attrs, self.children) == (other.tag, other.attrs, other.children)

    __hash__ = None  # type: ignore[assignment]

    def __getitem__(self, name: str) -> str | None:
        """Return the value of attribute ``name``, which must be present.

        Parameters
        ----------
        name : str
            The attribute name.

        Returns
        -------
        str | None
            The attribute value, or ``None`` for a boolean attribute.
        """
        return self.attrs[name]

    def __contains__(self, name: str) -> bool:
        """Return whether the element has attribute ``name``.

        Parameters
        ----------
        name : str
            The attribute name.

        Returns
        -------
        bool
            Whether the attribute is present.
        """
        return name in self.attrs

    @property
    def classes(self) -> list[str]:
        """Return the class names of the element.

        Returns
        -------
        list[str]
            The words of the ``class`` attribute.
        """
        return (self.attrs.get("class") or "").split()

    @property
    def text(self) -> str:
        """Return the text of the element and its descendants.

        Returns
        -------
        str
            The text joined in document order, as written.
        """
        return "".join(child if isinstance(child, str) else child.text for child in self.children)

    @property
    def words(self) -> str:
        """Return the text with each run of whitespace made one space.

        Returns
        -------
        str
            The stripped text with collapsed whitespace.
        """
        return " ".join(self.text.split())

    def iter(self) -> Iterator[Element]:
        """Yield every descendant element in document order.

        Yields
        ------
        Element
            Each descendant, the element itself excluded.
        """
        for child in self.children:
            if isinstance(child, Element):
                yield child
                yield from child.iter()

    def select(self, selector: str) -> list[Element]:
        """Return the descendants that match a CSS selector, in document order.

        The selector is a list of compound selectors separated by spaces (the
        descendant combinator); each one is an optional tag name followed by
        ``.class``, ``#id``, ``[attr]``, and ``[attr="value"]`` parts.

        Parameters
        ----------
        selector : str
            The selector.

        Returns
        -------
        list[Element]
            The matching descendants.
        """
        candidates = [self]
        for compound in _COMPOUNDS.findall(selector):
            matched = {id(element): element for parent in candidates for element in parent.iter() if _matches(element, compound)}
            candidates = sorted(matched.values(), key=lambda element: element.position)
        return candidates

    def select_one(self, selector: str) -> Element:
        """Return the only descendant that matches a CSS selector.

        Parameters
        ----------
        selector : str
            The selector, as in :meth:`select`.

        Returns
        -------
        Element
            The matching descendant.

        Raises
        ------
        AssertionError
            If no descendant or more than one matches.
        """
        matched = self.select(selector)
        assert len(matched) == 1, f"{len(matched)} elements match {selector!r}"
        return matched[0]


def _matches(element: Element, compound: str) -> bool:
    """Return whether an element matches one compound selector.

    Parameters
    ----------
    element : Element
        The element.
    compound : str
        A tag name followed by class, id, and attribute parts.

    Returns
    -------
    bool
        Whether the element matches every part.

    Raises
    ------
    ValueError
        If the selector is not of the supported form.
    """
    match = _COMPOUND.fullmatch(compound)
    if match is None:
        raise ValueError(f"unsupported selector: {compound!r}")
    tag, parts = match.groups()
    if tag and element.tag != tag:
        return False
    return all(_matches_part(element, *part.groups()) for part in _PART.finditer(parts))


def _matches_part(element: Element, kind: str | None, name: str | None, attribute: str | None, value: str | None) -> bool:
    """Return whether an element matches one class, id, or attribute part of a selector.

    Parameters
    ----------
    element : Element
        The element.
    kind : str | None
        ``"."`` for a class, ``"#"`` for an id, or ``None`` for an attribute.
    name : str | None
        The class or id.
    attribute : str | None
        The attribute name.
    value : str | None
        The attribute value, or ``None`` when only its presence is required.

    Returns
    -------
    bool
        Whether the element matches the part.
    """
    if kind == ".":
        return name in element.classes
    if kind == "#":
        return element.attrs.get("id") == name
    return attribute in element.attrs and (value is None or element.attrs[attribute] == value)


class _TreeBuilder(HTMLParser):
    """Build an :class:`Element` tree from the events of ``HTMLParser``."""

    def __init__(self) -> None:
        """Start a tree with an empty root."""
        super().__init__(convert_charrefs=True)
        self.root = Element("")
        self._open = [self.root]
        self._count = 0

    def _element(self, tag: str, attrs: list[tuple[str, str | None]]) -> Element:
        """Append a new element to the open element and return it.

        Parameters
        ----------
        tag : str
            The tag name.
        attrs : list[tuple[str, str | None]]
            The attributes of the start tag.

        Returns
        -------
        Element
            The new element.
        """
        self._count += 1
        element = Element(tag, dict(attrs), position=self._count)
        self._open[-1].children.append(element)
        return element

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Open an element, unless it is a void element.

        Parameters
        ----------
        tag : str
            The tag name.
        attrs : list[tuple[str, str | None]]
            The attributes of the start tag.
        """
        element = self._element(tag, attrs)
        if tag not in VOID_TAGS:
            self._open.append(element)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Add a self-closing element without opening it.

        Parameters
        ----------
        tag : str
            The tag name.
        attrs : list[tuple[str, str | None]]
            The attributes of the tag.
        """
        self._element(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        """Close the open element, which must be of ``tag``.

        Parameters
        ----------
        tag : str
            The tag name.

        Raises
        ------
        AssertionError
            If the innermost open element is not of ``tag``.
        """
        if tag in VOID_TAGS:
            return
        assert len(self._open) > 1, f"</{tag}> closes no open element"
        assert self._open[-1].tag == tag, f"</{tag}> closes <{self._open[-1].tag}>"
        self._open.pop()

    def handle_data(self, data: str) -> None:
        """Add text to the open element.

        Parameters
        ----------
        data : str
            The text, with character references converted.
        """
        self._open[-1].children.append(data)


def parse_html(html: str) -> Element:
    """Parse HTML into an element tree.

    Parameters
    ----------
    html : str
        The HTML, a whole document or a fragment.

    Returns
    -------
    Element
        A root element with tag ``""`` whose children are the top-level nodes.

    Raises
    ------
    AssertionError
        If an end tag does not close the innermost open element, or an element is left open.
    """
    builder = _TreeBuilder()
    builder.feed(html)
    builder.close()
    unclosed = [element.tag for element in builder._open[1:]]
    assert not unclosed, f"unclosed elements: {unclosed}"
    return builder.root


Render = Callable[..., Element]
"""The type of the ``render`` fixture: a macro call and its context to a parsed tree."""
