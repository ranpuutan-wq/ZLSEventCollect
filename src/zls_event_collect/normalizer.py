from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from datetime import date

from .models import DateMention, EventType, NewsArticle, NormalizedEvent


EVENT_TYPE_RULES: tuple[tuple[EventType, tuple[str, ...]], ...] = (
    ("event", ("イベント", "開催")),
    ("live", ("ライブ", "live")),
    ("screening", ("上映",)),
    ("collaboration", ("コラボ",)),
    ("exhibition", ("展示",)),
    ("talk_show", ("トークショー",)),
    ("stage_greeting", ("舞台挨拶",)),
    ("fair", ("フェア",)),
    ("pop_up", ("pop up", "ポップアップ")),
)

DATE_TOKEN_PATTERN = re.compile(
    r"(?:(?P<year>\d{4})年\s*)?"
    r"(?P<month>\d{1,2})月\s*(?P<day>\d{1,2})日"
)
TIME_TOKEN_PATTERN = re.compile(
    r"(?<!\d)(?P<ampm>午前|午後)?\s*(?P<hour>\d{1,2})"
    r"(?::(?P<minute>\d{2})|時(?:(?P<jp_minute>\d{1,2})分)?)(?!\d)"
)
VENUE_LABEL_PATTERN = re.compile(
    r"^[\s■●◆◇▼▽・※]*[【\[]?"
    r"(?P<label>開催場所|開催店舗|販売場所|会場)"
    r"[】\]]?\s*(?:[：:]\s*(?P<value>.+))?$"
)


def _unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def extract_event_types(article: NewsArticle) -> tuple[EventType, ...]:
    text = unicodedata.normalize(
        "NFKC", f"{article.title}\n{article.raw_text}"
    ).casefold()
    return tuple(
        event_type
        for event_type, keywords in EVENT_TYPE_RULES
        if any(keyword.casefold() in text for keyword in keywords)
    )


def _extract_dates(line: str) -> tuple[str, ...]:
    current_year: int | None = None
    dates: list[str] = []
    for match in DATE_TOKEN_PATTERN.finditer(line):
        raw_year = match.group("year")
        if raw_year is not None:
            current_year = int(raw_year)
        if current_year is None:
            continue
        try:
            normalized = date(
                current_year,
                int(match.group("month")),
                int(match.group("day")),
            ).isoformat()
        except ValueError:
            continue
        dates.append(normalized)
    return _unique(dates)


def _normalize_time(match: re.Match[str]) -> str | None:
    hour = int(match.group("hour"))
    minute = int(match.group("minute") or match.group("jp_minute") or 0)
    ampm = match.group("ampm")

    if minute > 59:
        return None
    if ampm is None:
        if hour > 23:
            return None
    else:
        if not 1 <= hour <= 12:
            return None
        if ampm == "午前":
            hour = 0 if hour == 12 else hour
        elif hour != 12:
            hour += 12
    return f"{hour:02d}:{minute:02d}"


def _extract_times(line: str) -> tuple[str, ...]:
    return _unique(
        normalized
        for match in TIME_TOKEN_PATTERN.finditer(line)
        if (normalized := _normalize_time(match)) is not None
    )


def extract_date_mentions(article: NewsArticle) -> tuple[DateMention, ...]:
    mentions: list[DateMention] = []
    seen: set[tuple[str, tuple[str, ...], tuple[str, ...]]] = set()
    for raw_line in (article.title, *article.raw_text.splitlines()):
        raw_text = " ".join(raw_line.split())
        if not raw_text:
            continue
        normalized_line = unicodedata.normalize("NFKC", raw_text)
        dates = _extract_dates(normalized_line)
        times = _extract_times(normalized_line)
        if not dates and not times:
            continue
        key = (raw_text, dates, times)
        if key in seen:
            continue
        seen.add(key)
        mentions.append(DateMention(raw_text=raw_text, dates=dates, times=times))
    return tuple(mentions)


def _venue_value_is_usable(value: str) -> bool:
    normalized = unicodedata.normalize("NFKC", value)
    if not normalized or len(normalized) > 200:
        return False
    if normalized.startswith(("http://", "https://")):
        return False
    if DATE_TOKEN_PATTERN.search(normalized) or TIME_TOKEN_PATTERN.search(normalized):
        return False
    if VENUE_LABEL_PATTERN.fullmatch(normalized):
        return False
    if normalized.startswith(("【", "■", "●", "◆", "◇", "▼", "▽", "※")):
        return False
    return True


def _clean_venue_value(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", " ".join(value.split()))
    return normalized.rstrip(" ([{").strip()


def extract_venue_mentions(article: NewsArticle) -> tuple[str, ...]:
    lines = [" ".join(line.split()) for line in article.raw_text.splitlines()]
    venues: list[str] = []
    for index, raw_line in enumerate(lines):
        if not raw_line:
            continue
        line = unicodedata.normalize("NFKC", raw_line)
        match = VENUE_LABEL_PATTERN.fullmatch(line)
        if match is None:
            continue
        inline_value = match.group("value")
        if inline_value is not None:
            value = _clean_venue_value(inline_value)
            if _venue_value_is_usable(value):
                venues.append(value)
            continue
        if index + 1 >= len(lines):
            continue
        value = _clean_venue_value(lines[index + 1])
        if _venue_value_is_usable(value):
            venues.append(value)
    return _unique(venues)


def normalize_article(article: NewsArticle) -> NormalizedEvent:
    return NormalizedEvent(
        title=article.title,
        published_at=article.published_at,
        source_url=article.source_url,
        source=article.source,
        raw_text=article.raw_text,
        event_name=article.title,
        event_types=extract_event_types(article),
        date_mentions=extract_date_mentions(article),
        venue_mentions=extract_venue_mentions(article),
    )


def normalize_articles(articles: Iterable[NewsArticle]) -> list[NormalizedEvent]:
    return [normalize_article(article) for article in articles]
