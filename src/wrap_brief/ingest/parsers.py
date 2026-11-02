"""Bounded RSS/Atom metadata extraction from bytes; never fetch URLs or resolve content."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, fields
from html.parser import HTMLParser
from io import BytesIO
from typing import Literal
from xml.etree.ElementTree import Element

from defusedxml import ElementTree as SafeET
from defusedxml.common import DefusedXmlException

from wrap_brief.models import Source

ATOM = "{http://www.w3.org/2005/Atom}"
DC = "{http://purl.org/dc/elements/1.1/}"
_CAPS = {
    "max_bytes": 2_097_152,
    "max_depth": 64,
    "max_items": 100,
    "max_text": 4096,
    "max_nodes": 10_000,
}
_ERROR_CODES = {
    "invalid_input",
    "invalid_source",
    "invalid_limits",
    "size_limit",
    "depth_limit",
    "item_limit",
    "text_limit",
    "node_limit",
    "xml_security",
    "malformed_xml",
    "unsupported_feed",
}


class FeedParseError(ValueError):
    """A fixed rejection code, never an underlying exception or input excerpt."""

    def __init__(self, code: str):
        self.code = code if isinstance(code, str) and code in _ERROR_CODES else "invalid_input"
        super().__init__(f"feed: {self.code}")


@dataclass(frozen=True, slots=True)
class FeedLimits:
    max_bytes: int = 2_097_152
    max_depth: int = 64
    max_items: int = 100
    max_text: int = 4096
    max_nodes: int = 10_000

    def __post_init__(self) -> None:
        for field in fields(self):
            value = getattr(self, field.name)
            if type(value) is not int or not 0 < value <= _CAPS[field.name]:
                raise FeedParseError("invalid_limits")


@dataclass(frozen=True, slots=True, repr=False)
class RawEntry:
    """Provisional, untrusted metadata: normalize/validate before persistence or rendering."""

    source_id: str
    title: str
    url: str
    guid: str | None = None
    published: str | None = None
    updated: str | None = None

    def __repr__(self) -> str:
        return "<RawEntry: untrusted metadata>"


@dataclass(frozen=True, slots=True)
class EntryIssue:
    index: int
    code: Literal["missing_title", "missing_link", "invalid_title"]


@dataclass(frozen=True, slots=True)
class ParsedFeed:
    format: Literal["rss2", "atom"]
    entries: tuple[RawEntry, ...]
    issues: tuple[EntryIssue, ...]


class _TitleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self.hidden.append(tag)
        elif tag in {"br", "p", "div"} and not self.hidden:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if self.hidden and tag == self.hidden[-1]:
            self.hidden.pop()
        elif tag in {"p", "div"} and not self.hidden:
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(data)


class _InvalidTitle(ValueError):
    pass


def _fragments(element: Element) -> Iterator[str]:
    if element.text:
        yield element.text
    for child in element:
        if isinstance(child.tag, str) and child.tag.rsplit("}", 1)[-1].lower() not in {
            "script",
            "style",
        }:
            yield from _fragments(child)
        if child.tail:
            yield child.tail


def _text(element: Element | None, limits: FeedLimits) -> str | None:
    if element is None:
        return None
    parts: list[str] = []
    length = 0
    for fragment in _fragments(element):
        length += len(fragment)
        if length > limits.max_text:
            raise FeedParseError("text_limit")
        parts.append(fragment)
    return "".join(parts).strip() or None


def _title(element: Element | None, limits: FeedLimits, *, html: bool) -> str | None:
    text = _text(element, limits)
    if text is None or not html:
        return text
    parser = _TitleText()
    try:
        parser.feed(text)
        parser.close()
    except (AssertionError, ValueError):
        raise _InvalidTitle() from None
    result = "".join(parser.parts).strip()
    if not result:
        raise _InvalidTitle()
    return result


def _rss_entry(element: Element, source: Source, limits: FeedLimits) -> RawEntry | str:
    try:
        title = _title(element.find("title"), limits, html=True)
    except _InvalidTitle:
        return "invalid_title"
    url = _text(element.find("link"), limits)
    if not title:
        return "missing_title"
    if not url:
        return "missing_link"
    return RawEntry(
        source.id,
        title,
        url,
        _text(element.find("guid"), limits),
        _text(element.find("pubDate"), limits) or _text(element.find(DC + "date"), limits),
        _text(element.find(ATOM + "updated"), limits),
    )


def _atom_entry(element: Element, source: Source, limits: FeedLimits) -> RawEntry | str:
    title_element = element.find(ATOM + "title")
    if title_element is not None and title_element.get("type", "text") not in {
        "text",
        "html",
        "xhtml",
    }:
        return "invalid_title"
    try:
        title = _title(
            title_element,
            limits,
            html=title_element is not None and title_element.get("type") == "html",
        )
    except _InvalidTitle:
        return "invalid_title"
    url = None
    for link in element.findall(ATOM + "link"):
        if link.get("rel", "alternate") not in {"alternate", ""} or link.get(
            "type", "text/html"
        ) not in {"text/html", "application/xhtml+xml", ""}:
            continue
        candidate = link.get("href", "")
        if len(candidate) > limits.max_text:
            raise FeedParseError("text_limit")
        if candidate.strip():
            url = candidate.strip()
            break
    if not title:
        return "missing_title"
    if not url:
        return "missing_link"
    return RawEntry(
        source.id,
        title,
        url,
        _text(element.find(ATOM + "id"), limits),
        _text(element.find(ATOM + "published"), limits),
        _text(element.find(ATOM + "updated"), limits),
    )


def parse_feed(data: bytes, source: Source, *, limits: FeedLimits | None = None) -> ParsedFeed:
    """Extract metadata only. Sources may be disabled for offline tests; this grants no fetch rights."""
    if type(data) is not bytes:
        raise FeedParseError("invalid_input")
    if not isinstance(source, Source):
        raise FeedParseError("invalid_source")
    if limits is None:
        limits = FeedLimits()
    elif type(limits) is not FeedLimits:
        raise FeedParseError("invalid_limits")
    else:
        FeedLimits.__post_init__(limits)
    if len(data) > limits.max_bytes:
        raise FeedParseError("size_limit")
    stack: list[str] = []
    entries: list[RawEntry] = []
    issues: list[EntryIssue] = []
    root = ""
    nodes = channels = count = 0
    try:
        with BytesIO(data) as stream:
            events = SafeET.iterparse(
                stream,
                events=("start", "end"),
                forbid_dtd=True,
                forbid_entities=True,
                forbid_external=True,
            )
            for event, element in events:
                if event == "start":
                    stack.append(element.tag)
                    nodes += 1
                    if len(stack) > limits.max_depth:
                        raise FeedParseError("depth_limit")
                    if nodes > limits.max_nodes:
                        raise FeedParseError("node_limit")
                    if len(stack) == 1:
                        root = element.tag
                        if root not in {"rss", ATOM + "feed"}:
                            raise FeedParseError("unsupported_feed")
                        if root == "rss" and element.get("version", "2.0") != "2.0":
                            raise FeedParseError("unsupported_feed")
                    elif stack == ["rss", "channel"]:
                        channels += 1
                        if channels > 1:
                            raise FeedParseError("unsupported_feed")
                    continue
                rss = stack == ["rss", "channel", "item"]
                atom = stack == [ATOM + "feed", ATOM + "entry"]
                if rss or atom:
                    count += 1
                    if count > limits.max_items:
                        raise FeedParseError("item_limit")
                    entry = (
                        _rss_entry(element, source, limits)
                        if rss
                        else _atom_entry(element, source, limits)
                    )
                    if isinstance(entry, str):
                        issues.append(EntryIssue(count - 1, entry))
                    else:
                        entries.append(entry)
                    element.clear()
                stack.pop()
    except FeedParseError:
        raise
    except DefusedXmlException:
        raise FeedParseError("xml_security") from None
    except (SafeET.ParseError, UnicodeError, LookupError, ValueError):
        raise FeedParseError("malformed_xml") from None
    if not root or (root == "rss" and channels != 1):
        raise FeedParseError("unsupported_feed")
    return ParsedFeed("rss2" if root == "rss" else "atom", tuple(entries), tuple(issues))
