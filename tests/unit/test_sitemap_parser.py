"""Unit tests for app/domain/sitemap_parser.py (pure, no network fetch).

Fixtures are inline XML strings — nothing here touches the network.
"""

from __future__ import annotations

from app.domain.sitemap_parser import parse_sitemap

URLSET_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://example.com/</loc>
    <lastmod>2026-01-01</lastmod>
  </url>
  <url>
    <loc>https://example.com/about</loc>
  </url>
  <url>
    <lastmod>2026-02-02</lastmod>
  </url>
</urlset>
"""

SITEMAPINDEX_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap>
    <loc>https://example.com/sitemap-posts.xml</loc>
    <lastmod>2026-03-03</lastmod>
  </sitemap>
  <sitemap>
    <loc>https://example.com/sitemap-pages.xml</loc>
  </sitemap>
</sitemapindex>
"""


def test_parse_urlset_returns_url_entries():
    result = parse_sitemap(URLSET_XML)

    assert result == [
        {"type": "url", "loc": "https://example.com/", "lastmod": "2026-01-01"},
        {"type": "url", "loc": "https://example.com/about", "lastmod": None},
    ]


def test_parse_urlset_skips_entries_without_loc():
    result = parse_sitemap(URLSET_XML)

    locs = [entry["loc"] for entry in result]
    assert "https://example.com/about" in locs
    assert len(result) == 2


def test_parse_sitemapindex_returns_sitemap_entries():
    result = parse_sitemap(SITEMAPINDEX_XML)

    assert result == [
        {
            "type": "sitemap",
            "loc": "https://example.com/sitemap-posts.xml",
            "lastmod": "2026-03-03",
        },
        {
            "type": "sitemap",
            "loc": "https://example.com/sitemap-pages.xml",
            "lastmod": None,
        },
    ]


def test_parse_handles_missing_namespace():
    xml = b"""<urlset>
      <url><loc>https://example.com/no-ns</loc></url>
    </urlset>"""

    result = parse_sitemap(xml)

    assert result == [
        {"type": "url", "loc": "https://example.com/no-ns", "lastmod": None}
    ]


def test_unknown_root_returns_empty_list():
    xml = b"<rss><channel></channel></rss>"

    assert parse_sitemap(xml) == []
