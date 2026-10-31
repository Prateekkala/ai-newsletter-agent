from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_SOURCES_PATH = Path(__file__).resolve().parents[2] / "config" / "sources.yaml"


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    category: str = "general"


def load_sources(path: Path | str = DEFAULT_SOURCES_PATH) -> list[Source]:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return [Source(**s) for s in data.get("sources", [])]
