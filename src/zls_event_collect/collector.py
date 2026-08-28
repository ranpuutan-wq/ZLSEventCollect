from __future__ import annotations

import logging
from collections.abc import Iterable
from collections.abc import Sequence
from typing import Final
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .models import NewsArticle
from .parser import HtmlStructureError, parse_news_detail, parse_news_list


logger = logging.getLogger(__name__)

DEFAULT_NEWS_URLS: Final = (
    "https://zombielandsaga.com/news/",
    "https://zombielandsaga-movie.com/news/",
)
DEFAULT_TIMEOUT: Final = (5.0, 30.0)
USER_AGENT: Final = "ZLSEventCollect/0.1 (+https://github.com/ranpuutan-wq/ZLSEventCollect)"


class CollectionError(RuntimeError):
    """収集を継続できない場合のエラー。"""


def _unique_urls(urls: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(urls))


def _new_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=2,
        connect=2,
        read=2,
        status=2,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": USER_AGENT})
    return session


class NewsCollector:
    """公式NEWSの一覧と詳細をHTTP経由で収集する。"""

    def __init__(
        self,
        base_urls: Sequence[str] = DEFAULT_NEWS_URLS,
        *,
        session: requests.Session | None = None,
        timeout: tuple[float, float] = DEFAULT_TIMEOUT,
    ) -> None:
        self.base_urls = tuple(base_url.rstrip("/") + "/" for base_url in base_urls)
        if not self.base_urls:
            raise ValueError("収集対象のNEWS URLを1件以上指定してください")
        self._session = session or _new_session()
        self._owns_session = session is None
        self._timeout = timeout

    def close(self) -> None:
        if self._owns_session:
            self._session.close()

    def _fetch(self, url: str) -> str:
        response = self._session.get(url, timeout=self._timeout)
        response.raise_for_status()
        return response.text

    def _collect_source(self, base_url: str) -> list[NewsArticle]:
        try:
            first_html = self._fetch(base_url)
            first_page = parse_news_list(first_html, base_url)
        except (requests.RequestException, HtmlStructureError) as exc:
            raise CollectionError(
                f"NEWS一覧を取得できませんでした: url={base_url} reason={exc}"
            ) from exc

        article_urls = list(first_page.article_urls)
        for page_number in range(2, first_page.max_page + 1):
            page_url = urljoin(base_url, f"?page={page_number}")
            try:
                page_html = self._fetch(page_url)
                page = parse_news_list(page_html, page_url)
            except (requests.RequestException, HtmlStructureError) as exc:
                logger.warning(
                    "NEWS一覧ページをスキップします: page=%s reason=%s",
                    page_number,
                    exc,
                )
                continue
            article_urls.extend(page.article_urls)

        article_urls = _unique_urls(article_urls)
        logger.info("記事URLを %d 件取得しました: source=%s", len(article_urls), base_url)

        articles: list[NewsArticle] = []
        for article_url in article_urls:
            try:
                detail_html = self._fetch(article_url)
                articles.append(parse_news_detail(detail_html, article_url))
            except (requests.RequestException, HtmlStructureError) as exc:
                logger.warning(
                    "NEWS記事をスキップします: url=%s reason=%s",
                    article_url,
                    exc,
                )

        if not articles:
            raise CollectionError("有効なNEWS記事を1件も取得できませんでした")

        logger.info("NEWS記事を %d 件解析しました: source=%s", len(articles), base_url)
        return articles

    def collect(self) -> list[NewsArticle]:
        articles: list[NewsArticle] = []
        for base_url in self.base_urls:
            try:
                articles.extend(self._collect_source(base_url))
            except CollectionError as exc:
                logger.warning("公式NEWSソースをスキップします: %s", exc)

        articles = list(
            {article.source_url: article for article in articles}.values()
        )
        if not articles:
            raise CollectionError("すべての公式NEWSソースから記事を取得できませんでした")
        return articles
