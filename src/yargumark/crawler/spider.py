from __future__ import annotations

from collections.abc import Iterator
from urllib.parse import urljoin

import scrapy
from scrapy import Request
from scrapy.http import Response

from yargumark.config import get_settings
from yargumark.db import DocumentRecord, get_connection, upsert_document

START_URLS = (
    "https://uniyar.ac.ru/news/main1443000/?PAGEN_1=1",
    "https://uniyar.ac.ru/events/?PAGEN_1=1",
    "https://uniyar.ac.ru/pressroom/?PAGEN_1=1",
)


class UniyarSpider(scrapy.Spider):
    name = "uniyar"
    allowed_domains = ("uniyar.ac.ru",)

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
            if absolute_url.startswith("https://uniyar.ac.ru/"):
                yield response.follow(absolute_url, callback=self.parse_article)

        next_page_link = response.css("a[rel='next']::attr(href)").get()
        if next_page_link is None:
            next_page_link = response.xpath(
                "//a[contains(normalize-space(), 'Следующая')]/@href"
            ).get()
        if next_page_link is not None:
            yield response.follow(next_page_link, callback=self.parse)

    def parse_article(self, response: Response) -> None:
        title = response.css("h1::text, .news-detail-title::text").get(default="").strip()
        paragraph_selector = "article p::text, .news-detail p::text, .content p::text"
        paragraphs = response.css(paragraph_selector).getall()
        body = "\n".join(paragraph.strip() for paragraph in paragraphs if paragraph.strip())
        if not title or not body:
            return

        published_at = response.css("time::attr(datetime), .date::text").get(default=None)
        html_raw = response.text

        settings = get_settings()
        with get_connection(settings.db_path) as connection:
            upsert_document(
                connection,
                DocumentRecord(
                    url=response.url,
                    title=title,
                    body=body,
                    html_raw=html_raw,
                    published_at=published_at,
                    source="uniyar",
                ),
            )
            connection.commit()
