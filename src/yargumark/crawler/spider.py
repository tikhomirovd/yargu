from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any
from urllib.parse import urlparse

import trafilatura
from scrapy import Request, Spider
from scrapy.http import Response
from scrapy.http.response.text import TextResponse
from scrapy.linkextractors import LinkExtractor

from yargumark.config import get_settings
from yargumark.crawler.items import UniyarDocumentItem
from yargumark.crawler.title import extract_article_title
from yargumark.crawler.urlnorm import (
    CRAWL_DENY_FILE_EXTENSIONS,
    LINK_EXTRACTOR_DENY_PATTERNS,
    normalize_document_url,
    should_index_uniyar_page,
)
from yargumark.db import get_connection

# Одна точка входа: главная. Остальной сайт добирается LinkExtractor в глубину.
DEFAULT_SEED_URLS: tuple[str, ...] = ("https://www.uniyar.ac.ru/",)

_UNIYAR_LINK_EXTRACTOR = LinkExtractor(
    allow_domains=["uniyar.ac.ru", "www.uniyar.ac.ru"],
    deny=LINK_EXTRACTOR_DENY_PATTERNS,
    deny_extensions=CRAWL_DENY_FILE_EXTENSIONS,
)


def _fallback_title_from_url(url: str) -> str:
    parsed = urlparse(url)
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if not parts:
        return (parsed.netloc or url)[:300]
    slug = parts[-1].replace("-", " ").replace("_", " ")
    return (slug if len(slug) > 2 else url)[:300]


class UniyarSpider(Spider):
    """Обход сайта в глубину; сохранение через Item → pipeline (как в yagu)."""

    name = "uniyar"
    allowed_domains = ("uniyar.ac.ru", "www.uniyar.ac.ru")

    def __init__(
        self,
        only_new: str | bool = False,
        max_depth: str | int = 5,
        link_limit: str | int = 200,
        extra_start_urls: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.only_new = str(only_new).lower() in {"1", "true", "yes", "y"}
        self._known_normalized_urls: set[str] = set()
        if self.only_new:
            settings = get_settings()
            with get_connection(settings.db_path) as conn:
                rows = conn.execute("SELECT url FROM documents").fetchall()
            self._known_normalized_urls = {
                normalize_document_url(str(r[0])) for r in rows if r and r[0]
            }
        self._max_depth = int(max_depth) if str(max_depth).isdigit() else 5
        self._link_limit = int(link_limit) if str(link_limit).isdigit() else 200
        seeds = list(DEFAULT_SEED_URLS)
        if extra_start_urls:
            seeds.extend(extra_start_urls)
        self._seed_urls = list(dict.fromkeys(seeds))

    def start_requests(self) -> Iterator[Request]:
        for url in self._seed_urls:
            yield Request(url=url, callback=self.parse)

    def _body_text(self, response: TextResponse) -> str:
        extracted = trafilatura.extract(
            response.text,
            include_comments=False,
            include_tables=True,
        )
        body = re.sub(r"\s+", " ", extracted or "").strip()
        if body:
            return body
        fallback = " ".join(response.css("body *::text").getall()[:2000])
        return re.sub(r"\s+", " ", fallback).strip()

    def parse(self, response: Response) -> Iterator[Request | UniyarDocumentItem]:
        if not isinstance(response, TextResponse):
            return

        normalized = normalize_document_url(response.url)
        should_store = (not self.only_new) or (
            normalized not in self._known_normalized_urls
        )

        if should_index_uniyar_page(response.url):
            body = self._body_text(response)
            if body and should_store:
                title = extract_article_title(response.text, body).strip()
                if not title:
                    title = _fallback_title_from_url(response.url)
                yield UniyarDocumentItem(
                    url=response.url,
                    title=title,
                    body=body,
                    html_raw=response.text,
                    published_at=response.css(
                        "span.b-news__date-detail::text, time::attr(datetime)"
                    ).get(default=None),
                    source="uniyar",
                )
                self._known_normalized_urls.add(normalized)

        depth = int(response.meta.get("depth", 0) or 0)
        if depth >= self._max_depth:
            return

        for link in _UNIYAR_LINK_EXTRACTOR.extract_links(response)[: self._link_limit]:
            if not should_index_uniyar_page(link.url):
                continue
            yield response.follow(link.url, callback=self.parse)
