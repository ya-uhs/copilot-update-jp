from __future__ import annotations

import logging
import os

from scripts.common import load_articles, save_articles
from scripts.fetch_sources import fetch_all
from scripts.generate_feed import generate_feed
from scripts.generate_site import generate_site
from scripts.summarize import summarize_pending


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    articles = load_articles()
    added, source_errors = fetch_all(articles)
    articles.extend(added)
    translated, untranslated = summarize_pending(articles)
    save_articles(articles)
    site_url = os.getenv("SITE_URL", "https://example.github.io/copilot-update-jp/")
    try:
        generate_feed(articles, site_url)
    except Exception:
        logging.exception("Feed generation failed; the previous feed was preserved")
    try:
        generate_site(articles)
    except Exception:
        logging.exception("Site data generation failed; the previous data was preserved")
    logging.info(
        "Done: %d new, %d translated, %d untranslated, %d source errors",
        len(added), translated, untranslated, len(source_errors),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

