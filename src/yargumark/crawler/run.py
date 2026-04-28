from __future__ import annotations

from scrapy.crawler import CrawlerProcess
from scrapy.settings import Settings

from yargumark.crawler.settings import (
    BOT_NAME,
    DOWNLOAD_DELAY,
    LOG_LEVEL,
    NEWSPIDER_MODULE,
    ROBOTSTXT_OBEY,
    SPIDER_MODULES,
    USER_AGENT,
)
from yargumark.crawler.spider import UniyarSpider


def run_crawler() -> None:
    scrapy_settings = Settings(
        {
            "BOT_NAME": BOT_NAME,
            "SPIDER_MODULES": SPIDER_MODULES,
            "NEWSPIDER_MODULE": NEWSPIDER_MODULE,
            "ROBOTSTXT_OBEY": ROBOTSTXT_OBEY,
            "DOWNLOAD_DELAY": DOWNLOAD_DELAY,
            "USER_AGENT": USER_AGENT,
            "LOG_LEVEL": LOG_LEVEL,
        }
    )
    process = CrawlerProcess(scrapy_settings)
    process.crawl(UniyarSpider)
    process.start()
