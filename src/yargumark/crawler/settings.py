from __future__ import annotations

BOT_NAME = "YarGuMarkBot"

SPIDER_MODULES = ["yargumark.crawler"]
NEWSPIDER_MODULE = "yargumark.crawler"

ROBOTSTXT_OBEY = True
DOWNLOAD_DELAY = 0
USER_AGENT = "YarGuMarkBot/0.1 (academic; tikhomirovd00@gmail.com)"

LOG_LEVEL = "INFO"
