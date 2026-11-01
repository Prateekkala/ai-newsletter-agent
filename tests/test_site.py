from datetime import date, datetime, timezone

from ainews.models import Item
from ainews.rank import ScoredItem
from ainews.render import render_html, write_issue
from ainews.site import build_site
from ainews.summarize import Entry


def entry(title="Big model <launch>", url="https://example.com/a?x=1&y=2"):
    item = Item(
        title, url, "OpenAI", "models", datetime(2026, 10, 30, tzinfo=timezone.utc), "snippet"
    )
    return Entry(ScoredItem(item, 9, ""), "A summary & more.", "")


def test_render_html_escapes_and_links():
    html = render_html([entry()], "Intro.", date(2026, 10, 31), ai_summaries=False)
    assert "Big model &lt;launch&gt;" in html
    assert 'href="https://example.com/a?x=1&amp;y=2"' in html
    assert "Models &amp; Releases" in html
    assert "AI-generated" not in html


def test_write_issue_writes_both_files(tmp_path):
    path = write_issue("# md", date(2026, 10, 31), tmp_path, html="<p>h</p>")
    assert path.name == "2026-10-31.md"
    assert (tmp_path / "2026-10-31.html").read_text(encoding="utf-8") == "<p>h</p>"


def test_build_site_lists_issues_newest_first(tmp_path):
    issues = tmp_path / "issues"
    issues.mkdir()
    for day, title in [("2026-10-24", "Older story"), ("2026-10-31", "Newer story")]:
        (issues / f"{day}.md").write_text(f"# x\n\n### [{title}](https://e.com)\n", encoding="utf-8")
        (issues / f"{day}.html").write_text(f"<html>{title}</html>", encoding="utf-8")
    (issues / "notes.md").write_text("ignored", encoding="utf-8")

    out = build_site(issues, tmp_path / "site")
    index = (out / "index.html").read_text(encoding="utf-8")
    assert index.index("2026-10-31") < index.index("2026-10-24")
    assert "Newer story" in index
    assert (out / "issues" / "2026-10-31.html").exists()
    assert "notes" not in index


def test_build_site_with_no_issues(tmp_path):
    (tmp_path / "issues").mkdir()
    out = build_site(tmp_path / "issues", tmp_path / "site")
    assert "No issues published yet" in (out / "index.html").read_text(encoding="utf-8")
