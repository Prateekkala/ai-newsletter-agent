from ainews.collect import parse_feed
from ainews.config import Source

SAMPLE_RSS = """<?xml version="1.0"?>
<rss version="2.0"><channel><title>t</title>
<item>
  <title>Big model drops</title>
  <link>https://example.com/big-model</link>
  <pubDate>Fri, 30 Oct 2026 10:00:00 GMT</pubDate>
  <description>&lt;p&gt;A &lt;b&gt;new&lt;/b&gt; model.&lt;/p&gt;</description>
</item>
<item>
  <title>No date, should be skipped</title>
  <link>https://example.com/nodate</link>
</item>
</channel></rss>"""


def test_parse_feed_extracts_and_cleans():
    src = Source(name="Example", url="https://example.com/feed", category="models")
    items = parse_feed(SAMPLE_RSS, src)
    assert len(items) == 1
    item = items[0]
    assert item.title == "Big model drops"
    assert item.source == "Example"
    assert item.category == "models"
    assert item.snippet == "A new model."
    assert item.published.year == 2026
