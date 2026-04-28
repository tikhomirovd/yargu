from __future__ import annotations

import re
from collections.abc import Iterator
from urllib.parse import urljoin

import scrapy
import trafilatura
from scrapy import Request
from scrapy.http import Response

from yargumark.config import get_settings
from yargumark.crawler.title import extract_article_title
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

    def start_requests(self) -> Iterator[Request]:
        for url in START_URLS:
            yield Request(url=url, callback=self.parse)

    def parse(self, response: Response) -> Iterator[Request]:
        link_selector = (
            "a[href*='/news/']::attr(href), "
            "a[href*='/events/']::attr(href), "
            "a[href*='/pressroom/']::attr(href)"
        )
        article_links = response.css(link_selector).getall()
        for href in article_links:
            absolute_url = urljoin(response.url, href)
            if any(absolute_url.startswith(p) for p in _ALLOWED_PREFIXES):
                yield response.follow(absolute_url, callback=self.parse_article)

        next_page_link = response.css("a[rel='next']::attr(href)").get()
        if next_page_link is None:
            next_page_link = response.xpath(
                "//a[contains(normalize-space(), 'Следующая')]/@href"
            ).get()
        if next_page_link is not None:
            yield response.follow(next_page_link, callback=self.parse)

    def parse_article(self, response: Response) -> None:
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
