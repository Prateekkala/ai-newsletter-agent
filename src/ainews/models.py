from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime


@dataclass
class Item:
    """One article/post/paper pulled from a feed."""

    title: str
    url: str
    source: str
    category: str
    published: datetime
    snippet: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["published"] = self.published.isoformat()
        return d
