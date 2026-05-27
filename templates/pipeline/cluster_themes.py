#!/usr/bin/env python3
"""
Cluster collected voices into themes + edges via LLM.

Inputs: { category, target_market, players, voices } (see prompt template)
Output: { themes, voice_themes, edges } — ready to merge into report-data schema.

Usage:
  # Real run (requires OPENAI_API_KEY):
  python templates/pipeline/cluster_themes.py \
      --input collected/health-ring-voices.json \
      --out  data/health-ring-themes.json

  # Cached re-run (uses prior LLM response from fixtures/clusters/):
  python templates/pipeline/cluster_themes.py \
      --input collected/health-ring-voices.json \
      --cached

  # Dry-run (no LLM, returns fixture for testing):
  python templates/pipeline/cluster_themes.py \
      --input collected/health-ring-voices.json \
      --dry-run

Env:
  OPENAI_API_KEY     required for real runs
  OPENAI_BASE_URL    optional, defaults to https://api.openai.com/v1
  OPENAI_MODEL       optional, defaults to gpt-4o-mini
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PROMPT_PATH = ROOT / "templates" / "pipeline" / "prompts" / "cluster.txt"
CACHE_DIR = ROOT / "fixtures" / "clusters"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------- #
# Cache key                                                                    #
# --------------------------------------------------------------------------- #

def cache_key(input_data: dict) -> str:
    """Stable hash over the input shape (so prompt changes do invalidate)."""
    blob = json.dumps(input_data, sort_keys=True, ensure_ascii=False)
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    return hashlib.sha256((blob + "\n---\n" + prompt).encode()).hexdigest()[:16]


def cache_path(key: str) -> Path:
    return CACHE_DIR / f"{key}.json"


# --------------------------------------------------------------------------- #
# LLM call (OpenAI-compatible)                                                 #
# --------------------------------------------------------------------------- #

def call_llm(input_data: dict, *, model: str | None = None) -> dict:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY not set. Either export it, or use --cached / --dry-run."
        )
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    user_content = prompt.replace("<<< INPUT JSON >>>",
                                  json.dumps(input_data, ensure_ascii=False, indent=2))

    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system",
             "content": "You output strict JSON only. No prose. No code fences."},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    print(f"  → calling {base_url} model={model} ...", file=sys.stderr)
    with urllib.request.urlopen(req, timeout=120) as resp:
        payload = json.loads(resp.read())
    text = payload["choices"][0]["message"]["content"]
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"LLM returned non-JSON: {e}\n{text[:500]}") from e


# --------------------------------------------------------------------------- #
# Validate LLM output before trusting it                                       #
# --------------------------------------------------------------------------- #

def validate_output(out: dict, input_data: dict) -> list[str]:
    errs = []
    themes = out.get("themes", [])
    voice_themes = out.get("voice_themes", {})
    edges = out.get("edges", [])

    if not isinstance(themes, list) or not themes:
        errs.append("themes[] missing or empty")
    if not isinstance(voice_themes, dict):
        errs.append("voice_themes must be a dict")
    if not isinstance(edges, list):
        errs.append("edges must be a list")

    theme_ids = {t.get("id") for t in themes if isinstance(t, dict)}
    voice_ids = {v["id"] for v in input_data["voices"]}
    player_ids = {p["id"] for p in input_data["players"]}

    for t in themes:
        if not isinstance(t.get("id"), str) or not t["id"].startswith("t."):
            errs.append(f"theme.id invalid: {t.get('id')!r} (must start with 't.')")
        if t.get("polarity") not in ("win", "pain", "neutral"):
            errs.append(f"theme {t.get('id')!r} polarity invalid: {t.get('polarity')!r}")

    for vid, tids in voice_themes.items():
        if vid not in voice_ids:
            errs.append(f"voice_themes references unknown voice {vid!r}")
        for tid in tids:
            if tid not in theme_ids:
                errs.append(f"voice_themes[{vid!r}] references unknown theme {tid!r}")

    for e in edges:
        if e.get("from") not in player_ids and e.get("from") not in theme_ids:
            errs.append(f"edge.from {e.get('from')!r} unknown")
        if e.get("to") not in theme_ids:
            errs.append(f"edge.to {e.get('to')!r} not a theme")
        w = e.get("w")
        if not (isinstance(w, int) and 1 <= w <= 3):
            errs.append(f"edge w invalid: {w!r}")
    return errs


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="Path to voices JSON")
    p.add_argument("--out",   help="Where to write the cluster result")
    p.add_argument("--cached", action="store_true",
                   help="Reuse prior LLM response if cache hit")
    p.add_argument("--dry-run", action="store_true",
                   help="Skip LLM; return canned fixture if available")
    p.add_argument("--retries", type=int, default=2,
                   help="Retry LLM if output fails validation (default 2)")
    args = p.parse_args()

    input_data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    key = cache_key(input_data)
    cpath = cache_path(key)
    print(f"  cache key: {key}", file=sys.stderr)

    if args.dry_run:
        # Use any existing fixture if present, else write a minimal placeholder
        if cpath.exists():
            out = json.loads(cpath.read_text(encoding="utf-8"))
            print(f"  ✓ using cached fixture {cpath.name}", file=sys.stderr)
        else:
            out = {
                "themes": [{
                    "id": "t.placeholder",
                    "label": "(dry-run)",
                    "polarity": "neutral",
                    "size": 12, "x": 0.5, "y": 0.5,
                    "color": "#80766a",
                    "summary": "Dry-run placeholder; replace with real LLM clustering",
                }],
                "voice_themes": {v["id"]: ["t.placeholder"] for v in input_data["voices"]},
                "edges": [],
            }
            print("  ⚠ no cache hit; emitting placeholder", file=sys.stderr)
    elif args.cached and cpath.exists():
        out = json.loads(cpath.read_text(encoding="utf-8"))
        print(f"  ✓ cache hit {cpath.name}", file=sys.stderr)
    else:
        last_err = None
        for attempt in range(args.retries + 1):
            try:
                out = call_llm(input_data)
                errs = validate_output(out, input_data)
                if not errs:
                    break
                last_err = errs
                print(f"  ⚠ attempt {attempt+1} failed validation: {errs[0]}", file=sys.stderr)
            except (urllib.error.HTTPError, RuntimeError) as e:
                last_err = [str(e)]
                print(f"  ⚠ attempt {attempt+1} errored: {e}", file=sys.stderr)
        else:
            print(f"✗ all {args.retries+1} LLM attempts failed.", file=sys.stderr)
            for e in last_err or []:
                print(f"   - {e}", file=sys.stderr)
            return 1
        # Cache successful output
        cpath.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  ✓ cached to {cpath.relative_to(ROOT)}", file=sys.stderr)

    # Final validation gate (even for cached/dry-run)
    errs = validate_output(out, input_data)
    if errs:
        print("✗ output failed validation:", file=sys.stderr)
        for e in errs:
            print(f"   - {e}", file=sys.stderr)
        return 1

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"✓ wrote {args.out}")
    else:
        print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
