from zls_event_collect.models import NewsArticle
from zls_event_collect.normalizer import (
    extract_date_mentions,
    extract_event_date_ranges,
    extract_event_types,
    extract_venue_mentions,
    normalize_article,
)


def _article(*, title: str = "イベント開催", body: str = "本文") -> NewsArticle:
    return NewsArticle(
        title=title,
        published_at="2026-01-01",
        source_url="https://example.test/news/1",
        raw_text=body,
    )


def test_extract_event_types_is_deterministic_and_ordered() -> None:
    article = _article(
        title="LIVE上映＆コラボイベント開催",
        body="衣装展示とPOP UPフェアも実施します。",
    )

    assert extract_event_types(article) == (
        "event",
        "live",
        "screening",
        "collaboration",
        "exhibition",
        "fair",
        "pop_up",
    )


def test_extract_date_mentions_carries_year_only_within_same_line() -> None:
    article = _article(
        body=(
            "開催日時：2027年4月23日（金）、4月24日（土）、4月25日（日）\n"
            "受付：2026年5月27日（水）18:00 ～ 6月7日（日）23:59\n"
            "別行：7月1日（水）12:00\n"
            "無効：2026年2月30日 25:99"
        )
    )

    mentions = extract_date_mentions(article)

    assert [mention.to_dict() for mention in mentions] == [
        {
            "raw_text": "開催日時：2027年4月23日（金）、4月24日（土）、4月25日（日）",
            "dates": ["2027-04-23", "2027-04-24", "2027-04-25"],
            "times": [],
        },
        {
            "raw_text": "受付：2026年5月27日（水）18:00 ～ 6月7日（日）23:59",
            "dates": ["2026-05-27", "2026-06-07"],
            "times": ["18:00", "23:59"],
        },
        {
            "raw_text": "別行：7月1日（水）12:00",
            "dates": [],
            "times": ["12:00"],
        },
    ]


def test_extract_date_mentions_normalizes_fullwidth_and_japanese_time() -> None:
    article = _article(body="２０２６年４月４日 午後１時３０分／午前１２時")

    mentions = extract_date_mentions(article)

    assert mentions[0].dates == ("2026-04-04",)
    assert mentions[0].times == ("13:30", "00:00")


def test_extract_date_mentions_carries_month_only_within_same_line() -> None:
    article = _article(body="開催日：2026年4月4日、5日\n別行：6日")

    mentions = extract_date_mentions(article)

    assert mentions[0].dates == ("2026-04-04", "2026-04-05")
    assert len(mentions) == 1


def test_extract_event_date_ranges_extracts_explicit_range() -> None:
    article = _article(
        body="・開催期間：2026年5月26日（火）～ 2026年5月31日（日）"
    )

    assert [item.to_dict() for item in extract_event_date_ranges(article)] == [
        {
            "raw_text": "・開催期間：2026年5月26日（火）～ 2026年5月31日（日）",
            "start_date": "2026-05-26",
            "end_date": "2026-05-31",
        }
    ]


def test_extract_event_date_ranges_keeps_listed_dates_separate() -> None:
    article = _article(body="開催日時：2027年4月23日、24日、25日")

    assert [item.to_dict() for item in extract_event_date_ranges(article)] == [
        {
            "raw_text": "開催日時：2027年4月23日、24日、25日",
            "start_date": "2027-04-23",
            "end_date": None,
        },
        {
            "raw_text": "開催日時：2027年4月23日、24日、25日",
            "start_date": "2027-04-24",
            "end_date": None,
        },
        {
            "raw_text": "開催日時：2027年4月23日、24日、25日",
            "start_date": "2027-04-25",
            "end_date": None,
        },
    ]


def test_extract_event_date_ranges_rolls_over_an_omitted_end_year() -> None:
    article = _article(body="開催期間：2026年12月31日～1月2日")

    assert [item.to_dict() for item in extract_event_date_ranges(article)] == [
        {
            "raw_text": "開催期間：2026年12月31日～1月2日",
            "start_date": "2026-12-31",
            "end_date": "2027-01-02",
        },
    ]


def test_extract_event_date_ranges_reads_lines_after_label_only_heading() -> None:
    article = _article(
        body=(
            "【公演日】\n"
            "2027年4月24日(土) 開演 16:00\n"
            "2027年4月25日(日) 開演 14:00\n"
            "【出演者】\n"
            "2027年5月1日発表"
        )
    )

    assert [item.to_dict() for item in extract_event_date_ranges(article)] == [
        {
            "raw_text": "2027年4月24日(土) 開演 16:00",
            "start_date": "2027-04-24",
            "end_date": None,
        },
        {
            "raw_text": "2027年4月25日(日) 開演 14:00",
            "start_date": "2027-04-25",
            "end_date": None,
        },
    ]


def test_extract_event_date_ranges_excludes_sales_and_application_periods() -> None:
    article = _article(
        body=(
            "申込期間：2026年4月1日～2026年4月2日\n"
            "販売期間：2026年4月3日～2026年4月4日\n"
            "発売日：2026年4月5日\n"
            "イベント開催日は2026年4月6日です"
        )
    )

    assert [item.to_dict() for item in extract_event_date_ranges(article)] == [
        {
            "raw_text": "イベント開催日は2026年4月6日です",
            "start_date": "2026-04-06",
            "end_date": None,
        }
    ]


def test_extract_venue_mentions_uses_only_explicit_labels() -> None:
    article = _article(
        body=(
            "【会場】\n"
            "SAGAアリーナ\n"
            "■開催場所：ぴあアリーナMM（1F） サミーブース\n"
            "■販売場所\n"
            "駅前不動産スタジアム 特設ブース\n"
            "販売場所：MAPPA ONLINE SHOP（\n"
            "https://example.test/shop\n"
            "）\n"
            "■開催期間\n"
            "2026年4月4日 10:00\n"
            "会場でお待ちしています"
        )
    )

    assert extract_venue_mentions(article) == (
        "SAGAアリーナ",
        "ぴあアリーナMM(1F) サミーブース",
        "駅前不動産スタジアム 特設ブース",
        "MAPPA ONLINE SHOP",
    )


def test_normalize_article_preserves_phase1_fields() -> None:
    article = _article(title="上映イベント開催", body="【会場】\nシアター")

    normalized = normalize_article(article).to_dict()

    assert normalized["title"] == article.title
    assert normalized["published_at"] == article.published_at
    assert normalized["source_url"] == article.source_url
    assert normalized["source"] == article.source
    assert normalized["raw_text"] == article.raw_text
    assert normalized["event_name"] == article.title
    assert normalized["event_types"] == ["event", "screening"]
    assert normalized["event_date_ranges"] == []
    assert normalized["venue_mentions"] == ["シアター"]
    assert normalized["normalization_version"] == 2
