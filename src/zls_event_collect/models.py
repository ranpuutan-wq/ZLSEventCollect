from dataclasses import dataclass
from typing import Final, Literal


SOURCE_NAME: Final = "zombielandsaga_official"
NORMALIZATION_VERSION: Final = 2

EventType = Literal[
    "event",
    "live",
    "screening",
    "collaboration",
    "exhibition",
    "talk_show",
    "stage_greeting",
    "fair",
    "pop_up",
]


@dataclass(frozen=True, slots=True)
class NewsArticle:
    """公式NEWSの記事1件を表す。"""

    title: str
    published_at: str
    source_url: str
    raw_text: str
    source: str = SOURCE_NAME

    def to_dict(self) -> dict[str, str]:
        return {
            "title": self.title,
            "published_at": self.published_at,
            "source_url": self.source_url,
            "source": self.source,
            "raw_text": self.raw_text,
        }


@dataclass(frozen=True, slots=True)
class DateMention:
    """日付・時刻を含む原文行と、その決定的な正規化結果。"""

    raw_text: str
    dates: tuple[str, ...]
    times: tuple[str, ...]

    def to_dict(self) -> dict[str, str | list[str]]:
        return {
            "raw_text": self.raw_text,
            "dates": list(self.dates),
            "times": list(self.times),
        }


@dataclass(frozen=True, slots=True)
class EventDateRange:
    """開催日または開催期間と、その抽出根拠。"""

    raw_text: str
    start_date: str
    end_date: str | None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "raw_text": self.raw_text,
            "start_date": self.start_date,
            "end_date": self.end_date,
        }


@dataclass(frozen=True, slots=True)
class NormalizedEvent:
    """Phase 1の記事情報と根拠付きの正規化情報。"""

    title: str
    published_at: str
    source_url: str
    source: str
    raw_text: str
    event_name: str
    event_types: tuple[EventType, ...]
    date_mentions: tuple[DateMention, ...]
    event_date_ranges: tuple[EventDateRange, ...]
    venue_mentions: tuple[str, ...]
    normalization_version: int = NORMALIZATION_VERSION

    def to_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "published_at": self.published_at,
            "source_url": self.source_url,
            "source": self.source,
            "raw_text": self.raw_text,
            "event_name": self.event_name,
            "event_types": list(self.event_types),
            "date_mentions": [mention.to_dict() for mention in self.date_mentions],
            "event_date_ranges": [
                date_range.to_dict() for date_range in self.event_date_ranges
            ],
            "venue_mentions": list(self.venue_mentions),
            "normalization_version": self.normalization_version,
        }
