from __future__ import annotations

import json
from pathlib import Path

from scripts.common import DOCS_DIR, atomic_write


def generate_site(articles: list[dict], output_dir: Path | None = None) -> None:
    target = output_dir or DOCS_DIR
    public = [{key: value for key, value in article.items() if key != "llm_provider"} for article in articles]
    atomic_write(target / "data.json", json.dumps(public, ensure_ascii=False, indent=2) + "\n")

