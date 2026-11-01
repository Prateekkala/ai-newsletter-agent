from datetime import datetime, timezone

from ainews import pipeline
from ainews.heuristic import extractive_summary, rank_heuristic, score_item
from ainews.models import Item


def make(title, snippet="", source="OpenAI", category="models", day=30):
    return Item(
        title=title,
        url=f"https://example.com/{title.replace(' ', '-')}",
        source=source,
        category=category,
        published=datetime(2026, 10, day, tzinfo=timezone.utc),
        snippet=snippet,
    )


def test_extractive_summary_strips_arxiv_prefix():
    snippet = "arXiv:2610.00001v1 Announce Type: new Abstract: We study X. It works well. Third."
    assert extractive_summary(snippet).startswith("We study X.")


def test_extractive_summary_strips_wordpress_tail_and_truncates():
    snippet = "Short news here. The post Foo appeared first on Bar."
    assert extractive_summary(snippet) == "Short news here."
    long = "word " * 200
    out = extractive_summary(long, max_chars=100)
    assert len(out) <= 101 and out.endswith("…")


def test_extractive_summary_empty_fallback():
    assert "No excerpt" in extractive_summary("")


def test_scoring_prefers_launches_over_promo():
    now = datetime(2026, 10, 31, tzinfo=timezone.utc)
    launch, _ = score_item(make("OpenAI launches new model"), now)
    promo, _ = score_item(make("Join our webinar: tips and tricks", source="TechCrunch (AI)"), now)
    assert launch > promo


def test_rank_heuristic_orders_and_limits():
    items = [make("Company launches new model"), make("Podcast episode 12"), make("Funding round of $1 billion")]
    top = rank_heuristic(items, top_n=2)
    assert len(top) == 2
    assert "Podcast episode 12" not in [s.item.title for s in top]


def test_free_pipeline_runs_offline(tmp_path, monkeypatch):
    items = [
        make("OpenAI launches new model", "OpenAI released a model today. It is faster."),
        make("Open-source agent framework released", "A new framework.", "Hugging Face Blog", "tools"),
        make("New paper on reasoning", "arXiv:1 Announce Type: new Abstract: We study reasoning.", "arXiv cs.AI", "research"),
    ]
    monkeypatch.setattr(pipeline, "collect", lambda sources, days=7: items)
    path = pipeline.run_full(
        [], raw_dir=tmp_path / "raw", issues_dir=tmp_path / "issues", use_llm=False
    )
    text = path.read_text(encoding="utf-8")
    assert path.parent == tmp_path / "issues"
    assert "## Models & Releases" in text
    assert "## Research" in text
    assert "We study reasoning." in text
    assert "arXiv:1" not in text
    assert "Why it matters" not in text  # free mode has no editorial line


def test_footer_matches_mode(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "collect", lambda sources, days=7: [make("OpenAI launches new model", "Text.")])
    path = pipeline.run_full([], raw_dir=tmp_path / "r", issues_dir=tmp_path / "i", use_llm=False)
    text = path.read_text(encoding="utf-8")
    assert "AI-generated" not in text
    assert "short excerpts" in text
