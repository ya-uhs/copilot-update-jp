from __future__ import annotations

from datetime import datetime, timezone
from email.utils import format_datetime
from html import escape
from pathlib import Path
from xml.etree import ElementTree as ET

from dateutil import parser as date_parser

from scripts.common import DOCS_DIR, atomic_write


def _rfc2822(value: str) -> str:
    try:
        parsed = date_parser.parse(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        parsed = datetime.now(timezone.utc)
    return format_datetime(parsed)


def build_feed(articles: list[dict], site_url: str) -> str:
    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    latest_change = max(
        (article.get("processed_at") or article.get("published_at") or "" for article in articles),
        default=datetime.now(timezone.utc).isoformat(),
    )
    for name, text in (
        ("title", "Copilot Update Japanese RSS"),
        ("link", site_url),
        ("description", "Microsoft 365 Copilot と GitHub Copilot の公式更新情報"),
        ("language", "ja"),
        ("lastBuildDate", _rfc2822(latest_change)),
    ):
        ET.SubElement(channel, name).text = text
    for article in sorted(articles, key=lambda item: item.get("published_at", ""), reverse=True)[:200]:
        item = ET.SubElement(channel, "item")
        title = article.get("title_ja") or article.get("title_original") or "Untitled"
        summary = article.get("summary_ja") or article.get("excerpt_original") or ""
        changes = "".join(f"<li>{escape(str(change))}</li>" for change in article.get("changes", []))
        body = (
            f"<p><strong>Product:</strong> {escape(article.get('product') or 'unknown')}<br>"
            f"<strong>Status:</strong> {escape(article.get('status') or 'unknown')}<br>"
            f"<strong>Importance:</strong> {escape(article.get('importance') or 'low')}</p>"
            f"<p>{escape(summary)}</p>"
            + (f"<ul>{changes}</ul>" if changes else "")
            + f'<p><a href="{escape(article["source_url"], quote=True)}">Original Source</a></p>'
        )
        ET.SubElement(item, "title").text = title
        ET.SubElement(item, "link").text = article["source_url"]
        ET.SubElement(item, "guid", {"isPermaLink": "false"}).text = article["id"]
        ET.SubElement(item, "pubDate").text = _rfc2822(article.get("published_at", ""))
        ET.SubElement(item, "description").text = body
    ET.indent(rss, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(rss, encoding="unicode") + "\n"


def generate_feed(articles: list[dict], site_url: str, output: Path | None = None) -> None:
    # Build fully before replacing the existing feed, so a generation error cannot truncate it.
    content = build_feed(articles, site_url)
    atomic_write(output or DOCS_DIR / "feed.xml", content)
