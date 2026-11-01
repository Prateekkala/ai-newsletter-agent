from __future__ import annotations

import argparse
import json
import logging
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from .collect import collect
from .config import DEFAULT_SOURCES_PATH, load_sources
from .dedupe import dedupe


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AI newsletter agent.")
    parser.add_argument("--days", type=int, default=7, help="look-back window in days")
    parser.add_argument("--sources", default=str(DEFAULT_SOURCES_PATH), help="path to sources.yaml")
    parser.add_argument("--out", default="data/raw", help="output directory for collected JSON")
    parser.add_argument(
        "--full",
        action="store_true",
        help="run the whole pipeline (rank, summarize, render) and write issues/<date>.md; "
        "needs ANTHROPIC_API_KEY",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="with --full: free mode, no API key needed (keyword ranking, feed excerpts)",
    )
    parser.add_argument("--top", type=int, default=12, help="stories in the issue (with --full)")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    load_dotenv()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )
    # keep third-party request logs quiet
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    sources = load_sources(args.sources)

    if args.full or args.no_llm:
        from .pipeline import run_full

        path = run_full(
            sources, days=args.days, top_n=args.top, raw_dir=args.out,
            use_llm=not args.no_llm,
        )
        print(f"Issue written to {path}")
        return 0

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
