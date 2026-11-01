from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .llm import LLM, ROOT, load_prompt
from .summarize import Entry

log = logging.getLogger(__name__)

SECTIONS = [
    ("models", "Models & Releases"),
    ("research", "Research"),
    ("tools", "Tools & Open Source"),
    ("industry", "Industry & Policy"),
]


def make_intro(entries: list[Entry], llm: LLM) -> str:
    payload = [{"title": e.item.title, "summary": e.summary} for e in entries]
    try:
        return llm.complete(load_prompt("intro"), json.dumps(payload, ensure_ascii=False), 300).strip()
    except Exception as exc:  # noqa: BLE001
        log.warning("Intro generation failed: %s", exc)
        return "Here are this week's most important AI stories."


def group_by_section(entries: list[Entry]) -> list[tuple[str, list[Entry]]]:
    known = {key for key, _ in SECTIONS}
    sections = []
    for key, title in SECTIONS:
        group = [e for e in entries if e.item.category == key]
        if key == "industry":  # anything with an unknown category lands here
            group += [e for e in entries if e.item.category not in known]
        if group:
            sections.append((title, group))
    return sections


def _env(autoescape: bool) -> Environment:
    return Environment(
        loader=FileSystemLoader(ROOT / "templates"),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        autoescape=autoescape,
    )


def _context(entries: list[Entry], intro: str, issue_date: date, ai_summaries: bool) -> dict:
    return {
        "issue_date": issue_date,
        "intro": intro,
        "sections": group_by_section(entries),
        "ai_summaries": ai_summaries,
    }


def render(
    entries: list[Entry], intro: str, issue_date: date, ai_summaries: bool = True
) -> str:
    """Markdown version of the issue."""
    template = _env(autoescape=False).get_template("newsletter.md.j2")
    return template.render(**_context(entries, intro, issue_date, ai_summaries))


def render_html(
    entries: list[Entry], intro: str, issue_date: date, ai_summaries: bool = True
) -> str:
    """Email-style HTML version of the issue (table layout, inline styles)."""
    template = _env(autoescape=True).get_template("newsletter.html.j2")
    return template.render(**_context(entries, intro, issue_date, ai_summaries))


def write_issue(
    text: str,
    issue_date: date,
    out_dir: Path | str = ROOT / "issues",
    html: str | None = None,
) -> Path:
    """Write issues/<date>.md (and issues/<date>.html when html is given). Returns the .md path."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{issue_date.isoformat()}.md"
    path.write_text(text, encoding="utf-8")
    if html is not None:
        path.with_suffix(".html").write_text(html, encoding="utf-8")
    return path
