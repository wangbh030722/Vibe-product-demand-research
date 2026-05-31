"""Anthropic LLM wrapper with on-disk cache.

Graceful no-op if ANTHROPIC_API_KEY is unset or the SDK isn't installed —
returns a structured "skipped" record so the UI can show a clear placeholder.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

CACHE_DIR = Path("evidence/.llm_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

MODEL = os.environ.get("DEMAND_LLM_MODEL", "claude-opus-4-7")


def _cache_key(system: str, prompt: str, model: str, max_tokens: int) -> str:
    h = hashlib.sha256()
    for part in (system, prompt, model, str(max_tokens)):
        h.update(part.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()[:32]


def available() -> bool:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return False
    try:
        import anthropic  # noqa: F401
        return True
    except Exception:
        return False


def call(system: str, prompt: str, max_tokens: int = 2000,
         model: str | None = None, expect_json: bool = False) -> dict[str, Any]:
    """Call Claude. Returns {ok, text, json (optional), skipped (optional), error (optional)}."""
    model = model or MODEL
    key = _cache_key(system, prompt, model, max_tokens)
    cache_file = CACHE_DIR / f"{key}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))

    if not available():
        return {"ok": False, "skipped": True,
                "error": "ANTHROPIC_API_KEY unset or anthropic SDK missing"}

    try:
        import anthropic
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        out = {"ok": True, "text": text}
        if expect_json:
            try:
                # Look for ```json blocks first, else parse whole text
                stripped = text.strip()
                if "```" in stripped:
                    parts = stripped.split("```")
                    for p in parts:
                        p = p.strip()
                        if p.startswith("json"):
                            p = p[4:].strip()
                        try:
                            out["json"] = json.loads(p)
                            break
                        except json.JSONDecodeError:
                            continue
                if "json" not in out:
                    out["json"] = json.loads(stripped)
            except Exception as e:
                out["json"] = None
                out["json_error"] = str(e)
        cache_file.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
        return out
    except Exception as e:
        return {"ok": False, "error": str(e)}
