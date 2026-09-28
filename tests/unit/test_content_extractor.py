"""Unit tests for app/domain/content_extractor.py (pure, no network fetch).

The HTML sample is inline; extract_content never fetches anything.
"""

from __future__ import annotations

from app.domain.content_extractor import extract_content

SAMPLE_HTML = """<!DOCTYPE html>
<html>
  <head>
    <title>Best Running Shoes</title>
    <meta name="description" content="A practical guide to choosing running shoes.">
  </head>
  <body>
    <nav>Home About Contact</nav>
    <article>
      <h1>Best Running Shoes</h1>
      <h2>Cushioned Options</h2>
      <p>Running shoes come in many varieties. Cushioned shoes protect your
      joints during long distance runs on hard pavement surfaces.</p>
      <h3>Budget Picks</h3>
      <p>Even on a tight budget you can find durable trainers that last for
      hundreds of miles without falling apart quickly.</p>
    </article>
    <footer>Copyright 2026 Example Inc.</footer>
  </body>
</html>"""

SAMPLE_URL = "https://example.com/best-running-shoes"


def test_extract_title():
    result = extract_content(SAMPLE_HTML, SAMPLE_URL)

    assert result["title"] == "Best Running Shoes"


def test_extract_meta_description():
    result = extract_content(SAMPLE_HTML, SAMPLE_URL)

    assert result["meta_description"] == "A practical guide to choosing running shoes."


def test_extract_headings_in_order():
    result = extract_content(SAMPLE_HTML, SAMPLE_URL)

    assert result["headings"] == [
        {"tag": "h1", "text": "Best Running Shoes"},
        {"tag": "h2", "text": "Cushioned Options"},
        {"tag": "h3", "text": "Budget Picks"},
    ]


def test_word_count_matches_main_text():
    result = extract_content(SAMPLE_HTML, SAMPLE_URL)

    assert result["word_count"] == len(result["main_text"].split())
    assert result["word_count"] > 0


def test_main_text_keeps_body_and_drops_boilerplate():
    result = extract_content(SAMPLE_HTML, SAMPLE_URL)

    assert "many varieties" in result["main_text"]
    assert "Copyright 2026" not in result["main_text"]


def test_empty_html_returns_empty_result():
    result = extract_content("   ", SAMPLE_URL)

    assert result == {
        "title": None,
        "meta_description": None,
        "headings": [],
        "main_text": "",
        "word_count": 0,
    }
