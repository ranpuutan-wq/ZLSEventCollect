from pathlib import Path

import pytest

from zls_event_collect.parser import (
    HtmlStructureError,
    parse_news_detail,
    parse_news_list,
)


FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_news_list_extracts_urls_and_last_page() -> None:
    html = (FIXTURES / "news_list.html").read_text(encoding="utf-8")

    result = parse_news_list(html, "https://zombielandsaga.com/news/")

    assert result.article_urls == (
        "https://zombielandsaga.com/news/detail.php?id=100",
        "https://zombielandsaga.com/news/detail.php?id=101",
    )
    assert result.max_page == 5


def test_parse_news_detail_extracts_required_fields() -> None:
    html = (FIXTURES / "news_detail.html").read_text(encoding="utf-8")
    source_url = "https://zombielandsaga.com/news/detail.php?id=100"

    article = parse_news_detail(html, source_url)

    assert article.title == "立川シネマシティにて 上映決定！"
    assert article.published_at == "2025-07-29"
    assert article.source_url == source_url
    assert article.source == "zombielandsaga_official"
    assert "開催日" in article.raw_text


def test_parse_movie_news_list_extracts_urls_and_last_page() -> None:
    html = (FIXTURES / "movie_news_list.html").read_text(encoding="utf-8")

    result = parse_news_list(html, "https://zombielandsaga-movie.com/news/")

    assert result.article_urls == (
        "https://zombielandsaga-movie.com/news/detail.php?id=200",
        "https://zombielandsaga-movie.com/news/detail.php?id=201",
    )
    assert result.max_page == 4


def test_parse_movie_news_detail_extracts_required_fields() -> None:
    html = (FIXTURES / "movie_news_detail.html").read_text(encoding="utf-8")
    source_url = "https://zombielandsaga-movie.com/news/detail.php?id=200"

    article = parse_news_detail(html, source_url)

    assert article.title == "Blu-ray発売記念パネル展＆WEB抽選会開催決定"
    assert article.published_at == "2026-05-22"
    assert article.source_url == source_url
    assert article.source == "zombielandsaga_official"
    assert article.raw_text == (
        "ゲーマーズ各店でパネル展を開催します。\n"
        "スペシャルスタンディも展示します。"
    )
    assert "BACK TO LIST" not in article.raw_text


def test_parse_news_detail_rejects_changed_structure() -> None:
    with pytest.raises(HtmlStructureError, match="必須要素"):
        parse_news_detail(
            "<main id='news'><article>unknown layout</article></main>",
            "https://zombielandsaga.com/news/detail.php?id=999",
        )
