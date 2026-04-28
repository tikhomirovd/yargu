from __future__ import annotations

from typing import Any

BOT_NAME = "YarGuMarkBot"

SPIDER_MODULES = ["yargumark.crawler"]
NEWSPIDER_MODULE = "yargumark.crawler"

ROBOTSTXT_OBEY = True

USER_AGENT = "YarGuMarkBot/0.1 (academic; tikhomirovd00@gmail.com)"

# Как в yagu scraper: вежливый темп и ограничение параллелизма.
DOWNLOAD_DELAY = 1.0
RANDOMIZE_DOWNLOAD_DELAY = 0.3
CONCURRENT_REQUESTS = 4
CONCURRENT_REQUESTS_PER_DOMAIN = 4

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1.0
AUTOTHROTTLE_MAX_DELAY = 8.0

DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru,en;q=0.5",
}

TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

FEED_EXPORT_ENCODING = "utf-8"

LOG_LEVEL = "INFO"

ITEM_PIPELINES = {
    "yargumark.crawler.pipelines.YarguDocumentPipeline": 300,
}


def scrapy_settings_dict() -> dict[str, Any]:
    """Настройки для `scrapy.crawler.CrawlerProcess` / тестов."""
    return {
        "BOT_NAME": BOT_NAME,
        "SPIDER_MODULES": SPIDER_MODULES,
        "NEWSPIDER_MODULE": NEWSPIDER_MODULE,
        "ROBOTSTXT_OBEY": ROBOTSTXT_OBEY,
        "USER_AGENT": USER_AGENT,
        "DOWNLOAD_DELAY": DOWNLOAD_DELAY,
        "RANDOMIZE_DOWNLOAD_DELAY": RANDOMIZE_DOWNLOAD_DELAY,
        "CONCURRENT_REQUESTS": CONCURRENT_REQUESTS,
        "CONCURRENT_REQUESTS_PER_DOMAIN": CONCURRENT_REQUESTS_PER_DOMAIN,
        "AUTOTHROTTLE_ENABLED": AUTOTHROTTLE_ENABLED,
        "AUTOTHROTTLE_START_DELAY": AUTOTHROTTLE_START_DELAY,
        "AUTOTHROTTLE_MAX_DELAY": AUTOTHROTTLE_MAX_DELAY,
        "DEFAULT_REQUEST_HEADERS": DEFAULT_REQUEST_HEADERS,
        "TWISTED_REACTOR": TWISTED_REACTOR,
        "FEED_EXPORT_ENCODING": FEED_EXPORT_ENCODING,
        "LOG_LEVEL": LOG_LEVEL,
        "ITEM_PIPELINES": ITEM_PIPELINES,
    }
