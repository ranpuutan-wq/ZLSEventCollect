# ZLSEventCollect

「ゾンビランドサガ」公式サイトの NEWS から、イベントに関係しそうな記事を収集して JSON に保存する Python アプリです。

Phase 1 では次の2つの公式 NEWS を対象にします。イベント情報の正規化、内容ベースの重複排除、Notion・X (Twitter)・LLM との連携は対象外です。

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
  "raw_text": "記事本文"
}
```

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
└── main.py       # 抽出、重複排除、JSON保存、CLI
```

Phase 1 の計画と受け入れ条件は [Issue #1](https://github.com/ranpuutan-wq/ZLSEventCollect/issues/1) にあります。
