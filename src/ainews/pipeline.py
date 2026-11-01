from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path

from .collect import collect
from .config import Source
from .dedupe import dedupe
from .heuristic import extractive_entries, free_intro, rank_heuristic
from .llm import LLM
from .rank import rank
from .render import make_intro, render, render_html, write_issue
from .summarize import summarize

log = logging.getLogger(__name__)


def run_full(
    sources: list[Source],
    days: int = 7,
    top_n: int = 12,
    raw_dir: Path | str = "data/raw",
    issues_dir: Path | str | None = None,
    llm: LLM | None = None,
    use_llm: bool = True,
) -> Path:
    """Collect -> dedupe -> rank -> summarize -> render. Returns the issue path.

    With use_llm=False nothing is sent to any API: ranking uses keyword rules and summaries
    are short excerpts from the feeds.
    """
    if use_llm:
        llm = llm or LLM()  # fail early if the API key is missing
    today = date.today()

    items = dedupe(collect(sources, days=days))
    raw_dir = Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / f"{today.isoformat()}.json").write_text(
        json.dumps([i.to_dict() for i in items], indent=2, ensure_ascii=False), encoding="utf-8"
    )
    if not items:
        raise RuntimeError("No items collected. Check your network and config/sources.yaml.")

    if use_llm:
        top = rank(items, llm, top_n=top_n)
        if not top:
            raise RuntimeError("Ranking returned nothing. Check the logs for API errors.")
        entries = summarize(top, llm)
        intro = make_intro(entries, llm)
    else:
        top = rank_heuristic(items, top_n=top_n)
        entries = extractive_entries(top)
        intro = free_intro(entries)

    text = render(entries, intro, today, ai_summaries=use_llm)
    html = render_html(entries, intro, today, ai_summaries=use_llm)
    kwargs = {"out_dir": issues_dir} if issues_dir else {}
    return write_issue(text, today, html=html, **kwargs)
