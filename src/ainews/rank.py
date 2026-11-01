from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from .llm import LLM, load_prompt
from .models import Item

log = logging.getLogger(__name__)

BATCH_SIZE = 25
DEFAULT_CATEGORY_LIMITS = {"research": 3}


@dataclass
class ScoredItem:
    item: Item
    score: float
    reason: str


def cap_per_source(items: list[Item], cap: int) -> list[Item]:
    """Keep at most `cap` items per source (items are newest first), so arXiv's volume
    cannot crowd out blogs and news and the number of LLM calls stays small."""
    counts: dict[str, int] = {}
    kept: list[Item] = []
    for item in items:
        counts[item.source] = counts.get(item.source, 0) + 1
        if counts[item.source] <= cap:
            kept.append(item)
    return kept


def select_top(
    scored: list[ScoredItem], top_n: int, category_limits: dict[str, int] | None = None
) -> list[ScoredItem]:
    """Highest scores first, newest as tie-break, honouring per-category limits."""
    limits = DEFAULT_CATEGORY_LIMITS if category_limits is None else category_limits
    ordered = sorted(scored, key=lambda s: (s.score, s.item.published), reverse=True)
    picked: list[ScoredItem] = []
    used: dict[str, int] = {}
    for s in ordered:
        cat = s.item.category
        if cat in limits and used.get(cat, 0) >= limits[cat]:
            continue
        picked.append(s)
        used[cat] = used.get(cat, 0) + 1
        if len(picked) == top_n:
            break
    return picked


def score_items(items: list[Item], llm: LLM) -> list[ScoredItem]:
    system = load_prompt("rank")
    scored: list[ScoredItem] = []
    for start in range(0, len(items), BATCH_SIZE):
        batch = items[start : start + BATCH_SIZE]
        payload = [
            {"id": i, "source": it.source, "title": it.title, "snippet": it.snippet[:300]}
            for i, it in enumerate(batch)
        ]
        try:
            results = llm.complete_json(system, json.dumps(payload, ensure_ascii=False))
        except Exception as exc:  # noqa: BLE001 - a failed batch should not kill the issue
            log.warning("Ranking batch starting at %d failed: %s", start, exc)
            continue
        for r in results:
            try:
                idx = int(r["id"])
                score = max(1, min(10, int(r["score"])))
                scored.append(ScoredItem(batch[idx], score, str(r.get("reason", ""))))
            except (KeyError, ValueError, TypeError, IndexError):
                log.warning("Skipping malformed ranking row: %r", r)
    return scored


def rank(
    items: list[Item],
    llm: LLM,
    top_n: int = 12,
    per_source_cap: int = 25,
    category_limits: dict[str, int] | None = None,
) -> list[ScoredItem]:
    candidates = cap_per_source(items, per_source_cap)
    log.info("Ranking %d candidates (from %d items)", len(candidates), len(items))
    return select_top(score_items(candidates, llm), top_n, category_limits)
