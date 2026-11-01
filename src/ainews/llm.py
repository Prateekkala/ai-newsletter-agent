from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL = "claude-sonnet-5-5"


def load_prompt(name: str) -> str:
    """Prompts live in prompts/<name>.md so you can tune them without touching code."""
    return (ROOT / "prompts" / f"{name}.md").read_text(encoding="utf-8").strip()


def parse_json(text: str):
    """Parse model output as JSON, tolerating ```json fences and stray text around it."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"(\[.*\]|\{.*\})", text, re.S)
        if not match:
            raise
        return json.loads(match.group(1))


class LLM:
    """Thin wrapper around the Anthropic SDK so the rest of the code never imports it."""

    def __init__(self, model: str | None = None, client=None):
        self.model = model or os.getenv("AINEWS_MODEL", DEFAULT_MODEL)
        if client is None:
            if not os.getenv("ANTHROPIC_API_KEY"):
                raise RuntimeError(
                    "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key."
                )
            import anthropic

            client = anthropic.Anthropic()
        self.client = client

    def complete(self, system: str, user: str, max_tokens: int = 2000) -> str:
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")

    def complete_json(self, system: str, user: str, max_tokens: int = 2000, attempts: int = 2):
        last_exc: Exception | None = None
        for _ in range(attempts):
            try:
                return parse_json(self.complete(system, user, max_tokens))
            except json.JSONDecodeError as exc:
                last_exc = exc
                log.warning("Model returned invalid JSON, retrying")
        raise last_exc  # type: ignore[misc]
