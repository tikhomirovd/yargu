from __future__ import annotations

from yargumark.crawler.urlnorm import (
    is_probable_uniyar_article_url,
    normalize_document_url,
    should_skip_crawl_url,
)


def test_normalize_strips_fragment_and_trailing_slash() -> None:
    assert (
        normalize_document_url("https://www.uniyar.ac.ru/news/foo/#section")
        == "https://www.uniyar.ac.ru/news/foo"
    )


def test_skip_media_and_upload_paths() -> None:
    assert should_skip_crawl_url("https://www.uniyar.ac.ru/upload/file.pdf")
    assert should_skip_crawl_url("https://www.uniyar.ac.ru/foo/photo.jpg")


def test_allow_article_path() -> None:
    assert not should_skip_crawl_url(
        "https://www.uniyar.ac.ru/news/main1443000/v-demidovskom-universitete-napisali-diktantpobedy/"
    )


def test_article_url_requires_three_path_segments() -> None:
    assert is_probable_uniyar_article_url(
        "https://www.uniyar.ac.ru/news/science/na-fakultete-biologii-test/"
    )
    assert not is_probable_uniyar_article_url("https://www.uniyar.ac.ru/news/science/")
    assert not is_probable_uniyar_article_url(
        "https://www.uniyar.ac.ru/news/main1443000/?PAGEN_1=2"
    )


def test_faculty_news_listing_not_article() -> None:
    """Разводящая страница факультета без slug материала."""
    assert not is_probable_uniyar_article_url(
        "https://www.uniyar.ac.ru/faculties/economic/news/"
    )


def test_faculty_news_article_url() -> None:
    assert is_probable_uniyar_article_url(
        "https://www.uniyar.ac.ru/faculties/economic/news/zavershilsya-forum-kadry-ved/"
    )
