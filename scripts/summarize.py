from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Callable

from scripts.common import clean_text, now_iso
from scripts.providers import gemini, groq

LOGGER = logging.getLogger(__name__)
ALLOWED_IMPORTANCE = {"low", "medium", "high"}

PROMPT = """あなたは公式プロダクト更新情報を中立的に整理する編集者です。
以下の英語原文だけを根拠に、日本語の構造化要約を作成してください。

必須ルール:
- 技術的意味を保ち、過度な意訳をしない
- 原文にない内容を追加せず、推測しない
- Microsoft、GitHub、Copilot、CLI、VS Codeなどの固有名詞は原文表記を優先する
- 宣伝表現は中立化する
- summary_jaは2〜4文、changesは重要な変更2〜5項目（情報が少なければ無理に増やさない）
- statusは原文で判断できる場合だけ Preview / Public Preview / Rolling Out / GA / Release 等を設定し、不明なら unknown
- target_userは文字列の配列
- importanceは low / medium / high のいずれか
- JSONオブジェクトのみを返す

JSON schema:
{{"title_ja":"","summary_ja":"","changes":[],"product":"","target_user":[],"status":"unknown","importance":"low","translated":true}}

Source: {source}
Original title: {title}
Known product: {product}
Known status: {status}
Original text:
{text}
"""


def parse_result(raw: str) -> dict[str, Any]:
    value = raw.strip()
    if value.startswith("```"):
        value = re.sub(r"^```(?:json)?\s*|\s*```$", "", value, flags=re.IGNORECASE)
    data = json.loads(value)
    required = {"title_ja", "summary_ja", "changes", "product", "target_user", "status", "importance"}
    if not isinstance(data, dict) or not required.issubset(data):
        raise ValueError("LLM JSON is missing required fields")
    if not isinstance(data["changes"], list) or not isinstance(data["target_user"], list):
        raise ValueError("changes and target_user must be arrays")
    if data["importance"] not in ALLOWED_IMPORTANCE:
        raise ValueError("invalid importance")
    for key in ("title_ja", "summary_ja", "product", "status"):
        if not isinstance(data[key], str):
            raise ValueError(f"{key} must be a string")
        data[key] = clean_text(data[key])
    data["changes"] = [clean_text(str(item)) for item in data["changes"] if clean_text(str(item))][:5]
    data["target_user"] = [clean_text(str(item)) for item in data["target_user"] if clean_text(str(item))]
    data["translated"] = True
    return data


def _providers() -> list[tuple[str, Callable[[str], str]]]:
    providers = []
    if os.getenv("GEMINI_API_KEY"):
        providers.append(("Gemini", gemini.summarize))
    if os.getenv("GROQ_API_KEY"):
        providers.append(("Groq", groq.summarize))
    return providers


def summarize_article(article: dict[str, Any]) -> bool:
    prompt = PROMPT.format(
        source=article.get("source", ""), title=article.get("title_original", ""),
        product=article.get("product", ""), status=article.get("status", "unknown"),
        text=article.get("excerpt_original", "")[:12000],
    )
    for name, provider in _providers():
        try:
            result = parse_result(provider(prompt))
            article.update(result)
            if article.get("content_type") == "roadmap":
                article["status"] = "Roadmap"
                article["title_ja"] = "[提供予定・ロードマップ] " + article["title_ja"]
            article["processed_at"] = now_iso()
            article["llm_provider"] = name
            return True
        except Exception as exc:
            LOGGER.warning("%s failed for %s: %s", name, article.get("id"), exc)
    article["title_ja"] = ""
    article["summary_ja"] = ""
    article["changes"] = []
    article["translated"] = False
    if not article.get("processed_at"):
        article["processed_at"] = now_iso()
    article.pop("llm_provider", None)
    return False


def summarize_pending(articles: list[dict[str, Any]]) -> tuple[int, int]:
    success = failure = 0
    limit = max(0, int(os.getenv("MAX_TRANSLATIONS_PER_RUN", "10")))
    for article in sorted(articles, key=lambda item: item.get("published_at", ""), reverse=True):
        if article.get("translated") is True:
            continue
        if success + failure >= limit:
            break
        if summarize_article(article):
            success += 1
        else:
            failure += 1
    return success, failure
