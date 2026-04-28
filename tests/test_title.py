from __future__ import annotations

from yargumark.crawler.title import (
    extract_article_title,
    is_blacklisted_title,
    is_site_branding_title,
)


def test_branding_line_detected() -> None:
    assert is_site_branding_title(
        "Ярославский государственный университет им.\xa0П.Г.\xa0Демидова"
    )


def test_extract_prefers_article_heading_over_first_content_h1() -> None:
    html = """
    <html><head>
    <title>Article headline from title tag</title>
    </head><body>
    <div class="content">
      <h1>Ярославский государственный университет им. П.Г. Демидова</h1>
      <h1>Конференция по экологии прошла на биофаке</h1>
    </div>
    </body></html>
    """
    assert extract_article_title(html, "") == "Конференция по экологии прошла на биофаке"


def test_extract_skips_branding_og_and_uses_content() -> None:
    html = """
    <html><head>
    <meta property="og:title" content="Ярославский государственный университет им. П.Г. Демидова"/>
    <title>Ignored until later</title>
    </head><body>
    <div class="content"><h1>Реальный заголовок новости</h1></div>
    </body></html>
    """
    assert extract_article_title(html, "") == "Реальный заголовок новости"


def test_extract_uses_title_when_only_branding_in_body() -> None:
    html = """
    <html><head>
    <title>Заголовок только в title</title>
    </head><body>
    <div class="content">
      <h1>Ярославский государственный университет им. П.Г. Демидова</h1>
    </div>
    </body></html>
    """
    assert extract_article_title(html, "") == "Заголовок только в title"


def test_is_blacklisted_includes_branding() -> None:
    assert is_blacklisted_title("Ярославский государственный университет им. П.Г. Демидова")
