from dataclasses import dataclass
from typing import Final, Literal


SOURCE_NAME: Final = "zombielandsaga_official"
NORMALIZATION_VERSION: Final = 1

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
            "venue_mentions": list(self.venue_mentions),
            "normalization_version": self.normalization_version,
        }
