import json
import unittest
from unittest.mock import patch

from scripts.fetch_sources import _is_duplicate
from scripts.summarize import parse_result, summarize_article


class CoreTests(unittest.TestCase):
    def test_duplicate_by_similar_title_in_same_source(self):
        existing = [{"id": "one", "source_url": "https://a", "source": "GitHub Changelog", "title_original": "Copilot is now faster!"}]
        candidate = {"id": "two", "source_url": "https://b", "source": "GitHub Changelog", "title_original": "Copilot is now faster"}
        self.assertTrue(_is_duplicate(candidate, existing))

    def test_parse_json_fence_and_validate(self):
        raw = "```json\n" + json.dumps({
            "title_ja": "更新", "summary_ja": "変更です。", "changes": ["改善"],
            "product": "GitHub Copilot", "target_user": ["Developer"],
            "status": "GA", "importance": "medium"
        }, ensure_ascii=False) + "\n```"
        result = parse_result(raw)
        self.assertTrue(result["translated"])
        self.assertEqual(result["importance"], "medium")

    @patch("scripts.summarize._providers")
    def test_provider_fallback(self, providers):
        valid = json.dumps({
            "title_ja": "更新", "summary_ja": "変更です。", "changes": [],
            "product": "GitHub Copilot CLI", "target_user": ["Developer"],
            "status": "Release", "importance": "low"
        }, ensure_ascii=False)
        providers.return_value = [("Gemini", lambda _: "not json"), ("Groq", lambda _: valid)]
        article = {"id": "x", "source": "x", "title_original": "x", "excerpt_original": "x", "product": "x", "status": "unknown"}
        self.assertTrue(summarize_article(article))
        self.assertEqual(article["llm_provider"], "Groq")

    @patch("scripts.summarize._providers", return_value=[])
    def test_no_key_keeps_publishable_english(self, _providers):
        article = {"id": "x", "source": "x", "title_original": "English title", "excerpt_original": "English excerpt", "product": "x", "status": "unknown"}
        self.assertFalse(summarize_article(article))
        self.assertFalse(article["translated"])
        self.assertEqual(article["title_original"], "English title")


if __name__ == "__main__":
    unittest.main()

