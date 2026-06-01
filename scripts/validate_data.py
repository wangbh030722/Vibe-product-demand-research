#!/usr/bin/env python3
"""
Validate a category-research data JSON file against:
  1. JSON Schema (schemas/report-data.schema.json) — structural
  2. Cross-reference integrity rules (custom) — semantic
  3. Evidence-rules.md hard gates                — content quality

Usage:
    python scripts/validate_data.py data/health-ring.json
    python scripts/validate_data.py --all                 # validate everything in data/
    python scripts/validate_data.py --schema-only path    # skip cross-ref checks
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    import jsonschema
    from jsonschema import Draft7Validator
except ImportError:
    print("ERROR: jsonschema not installed.\n  pip install jsonschema", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "schemas" / "report-data.schema.json"


# --------------------------------------------------------------------------- #
# Pretty output                                                                #
# --------------------------------------------------------------------------- #

class Style:
    RED = "\033[31m"
    YELLOW = "\033[33m"
    GREEN = "\033[32m"
    DIM = "\033[2m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def err(msg: str) -> None:
    print(f"{Style.RED}✗ {msg}{Style.RESET}", file=sys.stderr)


def warn(msg: str) -> None:
    print(f"{Style.YELLOW}⚠ {msg}{Style.RESET}")


def ok(msg: str) -> None:
    print(f"{Style.GREEN}✓ {msg}{Style.RESET}")


# --------------------------------------------------------------------------- #
# Schema validation                                                            #
# --------------------------------------------------------------------------- #

def load_schema() -> dict[str, Any]:
    if not SCHEMA_PATH.exists():
        err(f"Schema not found at {SCHEMA_PATH}")
        sys.exit(2)
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


# translation-suffix languages backfilled onto base fields (<field>_<code>)
_TR_SUFFIXES = ("_en", "_zh", "_ja", "_es", "_fr", "_de")


def _strip_en(obj: Any) -> Any:
    """Deep-copy with all translation keys (*_en, *_zh, *_ja, …) removed, so the
    base schema (additionalProperties:false) validates without declaring them.
    Note: meta.target_lang is a real schema field and is intentionally NOT stripped."""
    if isinstance(obj, dict):
        return {k: _strip_en(v) for k, v in obj.items()
                if not any(k.endswith(s) for s in _TR_SUFFIXES)}
    if isinstance(obj, list):
        return [_strip_en(v) for v in obj]
    return obj


def validate_schema(data: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    validator = Draft7Validator(schema)
    # Validate the *_en-stripped view (translations are optional add-ons).
    errors = sorted(validator.iter_errors(_strip_en(data)), key=lambda e: list(e.absolute_path))
    out = []
    for e in errors:
        path = "/".join(str(p) for p in e.absolute_path) or "(root)"
        out.append(f"[schema] {path}: {e.message}")
    return out


# --------------------------------------------------------------------------- #
# Cross-reference + semantic checks                                            #
# --------------------------------------------------------------------------- #

def check_cross_refs(data: dict[str, Any]) -> list[str]:
    """Catch things JSON Schema can't express (referential integrity)."""
    errors: list[str] = []

    player_ids = {p["id"] for p in data.get("players", [])}
    theme_ids  = {t["id"] for t in data.get("themes",  [])}
    voice_ids  = {v["id"] for v in data.get("voices",  [])}
    opp_id     = data.get("opportunity", {}).get("id")
    all_ids    = player_ids | theme_ids | voice_ids | ({opp_id} if opp_id else set())

    # 1. Voice.player must reference an existing player, or the "other" bucket
    # (a real voice not about any specific tracked brand — kept in the corpus but
    # not attributed to a player, so it never inflates a brand's share).
    for v in data.get("voices", []):
        if v["player"] != "other" and v["player"] not in player_ids:
            errors.append(
                f"[xref] voice {v['id']!r}.player = {v['player']!r} → not in players[]"
            )

    # 2. Voice.themes[] must all reference existing themes
    for v in data.get("voices", []):
        for tid in v.get("themes", []):
            if tid not in theme_ids:
                errors.append(
                    f"[xref] voice {v['id']!r}.themes contains {tid!r} → not in themes[]"
                )

    # 3. Edge endpoints must all be known node ids
    for i, e in enumerate(data.get("edges", [])):
        if e["from"] not in all_ids:
            errors.append(f"[xref] edges[{i}].from = {e['from']!r} → unknown node")
        if e["to"] not in all_ids:
            errors.append(f"[xref] edges[{i}].to = {e['to']!r} → unknown node")

    # 4a. Duplicate ids WITHIN each kind (set comprehension above silently dedupes)
    for kind_name, arr_key in [("player", "players"), ("theme", "themes"), ("voice", "voices")]:
        ids_list = [n["id"] for n in data.get(arr_key, [])]
        seen_here: dict[str, int] = {}
        for i, nid in enumerate(ids_list):
            if nid in seen_here:
                errors.append(
                    f"[xref] duplicate {kind_name} id {nid!r} at {arr_key}[{i}] "
                    f"(first seen at {arr_key}[{seen_here[nid]}])"
                )
            seen_here[nid] = i

    # 4b. Duplicate ids ACROSS kinds (id namespace must be globally unique)
    cross_seen: dict[str, str] = {}
    for kind, ids in [("player", player_ids), ("theme", theme_ids), ("voice", voice_ids)]:
        for nid in ids:
            if nid in cross_seen and cross_seen[nid] != kind:
                errors.append(
                    f"[xref] id {nid!r} used in both {cross_seen[nid]} and {kind}"
                )
            cross_seen[nid] = kind

    # 5. Marketplace.player must reference existing player
    for m in data.get("marketplace", []):
        if m["player"] not in player_ids:
            errors.append(
                f"[xref] marketplace entry on platform {m.get('platform')!r}"
                f" → player {m['player']!r} not in players[]"
            )

    return errors


# --------------------------------------------------------------------------- #
# Evidence-rules.md gates                                                      #
# --------------------------------------------------------------------------- #

def check_evidence_gates(data: dict[str, Any]) -> list[str]:
    """
    Hard gates from references/evidence-rules.md, codified.
    Returns errors (block report) and warnings (advise but don't block).
    """
    errors: list[str] = []
    warnings: list[str] = []

    verdict = data.get("verdict", {})
    status = verdict.get("status")
    counts = verdict.get("evidence_counts", {})

    raw_voices  = counts.get("raw_voices", 0)
    marketplace = counts.get("marketplace", 0)

    # Gate 1: status=real / partial requires raw_voices > 0
    if status in ("real", "partial") and raw_voices == 0:
        errors.append(
            f"[evidence] verdict.status={status!r} requires raw_voices > 0 "
            f"(got 0). Either downgrade to 'insufficient' or collect raw voices."
        )

    # Gate 2: raw_voices in verdict should match len(voices)
    actual_voices = len(data.get("voices", []))
    if raw_voices and raw_voices != actual_voices:
        warnings.append(
            f"[evidence] verdict.evidence_counts.raw_voices = {raw_voices} "
            f"but voices[] has {actual_voices} entries. Update one."
        )

    # Gate 3: marketplace count should match len(marketplace)
    actual_mkt = len(data.get("marketplace", []))
    if marketplace and marketplace != actual_mkt:
        warnings.append(
            f"[evidence] verdict.evidence_counts.marketplace = {marketplace} "
            f"but marketplace[] has {actual_mkt} entries."
        )

    # Gate 4: each player should have ≥1 voice if status=real
    if status == "real":
        speakers = {v["player"] for v in data.get("voices", [])}
        silent = [p["id"] for p in data.get("players", []) if p["id"] not in speakers]
        if silent:
            warnings.append(
                f"[evidence] status=real but players have 0 voices: {silent}. "
                f"Consider downgrading or collecting more."
            )

    # Print warnings as we go (they don't block)
    for w in warnings:
        warn(w)

    return errors


# --------------------------------------------------------------------------- #
# Entry                                                                        #
# --------------------------------------------------------------------------- #

def validate_file(path: Path, schema: dict, schema_only: bool = False) -> bool:
    print(f"{Style.BOLD}validating {path}{Style.RESET}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        err(f"JSON parse error at line {e.lineno}, col {e.colno}: {e.msg}")
        return False

    all_errors: list[str] = []
    all_errors += validate_schema(data, schema)

    if not schema_only:
        all_errors += check_cross_refs(data)
        all_errors += check_evidence_gates(data)

    if all_errors:
        for e in all_errors:
            err(e)
        return False

    ok(f"{path.name} passed all checks")
    return True


def main() -> int:
    p = argparse.ArgumentParser(description="Validate report data JSON files.")
    p.add_argument("path", nargs="?", help="Path to JSON file to validate")
    p.add_argument("--all", action="store_true",
                   help="Validate all files in data/")
    p.add_argument("--schema-only", action="store_true",
                   help="Skip cross-ref and evidence checks")
    args = p.parse_args()

    schema = load_schema()

    if args.all:
        files = sorted((ROOT / "data").glob("*.json"))
        if not files:
            warn("no files in data/")
            return 0
    elif args.path:
        files = [Path(args.path)]
    else:
        p.print_help()
        return 2

    failures = 0
    for f in files:
        if not validate_file(f, schema, args.schema_only):
            failures += 1
        print()

    if failures:
        err(f"{failures} / {len(files)} file(s) failed validation")
        return 1
    ok(f"{len(files)} file(s) validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
