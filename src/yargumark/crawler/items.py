from __future__ import annotations

import scrapy


class UniyarDocumentItem(scrapy.Item):
    """Страница для записи в `documents` (аналог PageItem в yagu)."""

    url = scrapy.Field()
    title = scrapy.Field()
    body = scrapy.Field()
    html_raw = scrapy.Field()
    published_at = scrapy.Field()
    source = scrapy.Field()
