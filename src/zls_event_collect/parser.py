from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from .models import NewsArticle


logger = logging.getLogger(__name__)

LIST_LAYOUTS: tuple[tuple[str, str], ...] = (
    ("#news .article__list", ".article__list--link[href]"),
    ("#news .newsLists__item", ".newsLists__link[href]"),
)
DETAIL_LAYOUTS: tuple[tuple[str, str, str], ...] = (
    (
        "#news .article__titles--title",
        "#news .article__titles--time",
        "#news .article__main",
    ),
    (
        "#news .newsDetail__title--text",
        "#news .newsDetail__title--time",
        "#news .newsDetail__text",
    ),
)


class HtmlStructureError(ValueError):
    """期待するHTML要素を取得できない場合のエラー。"""


@dataclass(frozen=True, slots=True)
class NewsListPage:
    article_urls: tuple[str, ...]
    max_page: int


def _single_line_text(element: Tag) -> str:
    return " ".join(element.get_text(" ", strip=True).split())


def _multiline_text(element: Tag) -> str:
    lines = (" ".join(line.split()) for line in element.get_text("\n").splitlines())
    return "\n".join(line for line in lines if line)


def _page_number(url: str) -> int | None:
    raw_page = parse_qs(urlparse(url).query).get("page", [None])[0]
    if raw_page is None or not re.fullmatch(r"[1-9]\d*", raw_page):
        return None
    return int(raw_page)


def parse_news_list(html: str, page_url: str) -> NewsListPage:
    """NEWS一覧HTMLから記事URLと最終ページ番号を取り出す。"""

    soup = BeautifulSoup(html, "html.parser")
    article_urls: list[str] = []

    selected_layout: tuple[str, str] | None = None
    for item_selector, link_selector in LIST_LAYOUTS:
        if soup.select_one(item_selector) is not None:
            selected_layout = (item_selector, link_selector)
            break
    if selected_layout is None:
        raise HtmlStructureError("既知の記事一覧レイアウトが見つかりませんでした")

    item_selector, link_selector = selected_layout
    for item in soup.select(item_selector):
        link = item.select_one(link_selector)
        if link is None:
            logger.warning("記事一覧にリンクのない項目があるためスキップします")
            continue
        href = link.get("href")
        if not isinstance(href, str) or not href.strip():
            logger.warning("記事一覧に空のリンクがあるためスキップします")
            continue
        article_urls.append(urljoin(page_url, href.strip()))

    if not article_urls:
        raise HtmlStructureError("記事一覧から有効な記事URLを取得できませんでした")

    current_page = _page_number(page_url) or 1
    page_numbers = [current_page]
    for link in soup.select("#news a[href]"):
        href = link.get("href")
        if not isinstance(href, str):
            continue
        number = _page_number(urljoin(page_url, href.strip()))
        if number is not None:
            page_numbers.append(number)

    return NewsListPage(tuple(article_urls), max(page_numbers))


def parse_news_detail(html: str, source_url: str) -> NewsArticle:
    """NEWS詳細HTMLから記事データを取り出す。"""

    soup = BeautifulSoup(html, "html.parser")
    title_element = None
    date_element = None
    body_element = None
    for title_selector, date_selector, body_selector in DETAIL_LAYOUTS:
        candidate_title = soup.select_one(title_selector)
        candidate_date = soup.select_one(date_selector)
        candidate_body = soup.select_one(body_selector)
        if all((candidate_title, candidate_date, candidate_body)):
            title_element = candidate_title
            date_element = candidate_date
            body_element = candidate_body
            break

    if title_element is None or date_element is None or body_element is None:
        raise HtmlStructureError("記事詳細の必須要素が既知のレイアウトにありません")

    assert title_element is not None
    assert date_element is not None
    assert body_element is not None

    title = _single_line_text(title_element)
    raw_date = _single_line_text(date_element)
    raw_text = _multiline_text(body_element)
    if not title or not raw_text:
        raise HtmlStructureError("記事詳細のタイトルまたは本文が空です")

    try:
        published_at = datetime.strptime(raw_date, "%Y.%m.%d").date().isoformat()
    except ValueError as exc:
        raise HtmlStructureError(f"公開日の形式を解釈できません: {raw_date}") from exc

    return NewsArticle(
        title=title,
        published_at=published_at,
        source_url=source_url,
        raw_text=raw_text,
    )
