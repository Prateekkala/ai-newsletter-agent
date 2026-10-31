from __future__ import annotations

import calendar
import html
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import feedparser
import httpx

from .config import Source
from .models import Item

log = logging.getLogger(__name__)

USER_AGENT = "ai-newsletter-agent/0.1 (+https://github.com/)"
TAG_RE = re.compile(r"<[^>]+>")
SNIPPET_MAX = 500


def _clean(text: str) -> str:
    text = html.unescape(TAG_RE.sub(" ", text or ""))
    return re.sub(r"\s+", " ", text).strip()


def _entry_date(entry) -> datetime | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    return datetime.fromtimestamp(calendar.timegm(parsed), tz=timezone.utc)


def parse_feed(content: bytes | str, source: Source) -> list[Item]:
    """Turn raw feed XML into Items. Pure function, easy to test."""
    feed = feedparser.parse(content)
    items: list[Item] = []
    for entry in feed.entries:
        published = _entry_date(entry)
        title = _clean(entry.get("title", ""))
        url = entry.get("link", "")
        if not (published and title and url):
            continue
        snippet = _clean(entry.get("summary", ""))[:SNIPPET_MAX]
        items.append(
            Item(
                title=title,
                url=url,
                source=source.name,
                category=source.category,
                published=published,
                snippet=snippet,
            )
        )
    return items


def fetch_source(source: Source, client: httpx.Client) -> list[Item]:
    """Fetch one feed. Failures are logged and return [] so one bad feed never kills the run."""
    try:
        resp = client.get(source.url)
        resp.raise_for_status()
        return parse_feed(resp.content, source)
    except Exception as exc:  # noqa: BLE001 - we deliberately isolate per-source failures
        log.warning("Failed to fetch %s (%s): %s", source.name, source.url, exc)
        return []


def collect(sources: list[Source], days: int = 7, workers: int = 8) -> list[Item]:
    """Fetch all sources in parallel and keep items from the last `days` days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    with httpx.Client(
        timeout=20, follow_redirects=True, headers={"User-Agent": USER_AGENT}
    ) as client:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(lambda s: fetch_source(s, client), sources))
    items = [it for batch in results for it in batch if it.published >= cutoff]
    items.sort(key=lambda i: i.published, reverse=True)
    log.info("Collected %d items from %d sources", len(items), len(sources))
    return items
