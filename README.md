# ZLSEventCollect

「ゾンビランドサガ」公式サイトの NEWS から、イベントに関係しそうな記事を収集し、根拠付きの正規化情報を JSON に保存する Python アプリです。

Phase 2 では次の2つの公式 NEWS を対象にします。内容ベースの重複排除、Notion・X (Twitter)・LLM との連携は対象外です。

- [TV アニメ「ゾンビランドサガ リベンジ」公式 NEWS](https://zombielandsaga.com/news/)
- [劇場版「ゾンビランドサガ ゆめぎんがパラダイス」公式 NEWS](https://zombielandsaga-movie.com/news/)

## 必要環境

- Python 3.12 以降
- インターネット接続

## セットアップ

PowerShell の例です。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
```

## 実行

```powershell
python -m zls_event_collect
```

実行ログを表示しながら両サイトの全 NEWS ページをたどり、イベント候補を公開日の新しい順で UTF-8 の `output/events.json` に保存します。一方のサイトで取得エラーが発生しても、もう一方の収集は継続します。別の出力先やログレベルも指定できます。

```powershell
python -m zls_event_collect --output output/custom-events.json --log-level DEBUG
```

出力される各記事の形式は次のとおりです。

```json
{
  "title": "記事タイトル",
  "published_at": "2025-07-29",
  "source_url": "https://zombielandsaga-movie.com/news/detail.php?id=...",
  "source": "zombielandsaga_official",
  "raw_text": "記事本文",
  "event_name": "公式記事タイトル",
  "event_types": ["event", "live"],
  "date_mentions": [
    {
      "raw_text": "開催日時：2027年4月24日(土) 開演 16:00",
      "dates": ["2027-04-24"],
      "times": ["16:00"]
    }
  ],
  "event_date_ranges": [
    {
      "raw_text": "開催期間：2027年4月24日(土)～2027年4月25日(日)",
      "start_date": "2027-04-24",
      "end_date": "2027-04-25"
    }
  ],
  "venue_mentions": ["SAGAアリーナ"],
  "normalization_version": 2
}
```

正規化された日付・時刻には必ず元の記述を `raw_text` として残します。`date_mentions` は記事中の日付候補を広く保持し、`event_date_ranges` は「開催期間」「開催日時」「公演日」などの明示ラベルまたは開催表現がある箇所だけを開催日程として保持します。明示された期間は `start_date` / `end_date`、単日は `start_date` と `end_date: null` で表します。列挙された複数日は連続期間と推定せず、単日を複数件出力します。申込期間、販売期間、発売日は開催日程に含めません。

Phase 3 の Notion 連携では、`event_date_ranges[].start_date` をNotion日付プロパティの `start`、`end_date` を `end` に写像します。1記事に複数の開催日程がある場合は、`event_date_ranges` の要素ごとに独立したイベントとしてNotionへ登録します。ツール側では分割前の根拠を失わないよう、記事単位の配列として保持します。年や月が省略された日付は、同じ原文行に先行する値がある場合だけ補完します。会場は「会場」「開催場所」「開催店舗」「販売場所」の明示ラベルがある場合だけ候補として取り出します。

タイトルまたは本文に次のいずれかを含む記事がイベント候補になります。

`開催`、`イベント`、`ライブ`、`上映`、`コラボ`、`展示`、`トークショー`、`舞台挨拶`、`フェア`、`POP UP`、`ポップアップ`

同一 URL は 1 件だけ出力します。一覧の一部ページ、個別記事、または一方の公式サイトで HTTP エラーや解析エラーが発生した場合は、警告を記録して残りを処理します。両方の公式サイトから有効な記事を1件も取得できない場合は、エラーを記録して終了コード `1` を返します。

## テスト

```powershell
python -m pytest
```

HTML 解析テストは `tests/fixtures/` の保存済み HTML を使うため、公式サイトへの通信なしで実行できます。

## 構成

```text
src/zls_event_collect/
├── collector.py  # HTTP取得、ページング、失敗時の継続
├── parser.py     # 一覧・詳細HTMLの解析
├── models.py     # 出力データモデル
├── normalizer.py # 種別・日付・時刻・会場候補の正規化
└── main.py       # 抽出、正規化、重複排除、JSON保存、CLI
```

Phase 2 の計画と受け入れ条件は [Issue #3](https://github.com/ranpuutan-wq/ZLSEventCollect/issues/3)、開催期間の追補仕様は [Issue #5](https://github.com/ranpuutan-wq/ZLSEventCollect/issues/5) にあります。
