"""Build a small static site (index + issues) from issues/*.md and issues/*.html.

Run:  python -m ainews.site     ->  writes ./site, which GitHub Pages can publish.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .llm import ROOT

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HEADLINE_RE = re.compile(r"^### \[(.+?)\]\(", re.M)


def build_site(issues_dir: Path | str = ROOT / "issues", out_dir: Path | str = ROOT / "site") -> Path:
    issues_dir, out_dir = Path(issues_dir), Path(out_dir)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    (out_dir / "issues").mkdir(parents=True)

    issues = []
    for md in sorted(issues_dir.glob("*.md"), reverse=True):
        html = md.with_suffix(".html")
        if not DATE_RE.match(md.stem) or not html.exists():
            continue
        headlines = HEADLINE_RE.findall(md.read_text(encoding="utf-8"))
        issues.append({"date": md.stem, "stories": len(headlines), "headlines": headlines[:3]})
        shutil.copy(html, out_dir / "issues" / html.name)

    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=True)
    index = env.get_template("index.html.j2").render(
        issues=issues, latest=issues[0] if issues else None
    )
    (out_dir / "index.html").write_text(index, encoding="utf-8")
    (out_dir / ".nojekyll").write_text("", encoding="utf-8")
    return out_dir


def main() -> int:
    out = build_site()
    print(f"Site written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
