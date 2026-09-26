from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path

from scripts.common import DOCS_DIR, atomic_write
from scripts.config import load_config


def generate_site(articles: list[dict], output_dir: Path | None = None) -> None:
    target = output_dir or DOCS_DIR
    public = [{key: value for key, value in article.items() if key != "llm_provider"} for article in articles]
    atomic_write(target / "data.json", json.dumps(public, ensure_ascii=False, indent=2) + "\n")
    page = target / 'index.html'
    if page.exists():
        links = ''.join(f'<li><a href="{escape(f["path"], quote=True)}">{escape(f["title"].replace("Copilot Update — ", ""))}</a></li>' for f in load_config('feeds')['feeds'])
        content = re.sub(r'<!-- FEEDS_START -->.*?<!-- FEEDS_END -->', lambda _: '<!-- FEEDS_START --><ul id="feed-links">' + links + '</ul><!-- FEEDS_END -->', page.read_text(), flags=re.S)
        atomic_write(page, content)
