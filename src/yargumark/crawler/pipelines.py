from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from itemadapter import ItemAdapter

from yargumark.config import get_settings
from yargumark.crawler.items import UniyarDocumentItem
from yargumark.db import DocumentRecord, get_connection, upsert_document

if TYPE_CHECKING:
    from scrapy.crawler import Crawler

logger = logging.getLogger(__name__)


class YarguDocumentPipeline:
    """Write UniyarDocumentItem rows to SQLite; one connection per crawl (yagu-style).

    Scrapy 2.13+: hook methods omit ``spider``; use :meth:`from_crawler` / ``crawler`` if needed.
    """

    def __init__(self) -> None:
        self.crawler: Crawler | None = None

    @classmethod
    def from_crawler(cls, crawler: Crawler) -> YarguDocumentPipeline:
        pipe = cls()
        pipe.crawler = crawler
        return pipe

    def open_spider(self) -> None:
        settings = get_settings()
        self._connection = get_connection(settings.db_path)

    def close_spider(self) -> None:
        if hasattr(self, "_connection"):
            self._connection.close()

    def process_item(self, item: Any) -> Any:
        if not isinstance(item, UniyarDocumentItem):
            return item
        fields: dict[str, Any] = dict(ItemAdapter(item))
        url = str(fields.get("url") or "")
        title = str(fields.get("title") or "")
        body = str(fields.get("body") or "")
        html_raw = str(fields.get("html_raw") or "")
        src = str(fields.get("source") or "uniyar")
        if src not in ("uniyar", "demo"):
            src = "uniyar"
        published_raw = fields.get("published_at")
        published_at: str | None = (
            None if published_raw is None or published_raw == "" else str(published_raw)
        )
        if not url or not body:
            logger.warning("skip item: empty url or body for %s", url or "?")
            return item
        record = DocumentRecord(
            url=url,
            title=title,
            body=body,
            html_raw=html_raw,
            published_at=published_at,
            source=src,
        )
        upsert_document(self._connection, record)
        self._connection.commit()
        return item
