from __future__ import annotations

import argparse
import json
import logging
import os
import tempfile
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Final

from .collector import CollectionError, NewsCollector
from .models import NewsArticle, NormalizedEvent
from .normalizer import normalize_articles


logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_PATH: Final = Path("output/events.json")
EVENT_KEYWORDS: Final = (
    "開催",
    "イベント",
    "ライブ",
    "上映",
    "コラボ",
    "展示",
    "トークショー",
    "舞台挨拶",
    "フェア",
    "POP UP",
    "ポップアップ",
)


def is_event_candidate(article: NewsArticle) -> bool:
    haystack = f"{article.title}\n{article.raw_text}".casefold()
    return any(keyword.casefold() in haystack for keyword in EVENT_KEYWORDS)


def select_event_candidates(articles: Iterable[NewsArticle]) -> list[NewsArticle]:
    """キーワード抽出とURL単位の重複排除を順序を保って行う。"""

    events: list[NewsArticle] = []
    seen_urls: set[str] = set()
    for article in articles:
        if article.source_url in seen_urls or not is_event_candidate(article):
            continue
        seen_urls.add(article.source_url)
        events.append(article)
    events.sort(key=lambda article: article.published_at, reverse=True)
    return events


def write_events(events: Sequence[NormalizedEvent], output_path: Path) -> None:
    """途中失敗で既存JSONを壊さないよう、一時ファイルから置換する。"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=output_path.parent,
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(
                [event.to_dict() for event in events],
                temporary_file,
                ensure_ascii=False,
                indent=2,
            )
            temporary_file.write("\n")
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, output_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def run(output_path: Path = DEFAULT_OUTPUT_PATH) -> int:
    collector = NewsCollector()
    try:
        articles = collector.collect()
        candidates = select_event_candidates(articles)
        events = normalize_articles(candidates)
        write_events(events, output_path)
    except CollectionError as exc:
        logger.error("収集に失敗しました: %s", exc)
        return 1
    except OSError as exc:
        logger.error("JSONの保存に失敗しました: %s", exc)
        return 1
    except Exception as exc:  # 最上位で未処理例外によるクラッシュを防ぐ
        logger.error("予期しないエラーが発生しました: %s", exc)
        logger.debug("予期しないエラーの詳細", exc_info=True)
        return 1
    finally:
        collector.close()

    logger.info(
        "正規化イベント候補を %d 件、%s に保存しました", len(events), output_path
    )
    return 0


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="ゾンビランドサガ公式NEWSからイベント候補を収集します。"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="出力JSONのパス（既定: output/events.json）",
    )
    parser.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        default="INFO",
        help="ログレベル（既定: INFO）",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    return run(args.output)
