import json

from zls_event_collect.main import (
    is_event_candidate,
    select_event_candidates,
    write_events,
)
from zls_event_collect.models import NewsArticle


def _article(url: str, *, title: str = "お知らせ", body: str = "本文") -> NewsArticle:
    return NewsArticle(
        title=title,
        published_at="2025-01-02",
        source_url=url,
        raw_text=body,
    )


def test_event_keyword_matching_is_case_insensitive() -> None:
    assert is_event_candidate(_article("https://example.test/1", body="pop up store"))
    assert not is_event_candidate(_article("https://example.test/2"))


def test_select_event_candidates_deduplicates_by_url() -> None:
    first = _article("https://example.test/1", title="イベント開催")
    duplicate = _article("https://example.test/1", title="ライブ開催")
    unrelated = _article("https://example.test/2")

    assert select_event_candidates([first, duplicate, unrelated]) == [first]


def test_select_event_candidates_sorts_multiple_sources_by_date() -> None:
    older = _article("https://zombielandsaga.com/news/detail.php?id=1", title="開催")
    newer = NewsArticle(
        title="コラボイベント",
        published_at="2026-08-26",
        source_url="https://zombielandsaga-movie.com/news/detail.php?id=2",
        raw_text="本文",
    )

    assert select_event_candidates([older, newer]) == [newer, older]


def test_write_events_outputs_utf8_json_with_required_fields(tmp_path) -> None:
    event = _article("https://example.test/1", title="上映決定", body="佐賀で開催")
    output_path = tmp_path / "output" / "events.json"

    write_events([event], output_path)

    raw = output_path.read_bytes()
    assert "上映決定".encode() in raw
    data = json.loads(raw.decode("utf-8"))
    assert data == [
        {
            "title": "上映決定",
            "published_at": "2025-01-02",
            "source_url": "https://example.test/1",
            "source": "zombielandsaga_official",
            "raw_text": "佐賀で開催",
        }
    ]
