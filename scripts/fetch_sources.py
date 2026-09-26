from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any, Callable

import feedparser
import requests
from bs4 import BeautifulSoup, Tag
from dateutil import parser as date_parser

from scripts.common import USER_AGENT, clean_text, normalize_title, now_iso, stable_id
from scripts.config import load_config

LOGGER = logging.getLogger(__name__)
TIMEOUT = 25
COPILOT_TERMS = ("copilot", "github copilot")


def _iso_date(value: str | None) -> str:
    if not value:
        return now_iso()
    try:
        parsed = date_parser.parse(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    except (ValueError, TypeError, OverflowError):
        return now_iso()


def _base_article(**values: Any) -> dict[str, Any]:
    return {
        **values,
        "title_ja": "",
        "summary_ja": "",
        "changes": [],
        "product": values.get("product", ""),
        "target_user": [],
        "status": values.get("status", "unknown"),
        "importance": "low",
        "translated": False,
        "processed_at": None,
    }


def fetch_rss(url: str, source: str, prefix: str, product: str, require_copilot: bool, keywords=None) -> list[dict[str, Any]]:
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    response.raise_for_status()
    parsed = feedparser.parse(response.content)
    if parsed.bozo and not parsed.entries:
        raise ValueError(f"Invalid feed: {parsed.bozo_exception}")
    items = []
    for entry in parsed.entries:
        title = clean_text(entry.get("title"))
        summary_html = entry.get("summary") or entry.get("description") or ""
        summary = clean_text(BeautifulSoup(summary_html, "html.parser").get_text(" "))
        tags = " ".join(tag.get("term", "") for tag in entry.get("tags", []))
        searchable = f"{title} {summary} {tags}".casefold()
        if require_copilot and not any(term.casefold() in searchable for term in (keywords or COPILOT_TERMS)):
            continue
        link = entry.get("link", "").strip()
        guid = entry.get("id") or entry.get("guid") or link
        if not title or not link:
            continue
        items.append(_base_article(
            id=stable_id(prefix, guid), source=source, source_url=link,
            published_at=_iso_date(entry.get("published") or entry.get("updated")),
            title_original=title, excerpt_original=summary[:6000], product=product,
            status="unknown",
        ))
    return items


def fetch_cli_releases(config) -> list[dict[str, Any]]:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT}
    if os.getenv("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    response = requests.get(config['url'], headers=headers, params={"per_page": config.get('limit', 30)}, timeout=TIMEOUT)
    response.raise_for_status()
    changelog: dict[str, str] = {}
    try:
        changelog_response = requests.get(config['changelog_url'], headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
        changelog_response.raise_for_status()
        sections = re.split(r"(?m)^##\s+", changelog_response.text)
        for section in sections[1:]:
            first_line, _, body = section.partition("\n")
            version = first_line.split(" - ", 1)[0].strip().removeprefix("v")
            if version:
                changelog[version] = clean_text(body)[:10000]
    except Exception as exc:
        # Releases remain publishable even if the supplementary changelog is unavailable.
        LOGGER.warning("Could not fetch Copilot CLI changelog.md: %s", exc)
    items = []
    for release in response.json():
        if release.get("draft"):
            continue
        release_id = str(release["id"])
        tag = clean_text(release.get("tag_name"))
        # GitHub returns Markdown here; treating it as HTML can misread short release notes as a path.
        body = clean_text(release.get("body") or "") or changelog.get(tag.removeprefix("v"), "")
        items.append(_base_article(
            id=f"github-copilot-cli-{release_id}", source="GitHub Copilot CLI Releases",
            source_url=release.get("html_url", ""),
            published_at=_iso_date(release.get("published_at") or release.get("created_at")),
            title_original=f"GitHub Copilot CLI {tag}", excerpt_original=body[:10000],
            product="GitHub Copilot CLI", status="Pre-release" if release.get("prerelease") else "Release",
        ))
    return items


def fetch_m365_release_notes(config) -> list[dict[str, Any]]:
    response = requests.get(config['url'], headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    main = soup.select_one("main") or soup
    items = []
    for heading in main.find_all("h2"):
        label = clean_text(heading.get_text(" "))
        if not re.search(r"\b20\d{2}\b", label):
            continue
        chunks: list[str] = []
        for sibling in heading.next_siblings:
            if isinstance(sibling, Tag) and sibling.name == "h2":
                break
            if isinstance(sibling, Tag):
                text = clean_text(sibling.get_text(" "))
                if text:
                    chunks.append(text)
        excerpt = clean_text(" ".join(chunks))[:12000]
        anchor = heading.get("id") or re.sub(r"[^a-z0-9]+", "-", label.casefold()).strip("-")
        url = f"{config['url']}#{anchor}"
        items.append(_base_article(
            id=stable_id("m365-release-notes", label), source="Microsoft 365 Copilot Release Notes",
            source_url=url, published_at=_iso_date(label),
            title_original=f"Microsoft 365 Copilot release notes — {label}",
            excerpt_original=excerpt, product="Microsoft 365 Copilot", status="Release",
        ))
    return items


def fetch_vscode_updates(config) -> list[dict[str, Any]]:
    response = requests.get(config['url'], headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    title = clean_text(soup.h1.get_text(" "))
    released = re.search(r"Released\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})", soup.get_text(" ", strip=True))
    chunks = []
    for heading in soup.find_all("h2"):
        label = clean_text(heading.get_text(" "))
        if not re.search(r"copilot|chat|agents?", label, re.I):
            continue
        chunks.append(label)
        for sibling in heading.next_siblings:
            if isinstance(sibling, Tag) and sibling.name == "h2":
                break
            if isinstance(sibling, Tag):
                chunks.append(clean_text(sibling.get_text(" ")))
    if not chunks:
        raise ValueError("No Copilot/Chat/Agents sections found in VS Code release notes")
    return [_base_article(
        id=stable_id("vscode", response.url), source="VS Code Release Notes",
        source_url=response.url, published_at=_iso_date(released.group(1)) if released else now_iso(),
        date_basis="published" if released else "first_seen",
        title_original=f"{title} — Copilot / Chat / Agents",
        excerpt_original="\n".join(chunks)[:12000], product="GitHub Copilot in VS Code", status="Release",
    )]


def fetch_m365_roadmap(config) -> list[dict[str, Any]]:
    items = fetch_rss(
        config['url'],
        "Microsoft 365 Roadmap", "m365-roadmap", "Microsoft 365 Copilot", True,
    )
    # Roadmap dates describe plans, not evidence that a feature has shipped.
    for item in items:
        item["status"] = "Roadmap"
        item["content_type"] = "roadmap"
        item["title_original"] = "[Roadmap] " + item["title_original"]
    return sorted(items, key=lambda item: item["published_at"], reverse=True)[:config.get('limit', 30)]


ADAPTERS = {"cli": fetch_cli_releases, "m365_notes": fetch_m365_release_notes,
            "vscode": fetch_vscode_updates, "roadmap": fetch_m365_roadmap}


def _is_duplicate(candidate: dict[str, Any], articles: list[dict[str, Any]]) -> bool:
    title = normalize_title(candidate.get("title_original", ""))
    for current in articles:
        if candidate["id"] == current.get("id") or candidate.get("source_url") == current.get("source_url"):
            return True
        other = normalize_title(current.get("title_original", ""))
        if title and other and candidate.get("source") == current.get("source"):
            if candidate.get("source") in {"GitHub Copilot CLI Releases", "VS Code Release Notes", "Microsoft 365 Roadmap", "Microsoft 365 Copilot Release Notes"}:
                continue
            if title == other or SequenceMatcher(None, title, other).ratio() >= 0.96:
                return True
    return False


def fetch_all(existing: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    added: list[dict[str, Any]] = []
    errors: list[str] = []
    combined = list(existing)
    sources = load_config('sources')['sources']
    for source in sources:
        # Backfill stable source metadata without changing article IDs.
        for item in existing:
            if item.get('source_id') == source['id'] or item.get('source') == source['name']:
                item.update(source_id=source['id'], family=source['family'])
        if not source.get('enabled', True):
            continue
        try:
            if source['adapter'] == 'rss':
                fetched = fetch_rss(source['url'], source['name'], source['id'], source['product'], bool(source.get('keywords')), source.get('keywords'))
                fetched = fetched[:source.get('limit', len(fetched))]
            else:
                fetched = ADAPTERS[source['adapter']](source)
            for item in fetched:
                item.update(source_id=source['id'], source=source['name'], family=source['family'])
                if not _is_duplicate(item, combined):
                    added.append(item)
                    combined.append(item)
        except Exception as exc:  # one source must not block the rest
            message = f"{source['id']}: {exc}"
            LOGGER.exception(message)
            errors.append(message)
    return added, errors
