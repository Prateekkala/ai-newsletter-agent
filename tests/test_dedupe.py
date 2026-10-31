from datetime import datetime, timezone

from ainews.dedupe import dedupe, normalize_url
from ainews.models import Item


def make(title: str, url: str, source: str = "A") -> Item:
    return Item(
        title=title,
        url=url,
        source=source,
        category="industry",
        published=datetime(2026, 10, 30, tzinfo=timezone.utc),
    )


def test_normalize_url_strips_tracking_and_slash():
    a = normalize_url("https://www.Example.com/post/?utm_source=x&id=1#top")
    b = normalize_url("https://example.com/post?id=1")
    assert a == b


def test_dedupe_by_url():
    items = [
        make("Model X released", "https://example.com/x?utm_campaign=a"),
        make("Totally different headline", "https://example.com/x/", source="B"),
    ]
    assert len(dedupe(items)) == 1


def test_dedupe_by_similar_title():
    items = [
        make("OpenAI launches new reasoning model", "https://a.com/1"),
        make("OpenAI launches new reasoning model!", "https://b.com/2", source="B"),
        make("Google updates Gemini app", "https://c.com/3", source="C"),
    ]
    out = dedupe(items)
    assert [i.url for i in out] == ["https://a.com/1", "https://c.com/3"]
