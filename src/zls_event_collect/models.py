from dataclasses import dataclass
from typing import Final


SOURCE_NAME: Final = "zombielandsaga_official"


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
