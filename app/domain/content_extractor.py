"""HTML content extraction — pure, side-effect-free.

Given already-fetched HTML, produce a compact summary: title, meta
description, h1-h3 headings, the main body text, and a word count. Main text
comes from trafilatura (good at stripping nav/boilerplate); the structural
metadata comes from lxml.html. This module never fetches the page — the caller
supplies the HTML and the URL is used only as a hint for extraction.
"""

from __future__ import annotations

from typing import Any

import trafilatura
from lxml import html as lxml_html

_HEADING_TAGS = ("h1", "h2", "h3")


def _empty_result() -> dict[str, Any]:
    return {
        "title": None,
        "meta_description": None,
        "headings": [],
        "main_text": "",
        "word_count": 0,
    }


def extract_content(html_str: str, url: str) -> dict[str, Any]:
    """Extract structured content from a raw HTML string.

    Args:
        html_str: The raw HTML of the page.
        url: The page URL, passed to trafilatura only as a hint (no fetching).

    Returns:
        A dict with keys:
            - "title": <str|None> the document <title>.
            - "meta_description": <str|None> the <meta name="description"> content.
            - "headings": list of {"tag": "h1"|"h2"|"h3", "text": str}, in
              document order.
            - "main_text": <str> the extracted body text (empty string if none).
            - "word_count": <int> whitespace-delimited word count of main_text.
        Empty or whitespace-only input yields an all-empty result rather than
        raising.
    """
    if not html_str or not html_str.strip():
        return _empty_result()

    main_text = trafilatura.extract(html_str, url=url) or ""

    try:
        tree = lxml_html.fromstring(html_str)
    except (lxml_html.etree.ParserError, ValueError):
        return {
            "title": None,
            "meta_description": None,
            "headings": [],
            "main_text": main_text,
            "word_count": len(main_text.split()),
        }

    title = tree.findtext(".//title")
    title = title.strip() if title and title.strip() else None

    meta_description = None
    for meta in tree.iter("meta"):
        name = (meta.get("name") or "").strip().lower()
        if name == "description":
            content = (meta.get("content") or "").strip()
            meta_description = content or None
            break

    headings: list[dict[str, str]] = []
    for element in tree.iter(*_HEADING_TAGS):
        text = element.text_content().strip()
        if text:
            headings.append({"tag": element.tag, "text": text})

    return {
        "title": title,
        "meta_description": meta_description,
        "headings": headings,
        "main_text": main_text,
        "word_count": len(main_text.split()),
    }
