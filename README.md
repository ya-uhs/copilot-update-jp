# Copilot Update Japanese RSS Aggregator

Microsoft 365 Copilot、GitHub Copilot、GitHub Copilot CLI の公式更新情報を取得し、日本語で整理して静的WebページとRSS 2.0を生成します。GitHub Pages + GitHub Actionsだけで動作し、LLMが利用できない場合も英語原文で配信を継続します。

## 対象ソース

- [GitHub Changelog](https://github.blog/changelog/)（Copilot関連のみ）
- [GitHub Copilot CLI Releases](https://github.com/github/copilot-cli/releases)
- [Microsoft 365 Blog](https://www.microsoft.com/en-us/microsoft-365/blog/)（Copilot関連のみ）
- [Microsoft 365 Copilot release notes](https://learn.microsoft.com/en-us/microsoft-365/copilot/release-notes)
- [VS Code Release Notes](https://code.visualstudio.com/updates)（最新安定版のCopilot・Chat・Agents節）
- [Microsoft 365 Roadmap](https://www.microsoft.com/microsoft-365/roadmap)（Copilot関連の最新30件。StatusはRoadmap）

Roadmapは予定情報であり、GA予定日が書かれていても提供開始とは判断しません。現在は初回取得時のスナップショットを保存し、同じIDの後日変更は追跡しません。VS Codeもバージョンごとに1記事です。翻訳は無料枠と実行時間を抑えるため1回最大10件（`MAX_TRANSLATIONS_PER_RUN`で変更可能）、新しい順に処理します。

## セットアップ

1. このリポジトリをGitHubへpushします。
2. Settings → Secrets and variables → Actionsで `GEMINI_API_KEY` と `GROQ_API_KEY` を登録します。片方だけでも、両方なしでも更新処理は動作します。
3. Settings → Pagesで Source を `GitHub Actions` に設定します。更新workflowが `docs` を直接デプロイします。
4. Actionsの `Update Copilot feed` を手動実行します。以後は日本時間 7:00、13:00、19:00 頃に自動実行されます。

Webページには、公式ソースを最後に確認した日時、最新記事の公開日時、翻訳済み件数を表示します。新着が0件でも `docs/status.json` を更新するため、定期実行が動いたことを確認できます。

必要に応じてRepository Variablesで `GEMINI_MODEL`、`GROQ_MODEL` を変更できます。既定値はそれぞれ `gemini-3.5-flash-lite`、`openai/gpt-oss-120b` です。APIキーはRepository Secretsへ登録します。モデルの提供状況・無料枠はプロバイダーにより変わります。

## ソースとRSSの設定

`config/sources.toml` でURL、enabled、family、取得件数を管理します。RSSは `adapter = "rss"` として追加でき、`keywords` で絞れます。独自HTML/APIの場合はPython側のadapter追加が必要です。既存の `id` は変更しないでください。無効にしても保存済み記事は残ります。

`config/feeds.toml` で配信条件を管理します。`family`、`content_type`、`importance`、`translated_only`、`days`、`sort`、`limit` を組み合わせられます。次回Actions実行時に反映されます。

| RSSパス | 内容 |
|---|---|
| `feed.xml` | 最新200件 |
| `feeds/important.xml` | 翻訳済み・重要度high |
| `feeds/top10.xml` | 過去7日の翻訳済み記事、重要度優先で最大10件 |
| `feeds/microsoft365.xml` | Microsoft 365関連 |
| `feeds/github.xml` | GitHub Copilot、CLI、VS Code |
| `feeds/roadmap.xml` | Roadmap予定情報 |

Top10は人気順ではありません。同じ重要度では新しい記事を優先します。リーダー側の表示順は異なることがあります。未翻訳は重要度未判定として重要更新・Top10から除外します。週刊ダイジェスト形式ではなく、通常の1記事1itemです。

各RSSは固定GUID、self URL、カテゴリ、キャッシュ時間のヒントを出力します。クエリパラメータによる動的絞り込みは行いません。Webページの「RSSを選んで購読」からURLを選択できます。

## ローカル実行

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
GEMINI_API_KEY=... GROQ_API_KEY=... python -m scripts.update
python -m http.server 8000 --directory docs
```

キーを設定しなければ、取得・JSON保存・Web/RSS生成だけを検証できます。未翻訳記事は `translated: false` で保存され、次回以降も翻訳を再試行します。

## 障害時の動作

- 取得元ごとに例外を分離し、1ソースの失敗で他ソースを止めません。
- GeminiのHTTPエラー、timeout、rate limit、不正JSON等はすべてGroqへfallbackします。
- 両方が失敗した記事も英語タイトルとexcerptで公開します。
- `articles.json` の既存IDは再処理せず、未翻訳記事だけをLLMへ再送します。
- feedとサイトデータは一時ファイルで完成させてから置換するため、生成途中の失敗で既存ファイルを空にしません。

## データと拡張

正本は `data/articles.json`、Pages向けコピーは `docs/data.json` です。取得元は `scripts/fetch_sources.py` のfetcher、LLMは `scripts/providers/` のadapterとして追加できます。記事数が増えた場合は、`load_articles` / `save_articles` の境界を保ったまま年月別ファイルへ移行できます。
