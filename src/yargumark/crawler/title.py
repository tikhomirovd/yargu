from __future__ import annotations

import re

from bs4 import BeautifulSoup

_SECTION_BLACKLIST: frozenset[str] = frozenset(
    {
        "",
        "события",
        "новости",
        "пресс-релизы",
        "пресс-релиз",
        "press release",
        "news",
        "events",
        "главная",
        "untitled",
    }
)

_SITE_SUFFIX_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\s*[-—–|]\s*ЯрГУ.*$", flags=re.IGNORECASE),  # noqa: RUF001
    re.compile(r"\s*[-—–|]\s*Ярославский государственный университет.*$", flags=re.IGNORECASE),  # noqa: RUF001
    re.compile(r"\s*[-—–|]\s*www\.uniyar\.ac\.ru.*$", flags=re.IGNORECASE),  # noqa: RUF001
    re.compile(r"\s*[-—–|]\s*Демидов.*$", flags=re.IGNORECASE),  # noqa: RUF001
)

_WHITESPACE_RE = re.compile(r"\s+")


def _clean(text: str | None) -> str:
    if text is None:
        return ""
    cleaned = _WHITESPACE_RE.sub(" ", text).strip()
    return cleaned


def _strip_site_suffix(text: str) -> str:
    cleaned = text
    for pattern in _SITE_SUFFIX_PATTERNS:
        cleaned = pattern.sub("", cleaned).strip()
    return cleaned


def _is_useful(text: str) -> bool:
    if not text:
        return False
    if text.casefold() in _SECTION_BLACKLIST:
        return False
    return len(text) >= 4


def _first_sentence(body: str, max_len: int = 120) -> str:
    snippet = _clean(body)
    if not snippet:
        return ""
    match = re.search(r"[.!?]\s", snippet)
    if match is not None:
        end = match.start() + 1
        snippet = snippet[:end].strip()
    if len(snippet) > max_len:
        snippet = snippet[: max_len - 1].rstrip() + "…"
    return snippet


def extract_article_title(html: str, body: str = "") -> str:
    """Best-effort article title extraction from HTML, with body fallback.

    Priority:
      1. <meta property="og:title">
      2. <title> with known site-suffix stripped
      3. First non-section <h1>
      4. First non-section <h2>/<h3>
      5. First sentence of body (truncated)
      6. Empty string
    """
    soup = BeautifulSoup(html or "", "html.parser")

    og = soup.find("meta", attrs={"property": "og:title"})
    og_content = ""
    if og is not None:
        raw = og.get("content", "") if hasattr(og, "get") else ""
        og_content = str(raw) if raw else ""
    candidate = _clean(og_content)
    if _is_useful(candidate):
        return _strip_site_suffix(candidate)

    title_tag = soup.find("title")
    title_text = _clean(title_tag.get_text() if title_tag is not None else "")
    title_stripped = _strip_site_suffix(title_text)
    if _is_useful(title_stripped):
        return title_stripped

    for tag_name in ("h1", "h2", "h3"):
        for tag in soup.find_all(tag_name):
            text = _clean(tag.get_text())
            if _is_useful(text):
                return text

    return _first_sentence(body)


def is_blacklisted_title(title: str) -> bool:
    return _clean(title).casefold() in _SECTION_BLACKLIST
