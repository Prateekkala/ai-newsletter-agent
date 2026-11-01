"""Free mode: rank with simple rules and summarize with feed excerpts. No API key, no cost.

This is deliberately basic. It is good enough for a first issue and a baseline to compare the
LLM version against later.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from .models import Item
from .rank import ScoredItem, cap_per_source, select_top
from .summarize import Entry

# Bonus points for sources that usually publish primary news. Edit freely.
SOURCE_WEIGHTS = {
    "OpenAI": 3,
    "Google DeepMind": 3,
    "Google AI": 2,
    "Hugging Face Blog": 2,
    "MIT Technology Review (AI)": 2,
    "NVIDIA Blog": 1,
    "The Verge (AI)": 1,
    "TechCrunch (AI)": 1,
}

# Keyword -> points. Matched in the title (full points) or the snippet (half points).
POSITIVE = {
    "launch": 2, "release": 2, "introduc": 2, "announce": 2, "unveil": 2,
    "open-source": 2, "open source": 2, "new model": 2, "gpt": 1, "gemini": 1,
    "claude": 1, "llama": 1, "mistral": 1, "benchmark": 1, "agent": 1,
    "state-of-the-art": 1, "outperform": 1, "reasoning": 1, "safety": 1,
    "regulation": 2, "policy": 1, "lawsuit": 2, "billion": 2, "funding": 2,
    "acquire": 2, "partnership": 1, "chip": 1, "robot": 1,
}
NEGATIVE = {
    "podcast": -3, "webinar": -3, "sponsored": -4, "newsletter": -2, "deal": -2,
    "sale": -2, "discount": -3, "how to": -2, "tips": -2, "best ": -2, "review": -1,
    "opinion": -1, "register now": -3, "join us": -3,
}

ARXIV_PREFIX_RE = re.compile(r"^.*?\bAbstract:\s*", re.S)
WORDPRESS_TAIL_RE = re.compile(r"\s*The post .{0,200}? appeared first on .*$", re.S)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def score_item(item: Item, now: datetime | None = None) -> tuple[float, str]:
    now = now or datetime.now(timezone.utc)
    title, snippet = item.title.lower(), item.snippet.lower()
    points = float(SOURCE_WEIGHTS.get(item.source, 0))
    hits: list[str] = []
    for table in (POSITIVE, NEGATIVE):
        for word, weight in table.items():
            if word in title:
                points += weight
                hits.append(word.strip())
            elif word in snippet:
                points += weight / 2
    if (now - item.published).days <= 2:
        points += 1
    reason = "keywords: " + ", ".join(hits) if hits else "source and recency only"
    return round(points, 1), reason


def rank_heuristic(
    items: list[Item],
    top_n: int = 12,
    per_source_cap: int = 25,
    category_limits: dict[str, int] | None = None,
) -> list[ScoredItem]:
    candidates = cap_per_source(items, per_source_cap)
    scored = []
    for item in candidates:
        score, reason = score_item(item)
        scored.append(ScoredItem(item, score, reason))
    return select_top(scored, top_n, category_limits)


def extractive_summary(snippet: str, max_chars: int = 280) -> str:
    """First one to three sentences of the feed snippet, trimmed. A short excerpt, not a rewrite."""
    text = ARXIV_PREFIX_RE.sub("", snippet).strip()
    text = WORDPRESS_TAIL_RE.sub("", text).strip()
    out = ""
    for sentence in SENTENCE_SPLIT_RE.split(text)[:3]:
        if out and len(out) + 1 + len(sentence) > max_chars:
            break
        out = f"{out} {sentence}".strip()
    if len(out) > max_chars:
        out = out[:max_chars].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return out or "No excerpt available. See the link for details."


def extractive_entries(scored_items: list[ScoredItem]) -> list[Entry]:
    return [Entry(s, extractive_summary(s.item.snippet), "", "snippet") for s in scored_items]


def free_intro(entries: list[Entry]) -> str:
    sources = {e.item.source for e in entries}
    return (
        f"This issue rounds up {len(entries)} AI stories from {len(sources)} sources over the "
        "past week. Each entry is a short excerpt from the publisher's feed; follow the link for "
        "the full story."
    )
