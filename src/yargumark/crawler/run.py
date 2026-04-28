from __future__ import annotations

import argparse
import sys

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


def run_crawler(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Crawl www.uniyar.ac.ru into YarguMark SQLite.")
    parser.add_argument(
        "-d",
        "--max-depth",
        type=int,
        default=5,
        metavar="N",
        help="Maximum depth from seed URLs (default 5). Higher = broader coverage.",
    )
    parser.add_argument(
        "--link-limit",
        type=int,
        default=200,
        metavar="N",
        help="Max internal links followed per page (default 200).",
    )
    parser.add_argument(
        "--only-new",
        action="store_true",
        help="Do not upsert pages whose URL is already in the database.",
    )
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

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
    process.crawl(
        UniyarSpider,
        max_depth=args.max_depth,
        link_limit=args.link_limit,
        only_new=args.only_new,
    )
    process.start()
