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

_DENIED_EXTENSIONS: frozenset[str] = frozenset(
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


def _is_faculty_news_article_path(parts: list[str]) -> bool:
    """Новости подразделения: /faculties/<подразделение>/news/<slug>/ (не сам листинг /news/)."""
    if len(parts) < 4 or parts[0] != "faculties":
        return False
    try:
        news_idx = parts.index("news")
    except ValueError:
        return False
    return news_idx < len(parts) - 1


def is_probable_uniyar_article_url(url: str) -> bool:
    """Карточка материала: не разводящая страница и не пагинация листинга."""
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()
    if host not in {"www.uniyar.ac.ru", "uniyar.ac.ru"}:
        return False
    query_l = (parsed.query or "").lower()
    if "pagen_" in query_l:
        return False
    parts = [p for p in (parsed.path or "").strip("/").split("/") if p]
    if len(parts) < 3:
        return False
    if parts[0] in {"news", "events", "pressroom"}:
        return True
    return _is_faculty_news_article_path(parts)


def should_skip_crawl_url(url: str) -> bool:
    """Не следовать за медиа, служебными путями Bitrix и файловым выдачей."""
    parsed = urlparse(url)
    path_l = (parsed.path or "").lower()
    for sub in _DENIED_PATH_SUBSTRINGS:
        if sub in path_l:
            return True
    suffix = PurePosixPath(path_l).suffix
    if suffix:
        ext = suffix.lstrip(".").lower()
        if ext in _DENIED_EXTENSIONS:
            return True
    return False
