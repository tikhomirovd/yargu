from __future__ import annotations

from yargumark.crawler.urlnorm import (
    normalize_document_url,
    should_index_uniyar_page,
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


def test_index_allows_listings_and_pagination() -> None:
    assert should_index_uniyar_page("https://www.uniyar.ac.ru/news/science/")
    assert should_index_uniyar_page("https://www.uniyar.ac.ru/news/main1443000/?PAGEN_1=2")
    assert should_index_uniyar_page("https://www.uniyar.ac.ru/faculties/economic/news/")


def test_index_rejects_non_http() -> None:
    assert not should_index_uniyar_page("mailto:a@b.c")


def test_index_rejects_wrong_host() -> None:
    assert not should_index_uniyar_page("https://example.com/foo")
