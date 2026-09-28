"""Sitemap XML parsing — pure, side-effect-free.

Parses a single sitemap document from raw bytes. It distinguishes a
<sitemapindex> (a list of nested sitemaps) from a <urlset> (a list of page
URLs). It does NOT fetch anything: recursion into nested sitemaps is the
responsibility of app/services/sitemap_service.py.
"""

from __future__ import annotations

from typing import Any

from lxml import etree


def _local_name(tag: Any) -> str:
    """Return an element's tag without its XML namespace.

    lxml reports namespaced tags as "{namespace}local"; sitemaps may or may not
    declare the sitemaps.org namespace, so we normalise to the local name.
    Non-element nodes (e.g. comments) have a non-str tag and yield "".
    """
    if not isinstance(tag, str):
        return ""
    return tag.rsplit("}", 1)[-1]


def _child_text(element: etree._Element, name: str) -> str | None:
    """Return the stripped text of the first direct child with the given local name."""
    for child in element:
        if _local_name(child.tag) == name:
            text = child.text
            return text.strip() if text and text.strip() else None
    return None


def parse_sitemap(xml_bytes: bytes) -> list[dict[str, Any]]:
    """Parse raw sitemap XML into a flat list of entries.

    Args:
        xml_bytes: The raw XML document as bytes.

    Returns:
        For a <sitemapindex> root: one entry per <sitemap> shaped as
        {"type": "sitemap", "loc": <url>, "lastmod": <str|None>}.
        For a <urlset> root: one entry per <url> shaped as
        {"type": "url", "loc": <url>, "lastmod": <str|None>}.
        Entries without a <loc> are skipped. Any other root returns [].

    Raises:
        lxml.etree.XMLSyntaxError: if the bytes are not well-formed XML.
    """
    # recover=True tolerates the minor malformations common in real sitemaps
    # (stray bytes, undeclared entities) without silently discarding structure.
    parser = etree.XMLParser(recover=True, resolve_entities=False)
    root = etree.fromstring(xml_bytes, parser=parser)
    if root is None:
        return []

    root_name = _local_name(root.tag)
    if root_name == "sitemapindex":
        child_name, entry_type = "sitemap", "sitemap"
    elif root_name == "urlset":
        child_name, entry_type = "url", "url"
    else:
        return []

    entries: list[dict[str, Any]] = []
    for element in root:
        if _local_name(element.tag) != child_name:
            continue
        loc = _child_text(element, "loc")
        if loc is None:
            continue
        entries.append(
            {
                "type": entry_type,
                "loc": loc,
                "lastmod": _child_text(element, "lastmod"),
            }
        )
    return entries
