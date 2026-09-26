# Copilot Update Japanese RSS Aggregator

Microsoft 365 Copilot、GitHub Copilot、GitHub Copilot CLI の公式更新情報を取得し、日本語で整理して静的WebページとRSS 2.0を生成します。GitHub Pages + GitHub Actionsだけで動作し、LLMが利用できない場合も英語原文で配信を継続します。

## 対象ソース

- [GitHub Changelog](https://github.blog/changelog/)（Copilot関連のみ）
- [GitHub Copilot CLI Releases](https://github.com/github/copilot-cli/releases)
- [Microsoft 365 Blog](https://www.microsoft.com/en-us/microsoft-365/blog/)（Copilot関連のみ）
- [Microsoft 365 Copilot release notes](https://learn.microsoft.com/en-us/microsoft-365/copilot/release-notes)

## セットアップ

1. このリポジトリをGitHubへpushします。
2. Settings → Secrets and variables → Actionsで `GEMINI_API_KEY` と `GROQ_API_KEY` を登録します。片方だけでも、両方なしでも更新処理は動作します。
3. Settings → Pagesで Source を `Deploy from a branch`、branchを既定ブランチ、folderを `/docs` に設定します。
4. Actionsの `Update Copilot feed` を手動実行します。以後は日本時間 7:00、13:00、19:00 頃に自動実行されます。

必要に応じてRepository Variablesまたはworkflowのenvで `GEMINI_MODEL`、`GROQ_MODEL` を変更できます。既定値はそれぞれ `gemini-2.5-flash`、`llama-3.3-70b-versatile` です。

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

