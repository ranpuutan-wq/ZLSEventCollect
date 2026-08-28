from __future__ import annotations

from dataclasses import dataclass

import requests

from zls_event_collect.collector import NewsCollector


BASE_URL = "https://zombielandsaga.com/news/"


def _list_html(article_ids: list[int], max_page: int = 1) -> str:
    items = "".join(
        f"<li class='article__list'><a class='article__list--link' "
        f"href='detail.php?id={article_id}'>article</a></li>"
        for article_id in article_ids
    )
    pages = "".join(
        f"<a href='?page={page}'>{page}</a>" for page in range(2, max_page + 1)
    )
    return f"<main id='news'>{items}{pages}</main>"


def _detail_html(title: str, body: str) -> str:
    return (
        "<main id='news'><time class='article__titles--time'>2025.01.02</time>"
        f"<h3 class='article__titles--title'>{title}</h3>"
        f"<div class='article__main'>{body}</div></main>"
    )


@dataclass
class FakeResponse:
    text: str
    status_code: int = 200

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, responses: dict[str, FakeResponse]) -> None:
        self.responses = responses
        self.requested_urls: list[str] = []

    def get(self, url: str, *, timeout: tuple[float, float]) -> FakeResponse:
        self.requested_urls.append(url)
        return self.responses.get(url, FakeResponse("", status_code=404))


def test_collector_continues_after_page_and_article_errors() -> None:
    first_url = f"{BASE_URL}detail.php?id=1"
    third_url = f"{BASE_URL}detail.php?id=3"
    broken_url = f"{BASE_URL}detail.php?id=4"
    session = FakeSession(
        {
            BASE_URL: FakeResponse(_list_html([1, 1], max_page=3)),
            f"{BASE_URL}?page=2": FakeResponse("server error", status_code=500),
            f"{BASE_URL}?page=3": FakeResponse(_list_html([3, 4])),
            first_url: FakeResponse(_detail_html("上映のお知らせ", "開催します")),
            third_url: FakeResponse(_detail_html("ライブのお知らせ", "本文です")),
            broken_url: FakeResponse("not found", status_code=404),
        }
    )

    articles = NewsCollector(base_urls=(BASE_URL,), session=session).collect()

    assert [article.source_url for article in articles] == [first_url, third_url]
    assert session.requested_urls.count(first_url) == 1


def test_collector_continues_when_one_source_is_unavailable() -> None:
    unavailable_url = "https://unavailable.example/news/"
    article_url = f"{BASE_URL}detail.php?id=1"
    session = FakeSession(
        {
            BASE_URL: FakeResponse(_list_html([1])),
            article_url: FakeResponse(_detail_html("上映のお知らせ", "開催します")),
            unavailable_url: FakeResponse("server error", status_code=500),
        }
    )

    articles = NewsCollector(
        base_urls=(unavailable_url, BASE_URL),
        session=session,
    ).collect()

    assert [article.source_url for article in articles] == [article_url]
