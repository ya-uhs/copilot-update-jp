from __future__ import annotations

from datetime import datetime, timezone, timedelta
from email.utils import format_datetime
from html import escape
from pathlib import Path
from xml.etree import ElementTree as ET

from dateutil import parser as date_parser

from scripts.common import DOCS_DIR, atomic_write
from scripts.config import load_config

ET.register_namespace('atom', 'http://www.w3.org/2005/Atom')


def select_articles(articles, config, now=None):
    now = now or datetime.now(timezone.utc)
    result = []
    for article in articles:
        if any(config.get(key) and article.get(key) != config[key] for key in ('family', 'content_type')):
            continue
        if config.get('translated_only') and not article.get('translated'):
            continue
        if config.get('importance') and article.get('importance') not in config['importance']:
            continue
        if config.get('days'):
            date = date_parser.parse(article['published_at'])
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
            if not now - timedelta(days=config['days']) <= date <= now:
                continue
        result.append(article)
    result.sort(key=lambda a: a.get('published_at', ''), reverse=True)
    if config.get('sort') == 'importance':
        result.sort(key=lambda a: {'high': 3, 'medium': 2, 'low': 1}.get(a.get('importance'), 0), reverse=True)
    return result[:config.get('limit', 200)]


def _rfc2822(value: str) -> str:
    try:
        parsed = date_parser.parse(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        parsed = datetime.now(timezone.utc)
    return format_datetime(parsed)


def build_feed(articles: list[dict], site_url: str, config=None) -> str:
    config = config or {'path': 'feed.xml', 'title': 'Copilot Update Japanese RSS', 'limit': 200}
    articles = select_articles(articles, config)
    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    latest_change = max(
        (article.get("processed_at") or article.get("published_at") or "" for article in articles),
        default='1970-01-01T00:00:00Z',
    )
    for name, text in (
        ("title", config['title']),
        ("link", site_url),
        ("description", "Microsoft 365 Copilot と GitHub Copilot の公式更新情報"),
        ("language", "ja"),
        ("lastBuildDate", _rfc2822(latest_change)),
    ):
        ET.SubElement(channel, name).text = text
    ET.SubElement(channel, '{http://www.w3.org/2005/Atom}link', {
        'href': site_url.rstrip('/') + '/' + config['path'], 'rel': 'self', 'type': 'application/rss+xml'})
    ET.SubElement(channel, 'ttl').text = '360'
    for article in articles:
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
        for category in (article.get('product'), article.get('status'), article.get('importance') if article.get('translated') else 'unclassified'):
            if category:
                ET.SubElement(item, 'category').text = category
    ET.indent(rss, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(rss, encoding="unicode") + "\n"


def generate_feed(articles: list[dict], site_url: str, output: Path | None = None) -> None:
    # Build fully before replacing the existing feed, so a generation error cannot truncate it.
    content = build_feed(articles, site_url)
    atomic_write(output or DOCS_DIR / "feed.xml", content)


def generate_feeds(articles, site_url):
    import logging
    import json
    catalog = []
    for config in load_config('feeds')['feeds']:
        path = Path(config['path'])
        if path.is_absolute() or '..' in path.parts or path.suffix != '.xml':
            raise ValueError('Invalid feed output path')
        try:
            content = build_feed(articles, site_url, config)
            # Only change lastBuildDate when this particular feed changes.
            target = DOCS_DIR / path
            if target.exists():
                old = ET.fromstring(target.read_text())
                new = ET.fromstring(content)
                old_date = old.find('./channel/lastBuildDate')
                new_date = new.find('./channel/lastBuildDate')
                if old_date is not None and new_date is not None:
                    saved = old_date.text
                    old_date.text = new_date.text = ''
                    new_date.text = saved if ET.tostring(old) == ET.tostring(new) else datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')
                    content = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(new, encoding='unicode') + '\n'
            atomic_write(target, content)
            catalog.append({'title': config['title'], 'path': config['path']})
        except Exception:
            logging.exception('Feed generation failed: %s; existing file preserved', path)
    atomic_write(DOCS_DIR / 'feeds.json', json.dumps(catalog, ensure_ascii=False, indent=2) + '\n')
