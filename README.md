# AI Newsletter Agent

[![CI](https://github.com/YOUR_USERNAME/ai-newsletter-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/ai-newsletter-agent/actions/workflows/ci.yml)

A Python pipeline that gathers the week's AI news from RSS feeds, removes duplicates, and (in later stages) ranks, summarizes and publishes a weekly newsletter.

## Pipeline

```
Collect (RSS) -> Dedupe -> Rank (LLM) -> Summarize (LLM) -> Render -> Publish
   done            done      planned        planned          planned    planned
```

| Stage | Module | Status |
|-------|--------|--------|
| Collect | `src/ainews/collect.py` | Working |
| Dedupe | `src/ainews/dedupe.py` | Working (URL normalisation + fuzzy title match) |
| Rank | `src/ainews/rank.py` | Stub |
| Summarize | `src/ainews/summarize.py` | Stub |
| Render | `src/ainews/render.py` | Stub |
| Publish | GitHub Pages + email | Planned |

## Quick start

```bash
git clone https://github.com/Prateekkala/ai-newsletter-agent.git
cd ai-newsletter-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # API key only needed from the summarize stage onward
PYTHONPATH=src python -m ainews.main --days 7
pytest
```

Output is written to `data/raw/YYYY-MM-DD.json`.

## Project layout

```
ai-newsletter-agent/
├── .github/workflows/ci.yml   # runs tests on every push/PR
├── config/sources.yaml        # RSS feeds + categories (edit to add sources)
├── src/ainews/                # pipeline code
├── tests/                     # pytest suite
├── templates/                 # Jinja2 newsletter templates (later)
├── issues/                    # published issues archive (later)
├── data/raw/                  # collected items (git-ignored)
└── docs/                      # architecture notes, design decisions
```

## Adding a source

Add an entry to `config/sources.yaml`:

```yaml
- name: My Favourite Blog
  url: https://example.com/feed.xml
  category: industry   # research | models | tools | industry
```

A broken or slow feed is logged and skipped; it never fails the whole run.

## Roadmap

- [x] RSS collection and dedupe
- [ ] LLM ranking with structured JSON output
- [ ] Summaries grounded in article text, with source links
- [ ] Markdown/HTML rendering and `issues/` archive
- [ ] Weekly GitHub Actions run that opens a PR for human review
- [ ] GitHub Pages archive site and email delivery
- [ ] Evals for ranking and summary quality

## License

MIT
