from __future__ import annotations

from typing import Any

BOT_NAME = "YarGuMarkBot"

SPIDER_MODULES = ["yargumark.crawler"]
NEWSPIDER_MODULE = "yargumark.crawler"

ROBOTSTXT_OBEY = True

USER_AGENT = "YarGuMarkBot/0.1 (academic; tikhomirovd00@gmail.com)"

# Вежливый режим: 503 у CDN часто из‑за пачки запросов (robots + сиды + ретраи).
# Один слот на домен + пауза снижают шанс словить «перегруз» при старте.
DOWNLOAD_DELAY = 2.0
RANDOMIZE_DOWNLOAD_DELAY = 0.5
CONCURRENT_REQUESTS = 1
CONCURRENT_REQUESTS_PER_DOMAIN = 1

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1.0
AUTOTHROTTLE_MAX_DELAY = 12.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 0.5

# Transient 503/502 on busy sites: default RETRY_TIMES=2 is often too few.
RETRY_TIMES = 5

DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ru,en;q=0.8,en-US;q=0.5",
    "Upgrade-Insecure-Requests": "1",
    # Часть фронтов/CDN ожидает «навигационный» профиль запроса (браузер шлёт Sec-Fetch-*).
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
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
        "AUTOTHROTTLE_TARGET_CONCURRENCY": AUTOTHROTTLE_TARGET_CONCURRENCY,
        "RETRY_TIMES": RETRY_TIMES,
        "DEFAULT_REQUEST_HEADERS": DEFAULT_REQUEST_HEADERS,
        "TWISTED_REACTOR": TWISTED_REACTOR,
        "FEED_EXPORT_ENCODING": FEED_EXPORT_ENCODING,
        "LOG_LEVEL": LOG_LEVEL,
        "ITEM_PIPELINES": ITEM_PIPELINES,
    }
