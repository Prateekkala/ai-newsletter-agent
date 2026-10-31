from __future__ import annotations

import argparse
import json
import logging
from datetime import date
from pathlib import Path

from .collect import collect
from .config import DEFAULT_SOURCES_PATH, load_sources
from .dedupe import dedupe


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect and dedupe AI news from RSS feeds.")
    parser.add_argument("--days", type=int, default=7, help="look-back window in days")
    parser.add_argument("--sources", default=str(DEFAULT_SOURCES_PATH), help="path to sources.yaml")
    parser.add_argument("--out", default="data/raw", help="output directory for JSON")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    sources = load_sources(args.sources)
    items = collect(sources, days=args.days)
    unique = dedupe(items)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{date.today().isoformat()}.json"
    out_file.write_text(
        json.dumps([i.to_dict() for i in unique], indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"{len(items)} collected -> {len(unique)} after dedupe -> {out_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
