from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any
from urllib.parse import urljoin, urlparse

import scrapy
import trafilatura
from scrapy import Request
from scrapy.http import Response

from yargumark.config import get_settings
from yargumark.crawler.title import extract_article_title
from yargumark.crawler.urlnorm import (
    is_probable_uniyar_article_url,
    normalize_document_url,
    should_skip_crawl_url,
)
from yargumark.db import DocumentRecord, get_connection, upsert_document

START_URLS = (
    "http://www.uniyar.ac.ru/news/main1443000/?PAGEN_1=1",
    "http://www.uniyar.ac.ru/events/?PAGEN_1=1",
    "http://www.uniyar.ac.ru/pressroom/?PAGEN_1=1",
)

_ALLOWED_PREFIXES = ("http://www.uniyar.ac.ru/", "https://www.uniyar.ac.ru/")


class UniyarSpider(scrapy.Spider):
    name = "uniyar"
    allowed_domains = ("uniyar.ac.ru", "www.uniyar.ac.ru")

    def __init__(
        self,
        only_new: str | bool = False,
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

    def start_requests(self) -> Iterator[Request]:
        for url in START_URLS:
            yield Request(url=url, callback=self.parse)

    def parse(self, response: Response) -> Iterator[Request]:
        link_selector = (
            "a[href^='/news/']::attr(href), "
            "a[href^='/events/']::attr(href), "
            "a[href^='/pressroom/']::attr(href), "
            "a[href^='http://www.uniyar.ac.ru/news/']::attr(href), "
            "a[href^='https://www.uniyar.ac.ru/news/']::attr(href), "
            "a[href^='http://www.uniyar.ac.ru/events/']::attr(href), "
            "a[href^='https://www.uniyar.ac.ru/events/']::attr(href), "
            "a[href^='http://www.uniyar.ac.ru/pressroom/']::attr(href), "
            "a[href^='https://www.uniyar.ac.ru/pressroom/']::attr(href)"
        )
        article_links = response.css(link_selector).getall()
        for href in article_links:
            absolute_url = urljoin(response.url, href)
            if not any(absolute_url.startswith(p) for p in _ALLOWED_PREFIXES):
                continue
            path = urlparse(absolute_url).path or ""
            if not (
                path.startswith("/news/")
                or path.startswith("/events/")
                or path.startswith("/pressroom/")
            ):
                continue
            if not is_probable_uniyar_article_url(absolute_url):
                continue
            if should_skip_crawl_url(absolute_url):
                continue
            normalized = normalize_document_url(absolute_url)
            if self.only_new and normalized in self._known_normalized_urls:
                continue
            yield response.follow(absolute_url, callback=self.parse_article)

        next_page_link = response.css("a[rel='next']::attr(href)").get()
        if next_page_link is None:
            next_page_link = response.xpath(
                "//a[contains(normalize-space(), 'Следующая')]/@href"
            ).get()
        if next_page_link is not None:
            np_abs = urljoin(response.url, next_page_link)
            if not should_skip_crawl_url(np_abs):
                normal_np = normalize_document_url(np_abs)
                if not self.only_new or normal_np not in self._known_normalized_urls:
                    yield response.follow(next_page_link, callback=self.parse)

    def parse_article(self, response: Response) -> None:
        if should_skip_crawl_url(response.url) or not is_probable_uniyar_article_url(
            response.url
        ):
            return
        extracted = trafilatura.extract(response.text, include_comments=False, include_tables=True)
        body = re.sub(r"\s+", " ", extracted or "").strip()
        title = extract_article_title(response.text, body)
        if not title or not body:
            return

        published_at = response.css("span.b-news__date-detail::text, time::attr(datetime)").get(
            default=None
        )

        settings = get_settings()
        with get_connection(settings.db_path) as connection:
            upsert_document(
                connection,
                DocumentRecord(
                    url=response.url,
                    title=title,
                    body=body,
                    html_raw=response.text,
                    published_at=published_at,
                    source="uniyar",
                ),
            )
            connection.commit()
        if self.only_new:
            self._known_normalized_urls.add(normalize_document_url(response.url))
