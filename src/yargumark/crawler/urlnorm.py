from __future__ import annotations

from pathlib import PurePosixPath
from urllib.parse import urldefrag, urlparse

_DENIED_PATH_SUBSTRINGS: tuple[str, ...] = (
    "/upload/",
    "/bitrix/",
    "/photos/",
    "/gallery/",
    "/video/",
    "/media/",
)

# Scrapy LinkExtractor.deny patterns (regex against full URL).
LINK_EXTRACTOR_DENY_PATTERNS: tuple[str, ...] = (
    r"/upload/",
    r"/bitrix/",
    r"/photos/",
    r"/gallery/",
    r"/video/",
    r"/media/",
)

# Для LinkExtractor.deny_extensions (как в yagu).
CRAWL_DENY_FILE_EXTENSIONS: frozenset[str] = frozenset(
    {
        "7z",
        "avi",
        "bmp",
        "csv",
        "doc",
        "docx",
        "epub",
        "gif",
        "gz",
        "jpeg",
        "jpg",
        "mp3",
        "mp4",
        "ods",
        "odt",
        "ogg",
        "pdf",
        "png",
        "ppt",
        "pptx",
        "rar",
        "rtf",
        "svg",
        "tar",
        "tgz",
        "tif",
        "tiff",
        "webm",
        "webp",
        "xls",
        "xlsx",
        "xml",
        "zip",
    }
)


def normalize_document_url(url: str) -> str:
    """Убрать фрагмент и хвостовой слэш для сравнения «уже видели эту страницу»."""
    clean, _fragment = urldefrag(url)
    return clean.rstrip("/")


def should_skip_crawl_url(url: str) -> bool:
    """Не ходить на медиа, служебные пути Bitrix и файловые URL."""
    parsed = urlparse(url)
    path_l = (parsed.path or "").lower()
    for sub in _DENIED_PATH_SUBSTRINGS:
        if sub in path_l:
            return True
    suffix = PurePosixPath(path_l).suffix
    if suffix:
        ext = suffix.lstrip(".").lower()
        if ext in CRAWL_DENY_FILE_EXTENSIONS:
            return True
    return False


def should_index_uniyar_page(url: str) -> bool:
    """Широкий режим: любая страница сайта, кроме явных медиа/bitrix (см. should_skip_crawl_url)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.netloc or "").lower()
    if host not in {"www.uniyar.ac.ru", "uniyar.ac.ru"}:
        return False
    return not should_skip_crawl_url(url)
