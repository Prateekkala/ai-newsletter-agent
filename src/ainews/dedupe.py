from __future__ import annotations

import re
from difflib import SequenceMatcher
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from .models import Item

TRACKING_PREFIXES = ("utm_", "fbclid", "gclid", "mc_", "ref")
WORD_RE = re.compile(r"[a-z0-9]+")


def normalize_url(url: str) -> str:
    """Strip tracking params, fragments, trailing slashes and www so equal pages compare equal."""
    p = urlparse(url.strip())
    query = [
        (k, v)
        for k, v in parse_qsl(p.query, keep_blank_values=True)
        if not k.lower().startswith(TRACKING_PREFIXES)
    ]
    host = p.netloc.lower().removeprefix("www.")
    path = p.path.rstrip("/") or "/"
    return urlunparse((p.scheme.lower(), host, path, "", urlencode(query), ""))


def _norm_title(title: str) -> str:
    return " ".join(title.lower().split())


def _is_similar(
    a: str, a_words: frozenset[str], b: str, b_words: frozenset[str], threshold: float
) -> bool:
    """Cheap word-overlap check first; only run the slow character matcher on likely pairs."""
    if not a_words or not b_words:
        return False
    if len(a_words & b_words) / len(a_words | b_words) < 0.5:
        return False
    return SequenceMatcher(None, a, b).ratio() >= threshold


def dedupe(items: list[Item], title_threshold: float = 0.85) -> list[Item]:
    """Drop repeated URLs, then near-identical headlines. Keeps the first occurrence,
    so pass items sorted the way you want winners chosen (newest first by default)."""
    seen_urls: set[str] = set()
    kept: list[Item] = []
    kept_titles: list[tuple[str, frozenset[str]]] = []
    for item in items:
        key = normalize_url(item.url)
        if key in seen_urls:
            continue
        title = _norm_title(item.title)
        words = frozenset(WORD_RE.findall(title))
        if any(_is_similar(title, words, t, w, title_threshold) for t, w in kept_titles):
            continue
        seen_urls.add(key)
        kept.append(item)
        kept_titles.append((title, words))
    return kept