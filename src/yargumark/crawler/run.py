from __future__ import annotations

import argparse
import sys

from scrapy.crawler import CrawlerProcess
from scrapy.settings import Settings

from yargumark.crawler.settings import scrapy_settings_dict
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
    parser.add_argument(
        "--start-url",
        action="append",
        default=[],
        metavar="URL",
        dest="extra_start_urls",
        help="Additional seed URL (repeatable). Default seed is https://www.uniyar.ac.ru/",
    )
    parser.add_argument(
        "--fast-local",
        action="store_true",
        help="Dev-only: no delay, autothrottle off (do not use against production servers).",
    )
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    settings_payload = scrapy_settings_dict()
    if args.fast_local:
        settings_payload = {**settings_payload}
        settings_payload["DOWNLOAD_DELAY"] = 0
        settings_payload["RANDOMIZE_DOWNLOAD_DELAY"] = 0
        settings_payload["AUTOTHROTTLE_ENABLED"] = False
        settings_payload["CONCURRENT_REQUESTS"] = 16
        settings_payload["CONCURRENT_REQUESTS_PER_DOMAIN"] = 16

    scrapy_settings = Settings(settings_payload)
    process = CrawlerProcess(scrapy_settings)
    process.crawl(
        UniyarSpider,
        max_depth=args.max_depth,
        link_limit=args.link_limit,
        only_new=args.only_new,
        extra_start_urls=args.extra_start_urls or None,
    )
    process.start()
