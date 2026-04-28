from __future__ import annotations

import re
import warnings

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

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
        "все события",
        "все новости",
        "пресс-центр",
    }
)

# Подстроки типичных «не заголовков»: хлебные крошки, ссылки в сайдбаре (uniyar и др.)
_NAV_NOISE_SUBSTRINGS: tuple[str, ...] = (
    "ссылка на все события",
    "ссылка на все новости",
    "ссылка на все материалы",
    "ссылка на архив",
    "перейти ко всем",
    "вернуться к списку",
)

# Сначала ищем заголовок статьи в основной колонке (до общего обхода DOM).
_CONTENT_HEADING_SELECTORS: tuple[str, ...] = (
    "main h1",
    "article h1",
    "[itemprop=headline]",
    ".b-news h1",
    ".b-news__title",
    "h1.b-news__title",
    ".content h1",
    ".main-content h1",
    "#workarea h1",
    ".news-detail h1",
    ".detail h1",
)

_SITE_SUFFIX_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\s*[-—–|]\s*ЯрГУ.*$", flags=re.IGNORECASE),
    re.compile(
        r"\s*[-—–|]\s*Ярославский государственный университет.*$",
        flags=re.IGNORECASE,
    ),
    re.compile(r"\s*[-—–|]\s*www\.uniyar\.ac\.ru.*$", flags=re.IGNORECASE),
    re.compile(r"\s*[-—–|]\s*Демидов.*$", flags=re.IGNORECASE),
)

# Полное официальное имя вуза как отдельный «шапочный» h1 на uniyar (не заголовок материала).
# Сравнение по строке после `_normalize_for_brand_match` (без пунктуации).
_BRANDING_FULL_NAME_NORM: re.Pattern[str] = re.compile(
    r"^ярославский\s+государственный\s+университет\s+им\s+п\s+г\s+демидова$",
)

_BRANDING_SHORT_LINE: re.Pattern[str] = re.compile(
    r"^официальный\s+сайт\s+яргу\b",
    flags=re.IGNORECASE,
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


def _normalize_for_brand_match(text: str) -> str:
    """Сжать пробелы и пунктуацию для сравнения с шаблоном шапки сайта."""
    s = _clean(text).casefold()
    s = re.sub(r"[^\w\s]+", " ", s, flags=re.UNICODE)
    return _WHITESPACE_RE.sub(" ", s).strip()


def is_site_branding_title(text: str) -> bool:
    """Текст совпадает с официальным названием сайта / шапкой, а не с заголовком материала."""
    c = _clean(text)
    if not c:
        return False
    norm = _normalize_for_brand_match(c)
    if _BRANDING_FULL_NAME_NORM.match(norm):
        return True
    if _BRANDING_SHORT_LINE.match(norm):
        return True
    return False


def _is_navigation_noise(text: str) -> bool:
    """Тексты навигации/«все события», ошибочно попадающие в og:title или первый h1."""
    cf = text.casefold().strip()
    if not cf:
        return True
    for sub in _NAV_NOISE_SUBSTRINGS:
        if sub in cf:
            return True
    # Короткая строка-ссылка из меню
    return bool(cf.startswith("ссылка на ") and len(cf) <= 48)


def _is_useful(text: str) -> bool:
    if not text:
        return False
    if text.casefold() in _SECTION_BLACKLIST:
        return False
    if _is_navigation_noise(text):
        return False
    return len(text) >= 4


def _is_good_article_heading(text: str) -> bool:
    """Полезный заголовок материала: не секция, не навигация, не шапка с названием вуза."""
    if not _is_useful(text):
        return False
    if is_site_branding_title(text):
        return False
    return True


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


def _first_good_heading_from_selectors(soup: BeautifulSoup) -> str:
    for selector in _CONTENT_HEADING_SELECTORS:
        for node in soup.select(selector):
            text = _clean(node.get_text())
            if _is_good_article_heading(text):
                return text
    return ""


def _first_heading_from_tags(soup: BeautifulSoup) -> str:
    for tag_name in ("h1", "h2", "h3"):
        for tag in soup.find_all(tag_name):
            text = _clean(tag.get_text())
            if _is_good_article_heading(text):
                return text
    return ""


def extract_article_title(html: str, body: str = "") -> str:
    """Best-effort article title extraction from HTML, with body fallback.

    Priority:
      1. <meta property="og:title"> (если не навигация и не шапка сайта)
      2. Заголовок в основной колонке (main / .content / …), пропуская шапку с именем вуза
      3. <title> с отсечением типичного суффикса сайта (если не шаблон «только вуз»)
      4. Любой подходящий h1–h3
      5. Первая фраза из извлечённого body (trafilatura)
      6. Пустая строка
    """
    soup = BeautifulSoup(html or "", "html.parser")

    og = soup.find("meta", attrs={"property": "og:title"})
    og_content = ""
    if og is not None:
        raw = og.get("content", "") if hasattr(og, "get") else ""
        og_content = str(raw) if raw else ""
    og_candidate = _strip_site_suffix(_clean(og_content))
    if _is_good_article_heading(og_candidate):
        return og_candidate

    from_content = _first_good_heading_from_selectors(soup)
    if from_content:
        return from_content

    title_tag = soup.find("title")
    title_text = _clean(title_tag.get_text() if title_tag is not None else "")
    title_stripped = _strip_site_suffix(title_text)
    if _is_good_article_heading(title_stripped):
        return title_stripped

    from_generic = _first_heading_from_tags(soup)
    if from_generic:
        return from_generic

    return _first_sentence(body)


def is_blacklisted_title(title: str) -> bool:
    """Считать заголовок «плохим» для бэкфилла: секция, навигация, шапка вуза, пусто."""
    c = _clean(title)
    if not c:
        return True
    if c.casefold() in _SECTION_BLACKLIST:
        return True
    if _is_navigation_noise(c):
        return True
    if is_site_branding_title(c):
        return True
    return False
