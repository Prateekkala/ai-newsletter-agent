from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from html.parser import HTMLParser

import httpx

from .collect import USER_AGENT
from .llm import LLM, load_prompt
from .rank import ScoredItem

log = logging.getLogger(__name__)

MAX_ARTICLE_CHARS = 6000
MIN_ARTICLE_CHARS = 300
SKIP_TAGS = {"script", "style", "noscript", "svg", "nav", "header", "footer", "form", "aside"}


@dataclass
class Entry:
    """A newsletter-ready item."""

    scored: ScoredItem
    summary: str
    why_it_matters: str
    grounded_on: str = "article"  # "article" or "snippet"

    @property
    def item(self):
        return self.scored.item


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data):
        if not self._skip_depth and data.strip():
            self.parts.append(data.strip())


def html_to_text(html_text: str) -> str:
    parser = _TextExtractor()
    parser.feed(html_text)
    return " ".join(parser.parts)


def fetch_article_text(url: str, client: httpx.Client) -> str:
    try:
        resp = client.get(url)
        resp.raise_for_status()
        return html_to_text(resp.text)[:MAX_ARTICLE_CHARS]
    except Exception as exc:  # noqa: BLE001
        log.warning("Could not fetch article %s: %s", url, exc)
        return ""


def summarize_one(scored: ScoredItem, llm: LLM, client: httpx.Client, system: str) -> Entry:
    item = scored.item
    text = fetch_article_text(item.url, client)
    grounded = "article"
    if len(text) < MIN_ARTICLE_CHARS:
        text, grounded = item.snippet, "snippet"
    payload = {
        "title": item.title,
        "source": item.source,
        "url": item.url,
        "article_text": text,
    }
    try:
        data = llm.complete_json(system, json.dumps(payload, ensure_ascii=False), max_tokens=600)
        return Entry(scored, str(data["summary"]).strip(), str(data["why_it_matters"]).strip(), grounded)
    except Exception as exc:  # noqa: BLE001
        log.warning("Summarizing %s failed: %s", item.url, exc)
        return Entry(scored, item.snippet[:300] or "Summary unavailable.", "", "snippet")


def summarize(scored_items: list[ScoredItem], llm: LLM, workers: int = 4) -> list[Entry]:
    system = load_prompt("summarize")
    with httpx.Client(
        timeout=20, follow_redirects=True, headers={"User-Agent": USER_AGENT}
    ) as client:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            return list(pool.map(lambda s: summarize_one(s, llm, client, system), scored_items))
