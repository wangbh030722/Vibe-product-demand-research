#!/usr/bin/env python3
"""
research.py — one-command category research pipeline.

    python scripts/research.py --idea "AI 智能体记忆" --slug agent-memory

Stages (each cached under collected/<slug>/ so re-runs are cheap & resumable):
  1. SCOPE      LLM: idea → {mode, subreddits, hn_queries, players}
  2. COLLECT    run reddit + HN collectors → raw voice pool
  3. CURATE     LLM: raw pool → ~14 best voices {player, sentiment, ...}
  4. CLUSTER    LLM: voices → themes + edges + voice_themes
  5. SYNTHESIZE LLM: everything → verdict, findings, opportunity, paths, risks, layout
  6. ASSEMBLE   merge into data/<slug>.json, validate
  7. RENDER     dist/<slug>.html + refresh dist/index.html

Flags:
  --slug SLUG          output slug (required)
  --idea "..."         product idea (required for a fresh run)
  --target-market STR  e.g. "US" / "US + CN"  (default: US)
  --skip-collect       reuse previously collected raw pool
  --from STAGE         resume from a stage: scope|collect|curate|cluster|synth|render
  --max-voices N       voices to curate (default 14)
  --dry-run            don't call LLM / network; use cached stage outputs only
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from llm_client import chat_json  # type: ignore

STAGES = ["scope", "collect", "curate", "cluster", "synth", "render"]


def work_dir(slug: str) -> Path:
    d = ROOT / "collected" / slug
    d.mkdir(parents=True, exist_ok=True)
    return d


def cached(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def save(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"    ✓ {path.relative_to(ROOT)}")


# --------------------------------------------------------------------------- #
# Stage 1 · SCOPE                                                              #
# --------------------------------------------------------------------------- #

def stage_scope(idea: str, target_market: str, wd: Path, dry: bool,
                mode_override: str | None = None) -> dict:
    out = wd / "01-scope.json"
    if dry and out.exists():
        return cached(out)
    sys = ("You are a market-research scoping assistant. Output STRICT JSON only.")
    if mode_override == "NON_STOCK":
        mode_instr = (
            '"mode": "NON_STOCK",   // FORCED: treat as new/emerging category. '
            "Do NOT map to an adjacent mature market. Players should be early "
            "entrants / conceptual / the closest analogues users currently hack "
            "together. Subreddits + queries should surface PAIN POINTS, "
            "WORKAROUNDS, and unmet-need signals, not established product reviews."
        )
    elif mode_override == "EXISTING":
        mode_instr = '"mode": "EXISTING",   // FORCED'
    else:
        mode_instr = ('"mode": "EXISTING" | "NON_STOCK",   // EXISTING if mature '
                      "category w/ products & reviews; NON_STOCK if new/emerging")
    user = f"""Product idea: {idea}
Target market: {target_market}

Decide research scope. Output JSON:
{{
  {mode_instr}
  "subreddits": ["name", ...],        // 3-6 real subreddit names (no /r/), most relevant
  "hn_queries": ["query", ...],       // 2-4 Hacker News search phrases
  "players": [                        // 3-6 entrants/analogues in this space
    {{"id": "<lowercase_slug>", "name": "<Brand Name>"}}
  ],
  "rationale": "<one sentence why this mode>"
}}
Rules: subreddit names must be plausible real subs. player ids lowercase a-z0-9_-."""
    res = chat_json(sys, user, temperature=0.3)
    if mode_override:
        res["mode"] = mode_override   # hard-enforce even if model drifts
    save(out, res)
    return res


# --------------------------------------------------------------------------- #
# Stage 2 · COLLECT                                                            #
# --------------------------------------------------------------------------- #

def stage_collect(scope: dict, wd: Path, skip: bool) -> list[dict]:
    out = wd / "02-pool.json"
    if skip and out.exists():
        print("    (skip-collect: reusing pool)")
        return cached(out)

    pool: list[dict] = []
    reddit_jsonl = wd / "reddit.jsonl"
    hn_jsonl = wd / "hn.jsonl"
    pullpush_jsonl = wd / "pullpush.jsonl"

    # pullpush.io — real Reddit posts/comments via a non-reddit.com domain,
    # so it works even when reddit.com 403s the proxy IP. Primary Reddit source.
    subs = scope.get("subreddits", [])
    pp_queries = scope.get("hn_queries") or [scope.get("_idea", "")]
    if pp_queries:
        cmd = [sys_exe(), str(ROOT / "core/collect/pullpush.py"),
               "--queries", *[q for q in pp_queries if q],
               "--size", "40", "--out", str(pullpush_jsonl)]
        if subs:
            cmd += ["--subs", *subs]
        print(f"    pullpush: {subs or '*'}")
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=180)
            pool += read_jsonl(pullpush_jsonl, source="reddit")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            print(f"    ! pullpush partial/failed: {e}", file=sys.stderr)

    # Reddit
    subs = scope.get("subreddits", [])
    if subs:
        cmd = [sys_exe(), str(ROOT / "core/collect/reddit.py"),
               "--subs", *subs, "--limit", "30",
               "--with-comments", "--comments-per-post", "4",
               "--out", str(reddit_jsonl)]
        print(f"    reddit: {' '.join(subs)}")
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=240)
            pool += read_jsonl(reddit_jsonl, source="reddit")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            print(f"    ! reddit collect partial/failed: {e}", file=sys.stderr)

    # HN
    queries = scope.get("hn_queries", [])
    if queries:
        cmd = [sys_exe(), str(ROOT / "core/collect/hn.py"),
               "--query", *queries, "--hits", "40", "--out", str(hn_jsonl)]
        print(f"    hn: {queries}")
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=150)
            pool += read_jsonl(hn_jsonl, source="hn")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            print(f"    ! hn collect partial/failed: {e}", file=sys.stderr)

    # Dedup by url (pullpush + reddit can overlap), keep highest-score, cap.
    seen, deduped = set(), []
    for r in sorted(pool, key=lambda r: abs(r.get("score") or 0), reverse=True):
        u = r.get("url")
        if u and u in seen:
            continue
        if u:
            seen.add(u)
        deduped.append(r)
    pool = deduped[:140]
    save(out, pool)
    print(f"    collected {len(pool)} raw records")
    return pool


def read_jsonl(path: Path, *, source: str) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
            rows.append({
                "title": d.get("title") or d.get("text", "")[:120],
                "score": d.get("score") or 0,
                "url": d.get("url", ""),
                "source": source,
            })
        except json.JSONDecodeError:
            continue
    return rows


def sys_exe() -> str:
    return sys.executable or "python3"


# --------------------------------------------------------------------------- #
# Stage 3 · CURATE                                                             #
# --------------------------------------------------------------------------- #

def stage_curate(idea: str, scope: dict, pool: list[dict], wd: Path,
                 max_voices: int, dry: bool) -> list[dict]:
    out = wd / "03-voices.json"
    if dry and out.exists():
        return cached(out)
    if not pool:
        print("    ! empty pool — cannot curate. Provide voices manually.", file=sys.stderr)
        return []

    players = scope.get("players", [])
    sys = ("You are a strict research analyst curating evidence. You RUTHLESSLY "
           "reject off-topic noise. Output STRICT JSON only.")
    # Send a generous candidate window so the LLM has enough relevant items to find.
    over = min(len(pool), max(max_voices * 3, 60))
    user = f"""Product idea: {idea}

Players / closest analogues: {json.dumps(players, ensure_ascii=False)}

Raw pool (title / score / url) — collected from broad communities, so it
contains some irrelevant chatter mixed with relevant signal:
{json.dumps(pool[:over], ensure_ascii=False, indent=1)}

TASK: score each candidate for relevance to the product idea, then return the
best ones. Output JSON:
{{
  "voices": [
    {{
      "id": "v01",
      "player": "<player id from list, or closest analogue id>",
      "title": "<concise english title, ≤80 chars>",
      "score": <int upvotes>,
      "url": "<original url>",
      "sentiment": "pos" | "neg",
      "relevance": 0 | 1 | 2 | 3,
      "why": "<≤12 words>"
    }}
  ]
}}

RELEVANCE RUBRIC:
  3 = directly about this product's need / pain / workaround / experience
      (e.g. for a pet feeder: "my auto feeder jammed", "I want timed feeding").
  2 = adjacent & informative — about the use-case, the buyers, an analogue
      device, or a related sub-problem this product touches.
  1 = same broad area but not about this product's job (generic chatter).
  0 = NOISE: memes, theft/lost packages, shipping rants, unboxing, jokes,
      unrelated off-topic. REJECT these.

SPECIAL CASE — only if the idea EXPLICITLY combines two distinct domains
(e.g. "physical keyboard FOR AI prompts" = hardware × AI): then a voice must
touch BOTH domains' intersection for a 3, and pure single-domain content caps
at 1. For ordinary single-concept products (a pet feeder, sleep earbuds,
a coffee maker), DO NOT apply this — score normally per the rubric above.

Return up to {over} scored candidates. Prefer diverse players + a mix of
pos/neg among the relevant ones. Be fair, not stingy: real on-topic voices
should land at 2-3."""
    res = chat_json(sys, user, temperature=0.2)
    candidates = res.get("voices", [])

    # Local relevance gate: keep relevance >= 2, fall back to >=1 if too few.
    def keep(min_rel):
        return [v for v in candidates if int(v.get("relevance", 0)) >= min_rel]
    voices = keep(2)
    if len(voices) < max(6, max_voices // 2):
        extra = [v for v in keep(1) if v not in voices]
        voices += extra
    # sort by relevance then |score|, cap, renumber ids
    voices.sort(key=lambda v: (int(v.get("relevance", 0)), abs(int(v.get("score", 0) or 0))), reverse=True)
    voices = voices[:max_voices]
    for i, v in enumerate(voices, 1):
        v["id"] = f"v{i:02d}"
    dropped = len(candidates) - len(voices)
    save(out, voices)
    print(f"    curated {len(voices)} voices (dropped {dropped} low-relevance/noise from {len(candidates)} candidates)")
    return voices


# --------------------------------------------------------------------------- #
# Stage 4 · CLUSTER                                                            #
# --------------------------------------------------------------------------- #

def stage_cluster(idea: str, target_market: str, scope: dict,
                  voices: list[dict], wd: Path, dry: bool) -> dict:
    out = wd / "04-cluster.json"
    if dry and out.exists():
        return cached(out)
    cluster_input = {
        "category": idea,
        "target_market": target_market,
        "players": scope.get("players", []),
        "voices": [{
            "id": v["id"], "player": v["player"], "title": v["title"],
            "score": v["score"], "url": v["url"],
            "excerpt": v["title"], "sentiment_hint": v["sentiment"],
        } for v in voices],
    }
    prompt = (ROOT / "templates/pipeline/prompts/cluster.txt").read_text(encoding="utf-8")
    user = prompt.replace("<<< INPUT JSON >>>",
                          json.dumps(cluster_input, ensure_ascii=False, indent=2))
    res = chat_json("You output strict JSON only. No prose.", user, temperature=0.2)
    save(out, res)
    print(f"    clustered into {len(res.get('themes', []))} themes")
    return res


# --------------------------------------------------------------------------- #
# Stage 5 · SYNTHESIZE                                                         #
# --------------------------------------------------------------------------- #

def stage_synth(idea: str, target_market: str, scope: dict, voices: list[dict],
                cluster: dict, wd: Path, dry: bool) -> dict:
    out = wd / "05-synth.json"
    if dry and out.exists():
        return cached(out)
    sys = "You are a senior category analyst. Output STRICT JSON only."
    user = f"""Product idea: {idea}
Target market: {target_market}
Mode: {scope.get('mode')}
Players: {json.dumps(scope.get('players', []), ensure_ascii=False)}
Themes: {json.dumps(cluster.get('themes', []), ensure_ascii=False)}
Voice count: {len(voices)}

Synthesize the strategic layer. Output JSON:
{{
  "thesis": "<one contrarian sentence, ≤80 chars>",
  "deck": "<one paragraph subhead, ≤180 chars>",
  "verdict": {{
    "status": "real" | "partial" | "insufficient",
    "rationale": "<≤120 chars>"
  }},
  "key_findings": ["<finding 1>", ... 4 total],
  "opportunity": {{ "label": "★ <gap name>", "summary": "<≤100 chars>" }},
  "paths": [
    {{"id":"path-a","label":"Path A · <name>","core":"<core>","description":"<≤80 chars>","time":"<e.g. 12 个月>","investment":"<e.g. $1-3M>","moat":"low|mid|high|extreme","recommended":true}},
    {{"id":"path-b", ...}}, {{"id":"path-c", ...}}
  ],
  "risks": [
    {{"id":"R-01","title":"<risk>","scenario":"<≤80 chars>","severity":"low|mid|high","mitigation":"<≤80 chars>"}},
    ... 3-5 total
  ]
}}
Rules: status=real only if voices clearly show real demand. exactly 1 recommended path."""
    res = chat_json(sys, user, temperature=0.4)
    save(out, res)
    return res


# --------------------------------------------------------------------------- #
# Stage 6 · ASSEMBLE                                                           #
# --------------------------------------------------------------------------- #

PALETTE = {
    "player": ["#2c2f3a", "#4a4e5b", "#4a4e5b", "#6b6f7c", "#6b6f7c", "#6b6f7c"],
    "win": "#5b7a52", "pain": "#a0533c", "neutral": "#80766a",
}


def stage_assemble(slug: str, idea: str, target_market: str, scope: dict,
                   voices: list[dict], cluster: dict, synth: dict) -> dict:
    import datetime
    today = datetime.date.today().isoformat()

    # Players with layout positions (spread on a circle)
    players_in = scope.get("players", [])
    import math
    players = []
    n = max(1, len(players_in))
    for i, p in enumerate(players_in):
        ang = (i / n) * 2 * math.pi
        players.append({
            "id": p["id"], "name": p["name"],
            "color": PALETTE["player"][min(i, len(PALETTE["player"]) - 1)],
            "size": 26 - i * 2 if i < 5 else 16,
            "x": round(0.5 + 0.32 * math.cos(ang), 3),
            "y": round(0.45 + 0.30 * math.sin(ang), 3),
            "summary": p.get("summary", ""),
        })

    # Themes from cluster (ensure colors + polarity normalization)
    themes = []
    for t in cluster.get("themes", []):
        pol = t.get("polarity", "neutral")
        color = PALETTE.get("win" if pol == "win" else "pain" if pol == "pain" else "neutral")
        themes.append({
            "id": t["id"], "label": t["label"],
            "color": t.get("color") or color,
            "size": t.get("size", 14),
            "x": t.get("x", 0.5), "y": t.get("y", 0.5),
            "polarity": pol, "summary": t.get("summary", ""),
        })

    # Voices with theme assignments
    vt = cluster.get("voice_themes", {})
    voices_out = []
    for v in voices:
        tids = vt.get(v["id"], [])
        if not tids and themes:
            tids = [themes[0]["id"]]
        voices_out.append({
            "id": v["id"], "player": v["player"], "title": v["title"],
            "score": int(v["score"]) if str(v["score"]).lstrip("-").isdigit() else 0,
            "url": v["url"], "sentiment": v["sentiment"],
            "themes": tids, "collected_at": today,
        })

    # Opportunity node
    opp = synth.get("opportunity", {})
    opportunity = {
        "id": "opp",
        "label": opp.get("label", "★ 机会区"),
        "color": "#5b7a52", "size": 30, "x": 0.42, "y": 0.18,
        "summary": opp.get("summary", ""),
    }

    # Edges: cluster edges + voice→theme + theme→opp
    edges = list(cluster.get("edges", []))
    for v in voices_out:
        for tid in v["themes"]:
            edges.append({"from": v["id"], "to": tid, "w": 1})
    # connect 2 strongest 'win' themes to opp
    win_themes = [t["id"] for t in themes if t["polarity"] == "win"][:2]
    for tid in win_themes:
        edges.append({"from": tid, "to": "opp", "w": 2})

    # Evidence counts
    counts = {
        "raw_voices": len(voices_out),
        "marketplace": 0,
        "editorials": 0,
        "simulated": 0,
    }

    return {
        "schema_version": "1.0",
        "meta": {
            "slug": slug, "idea": idea, "mode": scope.get("mode", "EXISTING"),
            "timestamp": today, "target_market": target_market,
            "thesis": synth.get("thesis", ""), "deck": synth.get("deck", ""),
        },
        "verdict": {
            "status": synth.get("verdict", {}).get("status", "partial"),
            "rationale": synth.get("verdict", {}).get("rationale", ""),
            "evidence_counts": counts,
            "key_findings": synth.get("key_findings", []),
        },
        "players": players,
        "themes": themes,
        "voices": voices_out,
        "opportunity": opportunity,
        "edges": edges,
        "paths": synth.get("paths", []),
        "risks": synth.get("risks", []),
    }


# --------------------------------------------------------------------------- #
# Orchestration                                                                #
# --------------------------------------------------------------------------- #

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--idea")
    ap.add_argument("--target-market", default="US")
    ap.add_argument("--max-voices", type=int, default=24)
    ap.add_argument("--mode", choices=["EXISTING", "NON_STOCK"],
                    help="Force market mode (overrides LLM auto-detection)")
    ap.add_argument("--skip-collect", action="store_true")
    ap.add_argument("--dry-run", action="store_true",
                    help="Use cached stage outputs; no LLM/network")
    args = ap.parse_args()

    wd = work_dir(args.slug)
    # idea can be recovered from cached scope if omitted on resume
    idea = args.idea
    scope_cache = cached(wd / "01-scope.json")
    if not idea and scope_cache:
        idea = scope_cache.get("_idea")
    if not idea:
        ap.error("--idea required for a fresh run")

    print(f"▶ SCOPE  ({idea})")
    scope = stage_scope(idea, args.target_market, wd, args.dry_run, args.mode)
    scope["_idea"] = idea
    save(wd / "01-scope.json", scope)
    print(f"    mode={scope.get('mode')}  subs={scope.get('subreddits')}  players={[p['id'] for p in scope.get('players',[])]}")

    print("▶ COLLECT")
    pool = stage_collect(scope, wd, args.skip_collect or args.dry_run)

    print("▶ CURATE")
    voices = stage_curate(idea, scope, pool, wd, args.max_voices, args.dry_run)
    if not voices:
        print("✗ no voices — aborting. Inspect collected/<slug>/02-pool.json", file=sys.stderr)
        return 1

    print("▶ CLUSTER")
    cluster = stage_cluster(idea, args.target_market, scope, voices, wd, args.dry_run)

    print("▶ SYNTHESIZE")
    synth = stage_synth(idea, args.target_market, scope, voices, cluster, wd, args.dry_run)

    print("▶ ASSEMBLE")
    data = stage_assemble(args.slug, idea, args.target_market, scope, voices, cluster, synth)
    data_path = ROOT / "data" / f"{args.slug}.json"
    save(data_path, data)

    print("▶ TRANSLATE (EN backfill)")
    try:
        subprocess.run([sys_exe(), str(ROOT / "scripts/translate_data.py"), str(data_path)],
                       check=True, timeout=180)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print(f"    ! translate skipped: {e} (report still works in zh)", file=sys.stderr)

    print("▶ VALIDATE")
    rc = subprocess.run([sys_exe(), str(ROOT / "scripts/validate_data.py"), str(data_path)])
    if rc.returncode != 0:
        print("✗ validation failed — data written but not rendered. Fix and re-run --from render.",
              file=sys.stderr)
        return 1

    print("▶ RENDER")
    subprocess.run([sys_exe(), str(ROOT / "scripts/render_report.py"), args.slug], check=True)
    subprocess.run([sys_exe(), str(ROOT / "scripts/render_index.py")], check=True)

    print(f"\n✓ done → dist/{args.slug}.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
