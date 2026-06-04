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
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from llm_client import chat_json, load_dotenv  # type: ignore

STAGES = ["scope", "collect", "curate", "cluster", "synth", "render"]


def _synth_model():
    """The qualitative synthesis/narrative stages use the (slower, higher-quality)
    reasoning model; everything else uses the fast non-thinking default. Returns the
    model name or None (→ chat_json falls back to OPENAI_MODEL)."""
    import os
    load_dotenv()
    return os.environ.get("OPENAI_SYNTH_MODEL") or None


# --------------------------------------------------------------------------- #
# Data-quality helpers (used by collect + curate)                             #
# --------------------------------------------------------------------------- #

def _norm_title(t: str) -> str:
    """Normalized title for near-duplicate collapse (lowercase, alnum-only, capped)."""
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()[:90]

# Marks a product LISTING / ad / affiliate-spam post (not a real user discussion).
# These flooded a hosted run: "DEESS ... ipl hair remover ... 350000 flashes",
# "Painless Hair Removal ... Portable Waterproof Electric ...".
_LISTING_RE = re.compile(
    r"(\b\d{3,}\s*(flash|flashes|mah|lumens|pcs|count|sheets|pack)\b"
    r"|for\s+face\s*&?\s*body|home\s+use|portable\s+waterproof|waterproof\s+electric"
    r"|free\s+shipping|best\s*seller|on\s+sale|buy\s+now|coupon|discount\s+code"
    r"|\bseries\s+\d|amazon\.com|aliexpress|\bsku\b)", re.I)

def _looks_like_listing(title: str) -> bool:
    t = title or ""
    if _LISTING_RE.search(t):
        return True
    # very long, comma-spec-heavy titles read like catalog entries, not posts
    if len(t) > 110 and t.count(",") >= 3:
        return True
    return False


# Marks a BRAND SELF-PROMO / official-marketing post (softer than a listing): launch
# announcements, founder "I built this" plugs, discount/affiliate pushes, giveaways.
# Checked against title + body so we catch posts that read normal but are an ad.
_PROMO_RE = re.compile(
    r"(we(?:'re| are)?\s+(?:just\s+)?(?:launch|excited|thrilled|proud|introduc)"
    r"|introducing\s+(?:the\s+|our\s+|my\s+)"
    r"|our\s+(?:new|latest)\b|just\s+launched|now\s+available|just\s+dropped"
    r"|check\s+(?:it|us|them)\s+out|check\s+out\s+(?:my|our|the)\b"
    r"|link\s+in\s+(?:bio|comments|profile)"
    r"|\buse\s+code\b|\bpromo\s*code\b|coupon\s+code"
    r"|\d{1,2}\s*%\s*off\s+(?:with|using|code|when|today|now|site-?wide|store-?wide|your\s+order)"
    r"|\bdm\s+me\b|shop\s+now|order\s+now|pre-?order|grab\s+yours|limited\s+time\s+offer"
    r"|\bgiveaway\b|\bkickstarter\b|\bindiegogo\b|early\s+bird"
    r"|i\s+(?:built|created|designed|developed)\s+(?:a|an|this|my)\b"
    r"|(?:my|our)\s+(?:startup|company|brand)\b"
    r"|(?:we|our\s+team)\s+(?:designed|developed|created|built|make|are\s+selling))", re.I)

def _looks_promotional(title: str, text: str = "") -> bool:
    """Brand self-promotion / official ad, vs an organic user post."""
    blob = ((title or "") + " " + (text or "")).strip()
    if not blob:
        return False
    return bool(_PROMO_RE.search(blob))


def _is_ad(title: str, text: str = "") -> bool:
    """Either a marketplace listing OR brand self-promotion — not a real user voice."""
    return _looks_like_listing(title) or _looks_promotional(title, text)


def _sub_of(url: str) -> str:
    m = re.search(r"/r/([A-Za-z0-9_]+)", url or "")
    return m.group(1).lower() if m else "other"

def _balance_sources_idx(records: list, limit: int, cap_frac: float = 0.55) -> list:
    """Source balancing: pick up to `limit` indices from `records` (kept in their
    existing rank order) but cap any single subreddit at cap_frac of the output, so
    one community can't dominate (a real run was 99% r/sleep). Overflow from a capped
    sub is appended only if there's room — quality order is otherwise preserved."""
    cap = max(1, int(cap_frac * limit))
    out, used, overflow = [], {}, []
    for i, r in enumerate(records):
        if len(out) >= limit:
            break
        s = _sub_of(r.get("url"))
        if used.get(s, 0) < cap:
            out.append(i); used[s] = used.get(s, 0) + 1
        else:
            overflow.append(i)
    for i in overflow:
        if len(out) >= limit:
            break
        out.append(i)
    return out


def compute_quality(data: dict) -> dict:
    """Post-generation self-check (plan C): scan the FINAL voices for the failure
    modes a tester hit — repeated titles, ad listings, and over-concentration on a
    single source — and emit warnings so a bad run is caught instead of shipped."""
    from collections import Counter
    voices = data.get("voices", []) or []
    n = len(voices)
    q = {"voices": n, "warnings": []}
    if not n:
        q["warnings"].append("没有任何真实原声")
        return q
    dup = sum(c - 1 for c in Counter(_norm_title(v.get("title")) for v in voices).values() if c > 1)
    listing = sum(1 for v in voices if _looks_like_listing(v.get("title")))
    # final voices only carry the title (no body), so promo is judged title-level here
    promo = sum(1 for v in voices if _looks_promotional(v.get("title")))
    subs = Counter((re.search(r"/r/([A-Za-z0-9_]+)", v.get("url") or "") or [None, "other"])[1].lower()
                   for v in voices)
    top_sub, top_n = subs.most_common(1)[0]
    q["dup_title_pct"]   = round(dup / n * 100)
    q["listing_pct"]     = round(listing / n * 100)
    q["promo_pct"]       = round(promo / n * 100)
    q["top_source"]      = top_sub
    q["top_source_pct"]  = round(top_n / n * 100)
    q["other_pct"]       = round(sum(1 for v in voices if v.get("player") == "other") / n * 100)
    if q["dup_title_pct"] > 8:
        q["warnings"].append(f"重复标题占比 {q['dup_title_pct']}% 偏高")
    if q["listing_pct"] > 5:
        q["warnings"].append(f"疑似广告 listing 占比 {q['listing_pct']}% 偏高")
    if q["promo_pct"] > 6:
        q["warnings"].append(f"疑似官方广告/自荐占比 {q['promo_pct']}% 偏高")
    if q["top_source_pct"] > 72:
        q["warnings"].append(f"来源过度集中:r/{q['top_source']} 占 {q['top_source_pct']}%")
    return q


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
    sys_msg = ("You are a market-research scoping assistant. Output STRICT JSON only.")
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

RESEARCH BREADTH — this is demand research, so scope the WHOLE CATEGORY and the
underlying user NEED, not just the literal words. Treat adjectives/qualifiers in the
idea (e.g. "AI", "smart", "portable") as ONE angle, NOT a hard filter. Someone
researching "AI sleep earbuds" wants to understand the whole "sleep audio / blocking
noise to sleep" space — so include the qualified products AND the broader category
AND the alternatives real users compare against or hack together (e.g. passive
sleep earplugs like Loop, Bose Sleepbuds, white-noise apps), even if they don't have
the qualifier. Going too narrow misses the real demand picture.

Decide research scope. Output JSON:
{{
  {mode_instr}
  "search_idea": "<the CATEGORY/need in 2-4 ENGLISH words>",   // Reddit is English-only;
                                      // prefer the broad category term (e.g. "sleep earbuds")
                                      // over the narrow qualified one ("AI sleep earbuds").
  "subreddits": ["name", ...],        // 8-12 real ENGLISH subreddit names (no /r/).
                                      // Cast a WIDE net: the core product subs PLUS
                                      // adjacent communities where the target user
                                      // hangs out (the use-case, the problem, the
                                      // lifestyle, related gear). More angles = more
                                      // real signal. e.g. for sleep earbuds:
                                      // sleep, insomnia, tinnitus, headphones, audiophile,
                                      // SleepApnea, GetOutOfBed, ShiftWork, travel, biohackers.
  "hn_queries": ["query", ...],       // 5-8 ENGLISH search phrases (buyers/pain/alternatives/use-cases)
  "players": [                        // 6-10 across the WHOLE category the target user shops:
                                      // category leaders, adjacent alternatives, and what
                                      // people hack together — NOT only literal matches of
                                      // every adjective (include e.g. Loop for sleep earbuds).
    {{"id": "<lowercase_slug>", "name": "<English Brand Name>", "price": "<approx retail, e.g. ~$60 or $40-90; '' if truly unknown>", "website": "<the brand's OFFICIAL site domain you are confident about, e.g. loopearplugs.com or bose.com; '' if unsure — do NOT guess>"}}
  ],
  "rationale": "<one sentence why this mode>"
}}
CRITICAL: Reddit/HN content is English. ALL subreddits, queries, player names, and
search_idea MUST be in ENGLISH even if the product idea is written in another
language — otherwise the search returns nothing. subreddit names must be plausible
real subs. player ids lowercase a-z0-9_-."""
    res = chat_json(sys_msg, user, temperature=0.3)
    if mode_override:
        res["mode"] = mode_override   # hard-enforce even if model drifts
    save(out, res)
    return res


# --------------------------------------------------------------------------- #
# Stage 2 · COLLECT                                                            #
# --------------------------------------------------------------------------- #

# Target size of the RELEVANT base pool. Bigger pool → after dedup/clean/relevance
# filtering, MORE genuinely-relevant voices survive (user wants a deeper evidence base).
TARGET_POOL = 1999


def stage_collect(scope: dict, wd: Path, skip: bool, log=None) -> list[dict]:
    def _log(m):
        print(f"    {m}", flush=True)
        if log:
            try: log("COLLECT", m)
            except Exception: pass

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
    # Build a WIDE but on-topic query set (idea + intent modifiers + player
    # names) so we can pull ~999 RELEVANT records, not random noise.
    subs = scope.get("subreddits", [])
    player_names = [p.get("name", "") for p in scope.get("players", []) if p.get("name")]
    # Reddit/HN are English; use the English search phrase (scope.search_idea),
    # not the raw idea which may be Chinese (→ pullpush returns nothing).
    search_idea = scope.get("search_idea") or scope.get("_idea", "")
    mods = ["review", "problem", "alternative", "worth it", "complaint",
            "recommendation", "vs", "issues"]
    pp_queries = list(scope.get("hn_queries") or [])
    if search_idea:
        pp_queries += [f"{search_idea} {m}" for m in mods]
    pp_queries += player_names[:6]
    pp_queries = [q for q in dict.fromkeys(pp_queries) if q] or [search_idea]

    # TWO interchangeable Reddit sources wired in with automatic failover, so a
    # run survives one being down/rate-limited. Manual override via env:
    #   REDDIT_SOURCE = auto (default) | arcticshift | pullpush
    #   - auto:        Arctic Shift first; pullpush fills in if it comes up short.
    #   - arcticshift: Arctic Shift only.
    #   - pullpush:    pullpush only.
    import os as _os
    _src = (_os.environ.get("REDDIT_SOURCE") or "auto").lower()

    # --- Arctic Shift (PRIMARY) — a Reddit archive on separate infrastructure;
    # reliable + fast where pullpush rate-limits. Subreddit-scoped (and more
    # relevant). Needs product subreddits (we have them from scope). ---
    arctic_jsonl = wd / "arcticshift.jsonl"
    if subs and _src in ("auto", "arcticshift"):
        a_cmd = [sys_exe(), str(ROOT / "core/collect/arcticshift.py"),
                 "--subs", *subs, "--queries", *pp_queries[:6],
                 "--size", "100", "--pages", "3", "--target", str(TARGET_POOL),
                 "--out", str(arctic_jsonl)]
        _log(f"联网搜索 Reddit 真实评论(目标 {TARGET_POOL} 条相关)…")
        import re as _reA, time as _timeA
        try:
            proc = subprocess.Popen(a_cmd, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.PIPE, text=True)
            deadline = _timeA.time() + 180
            while True:
                line = proc.stderr.readline()
                if line:
                    m = _reA.search(r"(\d+)\s+unique", line)
                    if m:
                        _log(f"已搜索 {m.group(1)} 条 Reddit 真实评论… (目标 {TARGET_POOL})")
                elif proc.poll() is not None:
                    break
                if _timeA.time() > deadline:
                    proc.kill()
                    break
            proc.wait(timeout=5)
        except Exception as e:
            print(f"    ! arcticshift error: {e}", file=sys.stderr)
        pool += read_jsonl(arctic_jsonl, source="reddit")
        _log(f"Reddit 已搜索 {len(pool)} 条")

    # --- pullpush (FALLBACK / alternate) — runs when forced, or in auto mode if
    # Arctic Shift came up short (down, throttled, or no subs). Global full-text
    # search complements the subreddit-scoped archive. ---
    if pp_queries and (_src == "pullpush" or (_src == "auto" and len(pool) < 300)):
        cmd = [sys_exe(), str(ROOT / "core/collect/pullpush.py"),
               "--queries", *pp_queries,
               "--size", "100", "--target", str(TARGET_POOL),
               "--out", str(pullpush_jsonl)]
        if subs:
            cmd += ["--subs", *subs]
        _log("pullpush 补充搜索…")
        # Stream the climbing unique-count from pullpush's stderr so the UI shows
        # a real, accumulating number (the "999" progress feel).
        import re as _re3, time as _time
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.PIPE, text=True)
            deadline = _time.time() + 280
            while True:
                line = proc.stderr.readline()
                if line:
                    m = _re3.search(r"(\d+)\s+unique", line)
                    if m:
                        _log(f"已搜索 {m.group(1)} 条 Reddit 真实评论… (目标 {TARGET_POOL})")
                elif proc.poll() is not None:
                    break
                if _time.time() > deadline:
                    proc.kill()
                    break
            proc.wait(timeout=5)
        except Exception as e:
            print(f"    ! pullpush stream error: {e}", file=sys.stderr)
        pool += read_jsonl(pullpush_jsonl, source="reddit")
        _log(f"Reddit 已搜索 {len(pool)} 条")

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
    _log(f"已搜索 {len(pool)} 条原始记录,正在按相关性过滤…")

    # Rank by PRODUCT-KEYWORD relevance first, then score, before the cap —
    # otherwise low-score-but-on-product posts (e.g. a niche brand thread) get
    # culled by viral off-topic category posts.
    import re as _re
    kw = set()
    for src in [scope.get("_idea", ""), scope.get("search_idea", ""),
                *(p.get("name", "") for p in scope.get("players", [])),
                *(p.get("id", "") for p in scope.get("players", [])),
                *(scope.get("hn_queries") or [])]:
        for w in _re.findall(r"[a-z0-9]+", str(src).lower()):
            if len(w) >= 3 and w not in ("the", "and", "for", "with", "smart"):
                kw.add(w)

    def kw_hits(r):
        t = (str(r.get("title", "")) + " " + str(r.get("text", ""))).lower()
        return sum(1 for k in kw if k in t)

    # Dedup across ALL sources by a CANONICAL identity, then rank by
    # (keyword hits, score). The same Reddit post can come back from Arctic Shift,
    # pullpush AND reddit.py with cosmetically different URLs (trailing slash,
    # different slug); keying on the post/comment id (not the raw URL) guarantees
    # the multi-method pool never double-counts the same voice — so every derived
    # metric (counts, trend, share-of-voice) stays consistent no matter which
    # collectors ran. Non-Reddit (HN) falls back to a normalized URL.
    def _canon_key(r):
        u = (r.get("url") or "").strip()
        m = _re.search(r"/comments/([a-z0-9]+)(?:/[^/]*/([a-z0-9]+))?", u)
        if m:
            return "rid:" + (m.group(2) or m.group(1))   # comment id if present, else post id
        return "url:" + u.rstrip("/").lower()
    seen, deduped = set(), []
    for r in pool:
        k = _canon_key(r)
        if not r.get("url"):
            deduped.append(r); continue
        if k in seen:
            continue
        seen.add(k)
        deduped.append(r)
    deduped.sort(key=lambda r: (kw_hits(r), abs(r.get("score") or 0)), reverse=True)

    # Clean the ranked pool BEFORE it's used anywhere downstream, so both the LLM
    # curation AND its keyword-fallback draw from clean data:
    #   1. drop product-listing / ad / affiliate spam (real run got flooded by them);
    #   2. collapse near-identical TITLES (reposts/crossposts/spam share a title but
    #      have different post ids, so id-dedup alone left e.g. the SAME item 11x).
    # Done after ranking so the kept copy of each title is the strongest one.
    seen_t, cleaned, n_drop, n_ad = set(), [], 0, 0
    for r in deduped:
        # drop marketplace listings AND brand self-promo / official ads (title+body)
        if _is_ad(r.get("title"), r.get("text")):
            n_drop += 1; n_ad += 1; continue
        nt = _norm_title(r.get("title"))
        if nt and nt in seen_t:
            n_drop += 1; continue
        if nt:
            seen_t.add(nt)
        cleaned.append(r)

    # The pool is on-topic BY CONSTRUCTION (product-specific queries + product
    # subreddits). Ranked by keyword relevance; CURATE then makes the strict
    # per-item relevance call. Cap at the 999 target.
    pool = cleaned[:TARGET_POOL]
    if n_drop:
        _log(f"已剔除 {n_drop} 条重复/广告(其中疑似广告/官方自荐 {n_ad} 条)")
    n_kw = sum(1 for r in pool if kw_hits(r) >= 1)
    save(out, pool)
    _log(f"已锁定 {len(pool)} 条相关 Reddit 真实评论(其中 {n_kw} 条命中产品关键词)")
    return pool


def stage_discover_brands(idea: str, scope: dict, pool: list[dict], wd: Path,
                          dry: bool, log=None) -> dict:
    """Data-driven players: mine the real brand/product names that actually appear in
    the collected pool and merge the high-frequency ones the upfront LLM scoping
    missed into scope['players']. So famous products users keep comparing to (e.g.
    Loop for sleep earbuds) surface from the DATA, not from guesswork — and because
    this runs BEFORE curate, those voices get attributed to the new brands.
    Best-effort: any failure just leaves the scope players unchanged."""
    def _log(m):
        print(f"    {m}", flush=True)
        if log:
            try: log("COLLECT", m)
            except Exception: pass
    players = scope.get("players", []) or []
    if not pool or len(pool) < 8:
        return scope
    existing = {(p.get("id") or "").lower() for p in players}
    existing |= {(p.get("name") or "").lower() for p in players}
    titles = [(r.get("title") or "")[:130] for r in pool[:180] if r.get("title")]
    if len(titles) < 8:
        return scope
    sys_msg = ("You extract real consumer PRODUCT / BRAND names from forum post "
               "titles. Output STRICT JSON only.")
    def _user(batch):
        return (f"Product idea / category: {idea}\n\n"
            "Post titles:\n" + "\n".join("- " + t for t in batch) + "\n\n"
            "TASK: list the distinct real PRODUCT or BRAND names that appear and that "
            "a shopper in this category would consider or compare — direct competitors "
            "AND adjacent alternatives people compare against (even if they don't match "
            "every adjective of the idea). EXCLUDE generic words, subreddit names, "
            "feature words, and non-products. Count how many titles mention each. "
            "Also give each brand's OFFICIAL site domain if you are confident "
            "(e.g. loopearplugs.com), else '' — do NOT guess.\n"
            'Return JSON: {"brands":[{"name":"<Brand/Product>","count":<int>,"website":"<domain or \'\'>"}]}')
    # CHUNKED so a long title list can't blow past the model's output limit (the
    # finish_reason=length → empty failure a tester hit). Merge brand counts across
    # batches; any single failed batch is just skipped.
    merged = {}
    batches = [titles[s:s+30] for s in range(0, len(titles), 30)]

    def _mine(batch):
        return chat_json(sys_msg, _user(batch), temperature=0.2,
                         max_tokens=4096, timeout=120)

    from concurrent.futures import ThreadPoolExecutor, as_completed
    results = []
    if batches:
        with ThreadPoolExecutor(max_workers=min(6, len(batches))) as ex:
            futs = [ex.submit(_mine, b) for b in batches]
            for f in as_completed(futs):
                try:
                    results.append(f.result())
                except Exception as e:
                    _log(f"品牌挖掘某批跳过: {e}")
    for res in results:
        for b in (res.get("brands") or []):
            nm = (b.get("name") or "").strip()
            if not nm: continue
            key = nm.lower()
            if key not in merged:
                merged[key] = {"name": nm, "count": 0, "website": (b.get("website") or "").strip()}
            merged[key]["count"] += int(b.get("count") or 0)
            if not merged[key]["website"] and b.get("website"):
                merged[key]["website"] = b.get("website").strip()
    found = list(merged.values())
    import re as _re
    MAX_PLAYERS, MIN_MENTIONS = 14, 3
    new = []
    for b in sorted(found, key=lambda x: -(int(x.get("count") or 0))):
        if len(players) + len(new) >= MAX_PLAYERS:
            break
        name = (b.get("name") or "").strip()
        if not name or int(b.get("count") or 0) < MIN_MENTIONS:
            continue
        sid = _re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:30]
        if not sid or name.lower() in existing or sid in existing:
            continue
        existing.add(name.lower()); existing.add(sid)
        web = (b.get("website") or "").strip()
        new.append({"id": sid, "name": name, "price": "", "website": web})
    if new:
        scope["players"] = players + new
        save(wd / "01-scope.json", scope)
        _log("从真实原声补充高频品牌:" + "、".join(p["name"] for p in new))
    return scope


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
                "created_utc": d.get("created_utc"),
                "source": source,
            })
        except json.JSONDecodeError:
            continue
    return rows


def sys_exe() -> str:
    return sys.executable or "python3"


def collect_reddit_trend(query: str, years_back: int = 5, max_pages: int = 4) -> list[dict]:
    """DEPRECATED — do not wire into the pipeline. This ran a SEPARATE pullpush
    query independent of the main collected pool, whose ~12-month archive lag made
    the latest year read 0 and CONTRADICTED the corpus (e.g. trend showed 2026=0
    while 18 collected voices were from 2026). The trend now derives from the
    unified pool via corpus_yearly_trend() so every source stays consistent.
    Kept only for reference / manual diagnostics."""
    import datetime, urllib.parse, time as _t
    sys.path.insert(0, str(ROOT / "core/collect"))
    try:
        import pullpush  # type: ignore
    except Exception:
        return []
    BASE = "https://api.pullpush.io/reddit/search/submission/"
    this_year = datetime.date.today().year
    out = []
    for yr in range(this_year - years_back + 1, this_year + 1):
        after = int(datetime.datetime(yr, 1, 1).timestamp())
        before = int(datetime.datetime(yr, 12, 31, 23, 59).timestamp())
        seen, cur = set(), before
        for _ in range(max_pages):
            url = BASE + "?" + urllib.parse.urlencode(
                {"q": query, "size": 100, "after": after, "before": cur,
                 "sort_type": "created_utc", "sort": "desc"})
            try:
                data = pullpush._get(url).get("data", [])
            except Exception:
                break
            if not data:
                break
            for d in data:
                seen.add(d.get("id"))
            ts = [d.get("created_utc") for d in data if d.get("created_utc")]
            if not ts:
                break
            cur = min(ts) - 1
            if len(data) < 100:
                break
            _t.sleep(0.3)
        out.append({"period": str(yr), "count": len(seen)})
    # drop leading empty years (archive may not cover them)
    while out and out[0]["count"] == 0:
        out.pop(0)
    # NOTE: we intentionally keep the trailing current year even if it's low/0.
    # The template renders it as a "year-to-date (as of generation date)" partial
    # point (dashed + cutoff label), rather than dropping it.
    return out if sum(o["count"] for o in out) >= 10 else []


def corpus_yearly_trend(records: list[dict], years_back: int = 5) -> list[dict]:
    """Yearly post-count distribution of the ACTUAL collected records (Arctic Shift
    pool / kept voices), by created_utc. Preferred over collect_reddit_trend()
    because pullpush's archive lags ~12 months (recent years read 0 there) while
    Arctic Shift is current — and this is self-consistent with the voices the report
    actually displays, so it can never contradict them. The current year is partial
    (the template renders it as 'year-to-date as of the generation date')."""
    import datetime
    this_year = datetime.date.today().year
    counts: dict[int, int] = {}
    for r in records:
        ts = r.get("created_utc")
        try:
            y = datetime.datetime.utcfromtimestamp(int(ts)).year
        except (TypeError, ValueError):
            continue
        counts[y] = counts.get(y, 0) + 1
    lo = this_year - years_back + 1
    out = [{"period": str(y), "count": counts.get(y, 0)} for y in range(lo, this_year + 1)]
    while out and out[0]["count"] == 0:   # trim leading empty years
        out.pop(0)
    return out if sum(o["count"] for o in out) >= 10 else []


def compute_trend(records: list[dict], buckets: int = 12) -> list[dict]:
    """Bucket records by their created_utc into recent quarters → a discussion
    heat curve (Reddit volume over time). Uses the FULL collected pool, so it's a
    real volume signal, not just the kept voices. Returns [{period, count}]."""
    import datetime
    times = [int(r["created_utc"]) for r in records
             if r.get("created_utc") and str(r.get("created_utc")).isdigit()]
    if len(times) < 6:
        return []
    # quarter key per timestamp
    def qkey(ts):
        d = datetime.datetime.utcfromtimestamp(ts)
        return d.year * 4 + (d.month - 1) // 3   # sortable quarter index
    def qlabel(k):
        y, q = k // 4, k % 4 + 1
        return f"{y} Q{q}"
    counts = {}
    for ts in times:
        counts[qkey(ts)] = counts.get(qkey(ts), 0) + 1
    if not counts:
        return []
    lo, hi = min(counts), max(counts)
    lo = max(lo, hi - buckets + 1)               # keep the most recent N quarters
    return [{"period": qlabel(k), "count": counts.get(k, 0)} for k in range(lo, hi + 1)]


# --------------------------------------------------------------------------- #
# Stage 3 · CURATE                                                             #
# --------------------------------------------------------------------------- #

def stage_curate(idea: str, scope: dict, pool: list[dict], wd: Path,
                 max_voices: int, dry: bool, min_voices: int = 0) -> list[dict]:
    out = wd / "03-voices.json"
    if dry and out.exists():
        return cached(out)
    if not pool:
        print("    ! empty pool — cannot curate. Provide voices manually.", file=sys.stderr)
        return []

    players = scope.get("players", [])
    player_ids = [p["id"] for p in players]
    # NOTE: name this sys_msg, NOT `sys` — a local `sys` would shadow the stdlib
    # `sys` module and break `sys.stderr` later in this function.
    sys_msg = ("You are a strict research analyst curating evidence. You RUTHLESSLY "
               "reject off-topic noise. Output STRICT JSON only.")

    # Build a product-keyword set from idea + player names/ids + scope queries,
    # then RANK the pool by keyword relevance (not just upvotes) so the few
    # genuinely on-product items aren't buried under viral category noise.
    import re as _re
    kw = set()
    for src in [scope.get("_idea", ""), scope.get("search_idea", ""),
                *(p.get("name", "") for p in players),
                *player_ids, *(scope.get("hn_queries") or [])]:
        for w in _re.findall(r"[a-z0-9]+", str(src).lower()):
            if len(w) >= 3 and w not in ("the", "and", "for", "with", "ai", "smart"):
                kw.add(w)

    def kw_hits(r):
        text = (str(r.get("title", "")) + " " + str(r.get("text", ""))).lower()
        return sum(1 for k in kw if k in text)

    # rank: keyword hits first, then score
    ranked = sorted(pool, key=lambda r: (kw_hits(r), abs(r.get("score") or 0)), reverse=True)
    # Output is index-only (tiny) so we can afford a wide candidate window, but keep
    # the request small enough to finish reliably from a remote host (cross-border
    # latency to some LLM providers makes huge requests time out / return empty).
    over = min(len(ranked), 300)
    # Source-balanced candidate window: cap any single subreddit at 55% so the LLM
    # sees a mix of communities (one run was 99% r/sleep), NOT just the dominant one.
    # The LLM still gates relevance, so balancing the input can't pull in off-topic.
    cand_idx = _balance_sources_idx(ranked, over, cap_frac=0.55)
    # include a short BODY excerpt (x) so the LLM can tell organic discussion from a
    # brand ad that happens to have a normal-looking title.
    indexed = [{"i": i, "t": (ranked[i].get("title") or "")[:120],
                "x": (ranked[i].get("text") or "").strip()[:140],
                "s": ranked[i].get("score") or 0, "sub": _sub_of(ranked[i].get("url"))}
               for i in cand_idx]
    pool = ranked  # reconstruct voices from this same ranked order

    def build_user(cands):
        return f"""Product idea: {idea}
Player ids: {json.dumps(player_ids, ensure_ascii=False)}

Candidate pool (i = index, t = title, x = body excerpt, s = score, sub = subreddit):
{json.dumps(cands, ensure_ascii=False)}

TASK: score each candidate's relevance to the product idea. Return ONLY the
ones worth keeping, as compact JSON (NO titles/urls — just the index):
{{
  "keep": [
    {{ "i": <index>, "player": "<a player id, or 'other'>", "sentiment": "pos"|"neg", "relevance": 1|2|3 }}
  ]
}}

RELEVANCE:
  3 = directly about this product's need / pain / workaround / experience.
  2 = adjacent & informative (use-case, buyers, analogue device, sub-problem).
  1 = same broad area but not about this product's job.
  (omit anything that's noise: memes, theft, shipping rants, unboxing, jokes,
   unrelated off-topic — just don't include them.)
  HARD REJECT (never keep) — we want REAL user discussion, not marketing:
   - product LISTINGS / ad copy / affiliate spam — titles that read like a shop
     catalog entry (model/series numbers, spec dumps like "350000 flashes",
     "for face & body home use", "portable waterproof electric", promo phrases).
   - BRAND SELF-PROMOTION / official marketing: launch & "now available"
     announcements, "introducing our new…", founder/maker self-plugs ("I built
     this", "my startup/brand"), discount-code / coupon / "% off" pushes,
     giveaways, Kickstarter/Indiegogo plugs, "DM me / link in bio / shop now".
     If the post is the SELLER talking up their own product rather than a user
     sharing a genuine experience or complaint, drop it.

SENTIMENT — classify honestly, do NOT default to "pos":
  neg = a complaint, problem, disappointment, defect, leak, return, "wish it
        did X", "stopped working", price/value gripe, or asking for an
        alternative because the current option fails.
  pos = praise, recommendation, satisfaction, "love it", solved my problem.
  A healthy product category has BOTH — expect a meaningful share of neg.

SPECIAL CASE — only if the idea EXPLICITLY combines two distinct domains
(e.g. "keyboard FOR AI prompts" = hardware × AI): require both-domain
intersection for a 3, single-domain caps at 1. For ordinary single-concept
products, score normally.

Keep every genuinely relevant item in THIS batch (real on-topic items are 2-3); omit the rest."""

    # CHUNKED curation (plan A): many small LLM calls instead of one big one. A
    # smaller request completes far more reliably from a far region (the hosted
    # cross-border timeout / empty-content failure a tester hit), and one bad chunk
    # only loses that chunk — the others still curate with the LLM, so we don't
    # collapse the whole run to the weak keyword-only fallback. Indices stay global.
    CHUNK = 90
    parts = [indexed[s:s + CHUNK] for s in range(0, len(indexed), CHUNK)]
    keep, chunk_fail, chunk_total = [], 0, len(parts)

    def _curate_chunk(part):
        res = chat_json(sys_msg, build_user(part), temperature=0.2, max_tokens=5000, timeout=150)
        return res.get("keep", []) or []

    # Chunks are independent (indices are global) → run them concurrently so curate
    # is bounded by the SLOWEST chunk, not their sum. One bad chunk only loses itself.
    from concurrent.futures import ThreadPoolExecutor, as_completed
    if parts:
        with ThreadPoolExecutor(max_workers=min(6, len(parts))) as ex:
            futs = [ex.submit(_curate_chunk, p) for p in parts]
            for f in as_completed(futs):
                try:
                    keep.extend(f.result())
                except Exception as e:
                    chunk_fail += 1
                    print(f"    ! curate chunk failed ({e})", file=sys.stderr)
    if chunk_fail:
        print(f"    ! {chunk_fail}/{chunk_total} 个筛选批次失败,其余批次仍由大模型筛选,"
              f"缺口用关键词兜底", file=sys.stderr)

    # Reconstruct voices from the pool by index (titles/urls never altered by LLM).
    recon = []
    for k in keep:
        try:
            idx = int(k.get("i"))
        except (TypeError, ValueError):
            continue
        if not (0 <= idx < len(pool)):
            continue
        r = pool[idx]
        rel = int(k.get("relevance", 1) or 1)
        # Unattributed / "other" voices stay "other" — do NOT dump them onto the
        # first player (that falsely inflated the leading brand to ~90% share).
        player = k.get("player") if k.get("player") in player_ids else "other"
        recon.append({
            "id": "", "player": player,
            "title": (r.get("title") or "")[:120],
            "score": int(r.get("score") or 0),
            "url": r.get("url", ""),
            "created_utc": r.get("created_utc"),
            "sentiment": "neg" if k.get("sentiment") == "neg" else "pos",
            "themes": [], "relevance": rel,
        })

    # Keep strong (relevance>=2) first, then fill with weaker-but-on-topic
    # (relevance==1) up to the cap — we want MORE real voices, so we don't
    # discard the adjacent ones unless we're already at the cap.
    strong = sorted([v for v in recon if v["relevance"] >= 2],
                    key=lambda v: (v["relevance"], abs(v["score"])), reverse=True)
    weak = sorted([v for v in recon if v["relevance"] == 1],
                  key=lambda v: abs(v["score"]), reverse=True)
    voices = (strong + weak)[:max_voices]

    # Guarantee a MINIMUM count when the pool is large enough: pad with the most
    # keyword-relevant pool items the LLM didn't explicitly keep (still on-topic
    # by keyword match). Lets us promise e.g. "≥99 real voices" without inventing
    # data — capped by what the pool actually contains.
    target = min(min_voices, len(ranked)) if min_voices else 0
    if len(voices) < target:
        have = {v.get("url") for v in voices}
        have_t = {_norm_title(v.get("title")) for v in voices}
        NEG = ("problem", "issue", "broke", "broken", "leak", "disappoint", "return",
               "refund", "worst", "hate", "complaint", "weak", "fail", "stuck",
               "defect", "scam", "avoid", "annoying", "frustrat")
        # iterate a source-balanced order so the fallback also spans communities
        ranked_bal = [ranked[i] for i in _balance_sources_idx(ranked, len(ranked), cap_frac=0.55)]
        def _pad(min_kw):
            for r in ranked_bal:
                if len(voices) >= target:
                    break
                u = r.get("url"); nt = _norm_title(r.get("title"))
                # NEVER pad with listings or duplicate titles — that's the junk we
                # cleaned out. Only the keyword-relevance bar is relaxed in tiers.
                if (not u or u in have or kw_hits(r) < min_kw
                        or _is_ad(r.get("title"), r.get("text")) or (nt and nt in have_t)):
                    continue
                have.add(u); have_t.add(nt)
                title = (r.get("title") or "")[:120]; tl = title.lower()
                pl = next((pid for pid in player_ids if pid and pid in tl), "other")
                voices.append({
                    "id": "", "player": pl, "title": title,
                    "score": int(r.get("score") or 0), "url": u,
                    "created_utc": r.get("created_utc"),
                    "sentiment": "neg" if any(w in tl for w in NEG) else "pos",
                    "themes": [],
                })
        # TIERED to honour the floor without re-adding junk: prefer strongly-relevant
        # (>=2 keyword hits); only if still short, relax to weaker-but-clean (>=1).
        _pad(2)
        if len(voices) < target:
            _pad(1)

    for i, v in enumerate(voices, 1):
        v["id"] = f"v{i:02d}"
        v.pop("relevance", None)
    save(out, voices)
    print(f"    curated {len(voices)} voices (from {len(keep)} kept of {len(indexed)} candidates)")
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
# Stage 4b · DECOMPOSE  (user & demand decomposition — VOC-style, for R&D)     #
# --------------------------------------------------------------------------- #

def stage_decompose(idea: str, target_market: str, scope: dict,
                    voices: list[dict], cluster: dict, wd: Path, dry: bool) -> dict:
    """Decompose the real voices into product-R&D-useful structure (Shulex/VOC-AI
    style, 5W1H): usage scenarios, personas, JTBD, unmet needs, workarounds, WTP.
    Each item cites supporting voice ids (traceable). Output 简体中文."""
    out = wd / "04b-demand.json"
    if dry and out.exists():
        return cached(out)
    mode = scope.get("mode", "EXISTING")
    vlist = [{"id": v["id"], "t": (v.get("title") or "")[:90], "s": v.get("sentiment")}
             for v in voices]
    theme_labels = [t.get("label") for t in cluster.get("themes", [])]
    mode_hint = ("非存量/需求验证:重点放在 unmet_needs(未被满足的期望)、workarounds"
                 "(用户现在怎么凑合)、wtp(支付意愿),用来判断需求真伪与该做什么。"
                 if mode == "NON_STOCK" else
                 "存量市场:重点放在不同人群/场景下的取舍,以及围绕真实痛点的改进方向。")
    user = f"""产品: {idea}
目标市场: {target_market}
市场类型: {mode}
需求主题: {json.dumps(theme_labels, ensure_ascii=False)}
真实用户原声 (id, t=标题, s=情绪):
{json.dumps(vlist, ensure_ascii=False)}

把这些真实声音拆解成对"产品研究与设计"有用的结构。每条尽量引用支撑它的真实 voice id
(evidence, 1-3 个),保证可溯源。全部用简体中文。输出 JSON:
{{
  "jtbd": "<用户根本要解决的任务(第一性原理,一句话)>",
  "scenarios": [ {{"name":"<使用场景名,如 露营徒步/差旅通勤>","share":<该场景在原声里的大致占比,整数 0-100>,"summary":"<谁在什么情境下、为什么用>","evidence":["v.."]}} ],
  "personas":  [ {{"name":"<人群名>","share":<该人群大致占比,整数 0-100>,"summary":"<画像+主场景+核心诉求>","evidence":["v.."]}} ],
  "unmet_needs":[ {{"need":"<用户希望但现状做不到的事>","summary":"<期望与现实的落差>","evidence":["v.."]}} ],
  "workarounds":[ {{"approach":"<用户现在的替代/凑合方案>","summary":"<为什么不够好>","evidence":["v.."]}} ],
  "wtp": "<价格带 + 支付意愿 / 值不值的洞察(一段)>"
}}
数量: scenarios 3-6、personas 2-4、unmet_needs 3-5、workarounds 2-4。
方法论: 客观唯物(只基于上面真实声音、带证据 id,不空谈)、辩证(点出取舍/张力)、
第一性(回到根本任务)。{mode_hint}
不要编造数据;evidence 必须是上面出现过的真实 id。"""
    res = chat_json("你是资深用户研究员,只输出严格 JSON。", user, temperature=0.3, max_tokens=6000,
                    model=_synth_model())
    # keep only valid voice ids in evidence (drop any hallucinated refs)
    valid_ids = {v["id"] for v in voices}
    for key in ("scenarios", "personas", "unmet_needs", "workarounds"):
        for item in (res.get(key) or []):
            if isinstance(item, dict):
                item["evidence"] = [e for e in (item.get("evidence") or []) if e in valid_ids][:3]
    save(out, res)
    print(f"    decomposed: {len(res.get('scenarios',[]))} scenarios, "
          f"{len(res.get('personas',[]))} personas, {len(res.get('unmet_needs',[]))} needs")
    return res


# --------------------------------------------------------------------------- #
# Stage 5 · SYNTHESIZE                                                         #
# --------------------------------------------------------------------------- #

def stage_synth(idea: str, target_market: str, scope: dict, voices: list[dict],
                cluster: dict, wd: Path, dry: bool) -> dict:
    out = wd / "05-synth.json"
    if dry and out.exists():
        return cached(out)
    sys_msg = "You are a senior category analyst. Output STRICT JSON only."
    user = f"""Product idea: {idea}
Target market: {target_market}
Mode: {scope.get('mode')}
Players: {json.dumps(scope.get('players', []), ensure_ascii=False)}
Themes: {json.dumps(cluster.get('themes', []), ensure_ascii=False)}
Voice count: {len(voices)}

LANGUAGE: write EVERY human-readable string in 简体中文 (Chinese), regardless of the
idea's language. Keep brand names and technical terms (FDA, RAG, prompt…) as-is.

Synthesize the strategic layer. Output JSON:
{{
  "thesis": "<一句有反差的核心论点, ≤40 字>",
  "deck": "<一段副标题, ≤90 字>",
  "verdict": {{
    "status": "real" | "partial" | "insufficient",
    "rationale": "<≤60 字>"
  }},
  "key_findings": ["<核心发现1>", ... 共4条],
  "section_insights": {{
    "market": "<市场洞察>",
    "user": "<用户洞察>",
    "competitive": "<竞争洞察>",
    "opportunity": "<机会洞察>",
    "risk": "<风险洞察>"
  }},
  "opportunity": {{ "label": "★ <空白机会名>", "summary": "<≤50 字>" }},
  "paths": [
    {{"id":"path-a","label":"方向 A · <名字>","core":"<这个方向的核心思路>","hypothesis":"<它赌的是什么假设>","evidence":"<支撑它的真实用户证据,引用现象/占比>","open_questions":["<还需验证的关键问题1>","<问题2>"],"risk":"<最大不确定性>"}},
    {{"id":"path-b", ...}}, {{"id":"path-c", ...}}
  ],
  "risks": [
    {{"id":"R-01","title":"<risk>","scenario":"<≤80 chars>","severity":"low|mid|high","mitigation":"<≤80 chars>"}},
    ... 3-5 total
  ]
}}
section_insights 写作方法论(每条 2-4 句、≤130 字、简体中文,必须遵循):
  · 客观唯物:只从上面的真实用户声音/数据出发下判断,带证据(谁说了什么、占比多少),
    不空谈愿景、不写正确的废话。
  · 辩证:点出这个品类的核心矛盾/张力(如「便携 vs 浓缩品质」「低价走量 vs 高端体验」),
    以及它当前正往哪个方向演化。
  · 第一性原理:回到最根本的 job-to-be-done —— 用户真正要解决的根本问题是什么(物理/场景
    本质),而不是停留在表面功能或类比。
  · 安克「浅海」方法论:判断这是不是一片浅海 = 有真实且普遍的未满足需求 + 现有玩家有明显
    结构性短板 + 新进入者能做出用户可感知的差异。痛点够不够痛、够不够普遍。
  每个字段的侧重:
    market=行业所处阶段+根本驱动力+核心矛盾+演化方向;
    user=根本 job-to-be-done + 好评/差评暴露的底层未满足需求 + 痛点强度;
    competitive=格局松紧 + 主导者的结构性短板 + 是否浅海;
    opportunity=基于上述矛盾最该切的差异化空白 + 为什么现有玩家切不进去;
    risk=做这件事最根本的结构性风险(第一性:物理/成本/技术/需求真伪)。

paths 写作要求(2-3 个「可能的切入方向」,不是拍板的推荐):每个方向给出它赌的假设、
支撑它的真实用户证据、还需要验证的关键问题(open_questions)、和最大不确定性(risk)。
不要下「就做某某」的定论,而是给「如果相信 X 假设并验证了 Y,这条路值得一试,但要注意 Z」
式的思考脚手架,把判断权留给读者。
Rules: status=real only if voices clearly show real demand."""
    res = chat_json(sys_msg, user, temperature=0.4, max_tokens=8000, model=_synth_model())
    save(out, res)
    return res


# --------------------------------------------------------------------------- #
# Stage 6 · ASSEMBLE                                                           #
# --------------------------------------------------------------------------- #

PALETTE = {
    "player": ["#2c2f3a", "#4a4e5b", "#4a4e5b", "#6b6f7c", "#6b6f7c", "#6b6f7c"],
    "win": "#5b7a52", "pain": "#a0533c", "neutral": "#80766a",
}


def attribute_voices_by_name(players: list[dict], voices: list[dict]):
    """Deterministic brand attribution: a voice left 'other' by the LLM but whose
    TITLE clearly names exactly one tracked brand gets credited to that brand (the
    LLM under-credits). Only fills 'other' (never overrides a positive call); skips
    titles that name two+ brands (ambiguous 'X vs Y' comparisons). Word-boundary
    match on each brand's distinctive leading token."""
    import re as _re
    STOP = {"the", "app", "sleep", "earplugs", "earplug", "earbuds", "earbud",
            "buds", "pillow", "soft", "noise", "white", "basics", "pro", "plus"}
    def lead_token(name):
        ts = [w for w in _re.sub(r"[^a-z0-9 ]", " ", (name or "").lower()).split()
              if len(w) >= 3 and w not in STOP]
        return ts[0] if ts else None
    pmatch = [(p.get("id"), lead_token(p.get("name"))) for p in players]
    for v in voices:
        if v.get("player") not in ("other", None, ""):
            continue
        title = (v.get("title") or "").lower()
        hits = [pid for pid, tok in pmatch
                if tok and _re.search(r"\b" + _re.escape(tok) + r"\b", title)]
        if len(set(hits)) == 1:
            v["player"] = hits[0]
    return voices


def merge_brand_variants(players: list[dict], voices: list[dict]):
    """Collapse near-duplicate players to one entry PER BRAND, e.g.
    'Loop Quiet' / 'Loop' → 'Loop', 'Mack's Pillow Soft Earplugs' / 'Mack's' →
    'Mack's'. A player is a variant of another when one's word-tokens are a prefix
    of the other's (so 'Soundcore Sleep A30' vs 'A10' stay separate). The kept
    canonical is the one with the most voices (tie → fewer words); the others'
    voices are reassigned to it. Returns (deduped_players, voices)."""
    import re as _re
    def toks(s):
        return [t for t in _re.sub(r"[^a-z0-9 ]", " ", (s or "").lower()).split() if t]
    cnt = {}
    for v in voices:
        cnt[v.get("player")] = cnt.get(v.get("player"), 0) + 1
    order = sorted(players, key=lambda p: (-cnt.get(p.get("id"), 0), len(toks(p.get("name")))))
    kept, kept_toks, remap = [], [], {}
    def same_brand(a, b):
        n = min(len(a), len(b))
        if n == 0:
            return False
        if a[:n] == b[:n]:                 # one is a prefix of the other ('Loop' ⊂ 'Loop Quiet')
            return True
        # same ≥2-token brand line differing only in a trailing model code
        # ('Soundcore Sleep A10' vs 'A30'); guards against 'Loop Quiet' vs 'Loop Dream'
        return len(a) == len(b) >= 3 and a[:-1] == b[:-1]
    for p in order:
        pt = toks(p.get("name"))
        canon = None
        for kt, kid in kept_toks:
            if same_brand(pt, kt):
                canon = kid; break
        if canon:
            remap[p.get("id")] = canon
        else:
            kept.append(p); kept_toks.append((pt, p.get("id")))
    for v in voices:
        if v.get("player") in remap:
            v["player"] = remap[v["player"]]
    kept_ids = {p.get("id") for p in kept}
    return [p for p in players if p.get("id") in kept_ids], voices


def stage_assemble(slug: str, idea: str, target_market: str, scope: dict,
                   voices: list[dict], cluster: dict, synth: dict,
                   demand: dict | None = None) -> dict:
    import datetime
    today = datetime.date.today().isoformat()

    # Players with layout positions (spread on a circle)
    # Collapse near-duplicate brands first (e.g. 'Loop Quiet' + 'Loop' → 'Loop'),
    # reassigning their voices, so the brand table shows one row per real brand.
    players_in = scope.get("players", [])
    voices = attribute_voices_by_name(players_in, voices)   # credit explicit brand mentions
    players_in, voices = merge_brand_variants(players_in, voices)
    import math
    players = []
    n = max(1, len(players_in))
    for i, p in enumerate(players_in):
        ang = (i / n) * 2 * math.pi
        pl = {
            "id": p["id"], "name": p["name"],
            "color": PALETTE["player"][min(i, len(PALETTE["player"]) - 1)],
            "size": 26 - i * 2 if i < 5 else 16,
            "x": round(0.5 + 0.32 * math.cos(ang), 3),
            "y": round(0.45 + 0.30 * math.sin(ang), 3),
            "summary": p.get("summary", ""),
        }
        if p.get("price"):
            pl["price"] = p["price"]
        if p.get("website"):
            pl["website"] = p["website"]
        players.append(pl)

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

    # Voices with theme assignments. The cluster LLM sometimes references a
    # theme id it didn't emit in themes[] (more likely at 40 voices), so drop
    # any unknown theme id and fall back to the first theme.
    valid_theme_ids = {t["id"] for t in themes}
    vt = cluster.get("voice_themes", {})
    voices_out = []
    for v in voices:
        tids = [t for t in vt.get(v["id"], []) if t in valid_theme_ids]
        if not tids and themes:
            tids = [themes[0]["id"]]
        vout = {
            "id": v["id"], "player": v["player"], "title": v["title"],
            "score": int(v["score"]) if str(v["score"]).lstrip("-").isdigit() else 0,
            "url": v["url"], "sentiment": v["sentiment"],
            "themes": tids, "collected_at": today,
        }
        if v.get("created_utc"):
            vout["created_utc"] = v["created_utc"]
        voices_out.append(vout)

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

    # Drop any edge that points at a node we didn't emit (cluster LLM drift),
    # then dedup — keeps the graph/validator consistent at scale.
    valid_nodes = ({p["id"] for p in players} | valid_theme_ids
                   | {v["id"] for v in voices_out} | {"opp"})
    seen_e, clean_edges = set(), []
    for e in edges:
        a, b = e.get("from"), e.get("to")
        if a not in valid_nodes or b not in valid_nodes:
            continue
        key = (a, b)
        if key in seen_e:
            continue
        seen_e.add(key)
        clean_edges.append(e)
    edges = clean_edges

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
        "section_insights": synth.get("section_insights", {}),
        "user_demand": demand or {},
    }


# --------------------------------------------------------------------------- #
# Stage · EXPAND  (live deeper search — drives the radar "widen range" button) #
# --------------------------------------------------------------------------- #

def stage_expand(idea: str, target_market: str, scope: dict,
                 existing_voices: list[dict], themes: list[dict],
                 wd: Path, log=None, depth: int = 1) -> list[dict]:
    """Go back online with widened queries, keep only NEW (unseen) on-topic
    voices, and map each to an EXISTING theme. Returns voices in data.voices
    shape. This is the real, evidence-based counterpart to the radar's
    'widen scan range' gesture — no synthetic blips."""
    def _log(m):
        print(f"    [expand] {m}", flush=True)
        if log:
            try: log("EXPAND", m)
            except Exception: pass

    base = scope.get("_idea") or idea
    # Big intent vocabulary; ROTATE the emphasis by round (depth) so each expand
    # explores NEW angles — repeating the same queries is exactly why it felt fake.
    MODS = ["review", "problem", "alternative", "worth it", "complaint", "setup",
            "battery life", "vs", "recommendation", "issues", "best", "cheap",
            "durability", "leak", "warranty", "return", "comparison", "experience",
            "upgrade", "regret", "love it", "hate", "waste of money", "tips",
            "which one", "long term", "honest", "before you buy"]
    k = ((depth - 1) * 9) % len(MODS)
    mods = (MODS + MODS)[k:k + 14]            # rotating 14-mod window per round
    queries = list(scope.get("hn_queries") or [])
    queries += [f"{base} {m}" for m in mods]
    queries += [p.get("name", "") for p in scope.get("players", []) if p.get("name")]
    queries = [q for q in dict.fromkeys(queries) if q][:18]
    subs = scope.get("subreddits", [])

    # Light live collect: Arctic Shift (primary) → pullpush (fallback) + HN.
    asj, pp, hn = wd / "as-expand.jsonl", wd / "pp-expand.jsonl", wd / "hn-expand.jsonl"
    pool: list[dict] = []
    _log(f"联网深搜:{len(queries)} 组查询 × {subs or '*'} …")
    if subs:
        try:
            subprocess.run([sys_exe(), str(ROOT / "core/collect/arcticshift.py"),
                            "--subs", *subs, "--queries", *queries[:10],
                            "--size", "100", "--pages", str(2 + depth), "--out", str(asj)],
                           check=False, capture_output=True, timeout=210)
        except subprocess.TimeoutExpired:
            pass
        pool += read_jsonl(asj, source="reddit")
    if len(pool) < 100:   # fall back to pullpush if Arctic Shift came up short
        try:
            cmd = [sys_exe(), str(ROOT / "core/collect/pullpush.py"), "--queries", *queries,
                   "--size", "100", "--out", str(pp)]
            if subs:
                cmd += ["--subs", *subs]
            subprocess.run(cmd, check=False, capture_output=True, timeout=120)
        except subprocess.TimeoutExpired:
            pass
        pool += read_jsonl(pp, source="reddit")
    try:
        subprocess.run([sys_exe(), str(ROOT / "core/collect/hn.py"), "--query", *queries[:6],
                        "--hits", "40", "--out", str(hn)], check=False, capture_output=True, timeout=120)
    except subprocess.TimeoutExpired:
        pass
    pool += read_jsonl(hn, source="hn")

    # Dedup + drop anything already on the radar.
    seen = {v.get("url") for v in existing_voices if v.get("url")}
    uniq, us = [], set()
    for r in pool:
        u = r.get("url")
        if not u or u in seen or u in us:
            continue
        us.add(u)
        uniq.append(r)
    _log(f"去重后新候选 {len(uniq)} 条")
    if not uniq:
        return []

    # Curate the new pool in an isolated cache dir (don't clobber canonical stages).
    # Big batch per click (user wants a real jump, accepts the token cost): ~100 new
    # the first round, more each deeper round — bounded only by what's actually out
    # there after dedup against what's already shown.
    cap = 60 + depth * 40
    xwd = wd / "_expand"
    xwd.mkdir(exist_ok=True)
    _log(f"AI 打分相关性 · 从 {len(uniq)} 条里筛强相关…")
    new = stage_curate(idea, scope, uniq, xwd, cap, False)
    if not new:
        return []
    _log(f"归类到需求主题 · 整理 {len(new)} 条新原声…")

    # Map each new voice to an EXISTING theme id (LLM classify, keyword fallback).
    valid = {t["id"] for t in themes}
    theme_min = [{"id": t["id"], "label": t["label"]} for t in themes]
    items = [{"i": i, "t": (v.get("title") or "")[:120]} for i, v in enumerate(new)]
    amap = {}
    try:
        res = chat_json(
            "You output strict JSON only. No prose.",
            f"Existing themes: {json.dumps(theme_min, ensure_ascii=False)}\n"
            f"New voices: {json.dumps(items, ensure_ascii=False)}\n"
            "Assign each voice to the single best-fitting theme id. Use ONLY the "
            "given ids; if none fits, use the first theme's id. Return JSON: "
            '{"assign":[{"i":<index>,"theme":"<theme id>"}]}',
            temperature=0.2, max_tokens=2000)
        amap = {int(a["i"]): a.get("theme") for a in res.get("assign", []) if "i" in a}
    except Exception as e:
        _log(f"主题归类降级(关键词):{e}")

    def kw_theme(title):
        tl = title.lower()
        for t in themes:
            if str(t.get("label", "")).lower() in tl:
                return t["id"]
        return themes[0]["id"] if themes else None

    import datetime
    today = datetime.date.today().isoformat()
    start = len(existing_voices)
    out = []
    for j, v in enumerate(new):
        tid = amap.get(j)
        if tid not in valid:
            tid = kw_theme(v.get("title", ""))
        out.append({
            "id": f"vx{start + j + 1:02d}",
            "player": v.get("player", "other"),
            "title": v.get("title", ""),
            "score": int(v.get("score") or 0),
            "url": v.get("url", ""),
            "sentiment": "neg" if v.get("sentiment") == "neg" else "pos",
            "themes": [tid] if tid else [],
            "collected_at": today,
        })
    _log(f"深搜新增 {len(out)} 条真实原声")
    return out


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

    if not args.dry_run:
        scope = stage_discover_brands(idea, scope, pool, wd, args.dry_run)

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
    data["quality"] = compute_quality(data)
    for w in data["quality"]["warnings"]:
        print(f"    ⚠ 数据质量:{w}", file=sys.stderr)
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
