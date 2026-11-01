import json
from datetime import date, datetime, timezone

from ainews.llm import parse_json
from ainews.models import Item
from ainews.rank import ScoredItem, cap_per_source, rank, select_top
from ainews.render import render
from ainews.summarize import Entry, html_to_text


def make(title: str, category: str = "industry", source: str = "S", day: int = 30) -> Item:
    return Item(
        title=title,
        url=f"https://example.com/{title.replace(' ', '-')}",
        source=source,
        category=category,
        published=datetime(2026, 10, day, tzinfo=timezone.utc),
        snippet="snippet text",
    )


class FakeLLM:
    """Scores titles containing 'big' as 9, everything else 3."""

    def complete_json(self, system, user, max_tokens=2000):
        return [
            {"id": d["id"], "score": 9 if "big" in d["title"] else 3, "reason": "r"}
            for d in json.loads(user)
        ]

    def complete(self, system, user, max_tokens=2000):
        return "intro"


def test_parse_json_handles_fences_and_noise():
    assert parse_json('```json\n[{"a": 1}]\n```') == [{"a": 1}]
    assert parse_json('Sure! Here you go: {"a": 2} Hope that helps') == {"a": 2}


def test_cap_per_source():
    items = [make(f"t{i}", source="arxiv") for i in range(10)] + [make("blog", source="blog")]
    capped = cap_per_source(items, 3)
    assert len(capped) == 4


def test_select_top_respects_category_limit():
    scored = [ScoredItem(make(f"big paper {i}", "research"), 9, "") for i in range(5)]
    scored.append(ScoredItem(make("news", "industry"), 5, ""))
    top = select_top(scored, top_n=4, category_limits={"research": 2})
    cats = [s.item.category for s in top]
    assert cats.count("research") == 2
    assert "industry" in cats


def test_rank_end_to_end_with_fake_llm():
    items = [make("big model", "models"), make("minor update"), make("big paper", "research")]
    top = rank(items, FakeLLM(), top_n=2)
    assert [s.item.title for s in top] == ["big model", "big paper"]


def test_html_to_text_skips_scripts_and_nav():
    html = "<nav>menu</nav><script>var x=1</script><p>Hello</p><p>world</p>"
    assert html_to_text(html) == "Hello world"


def test_render_groups_sections_and_links():
    entry = Entry(ScoredItem(make("big model", "models"), 9, ""), "A summary.", "It matters.")
    text = render([entry], "Intro here.", date(2026, 10, 31))
    assert "# AI Weekly: 31 October 2026" in text
    assert "## Models & Releases" in text
    assert "[big model](https://example.com/big-model)" in text
    assert "**Why it matters:** It matters." in text
    assert "## Research" not in text
