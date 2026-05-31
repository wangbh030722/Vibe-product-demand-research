"""Mode detection: existing / non-stock / hybrid.

Uses a lightweight LLM call (if available) to suggest subreddits + HN queries,
then does a cheap signal scan to apply thresholds from evidence-rules.md.

When LLM is unavailable, falls back to heuristic keyword extraction from the idea.
"""
from __future__ import annotations

import re

from . import llm
from .collect import collect_hn


def suggest_queries(idea: str, locale: str) -> dict:
    """Return suggested subreddits, HN queries, and locale-aware platforms."""
    if not llm.available():
        return _fallback_queries(idea, locale)
    out = llm.call(
        system=(
            "You suggest data-collection targets for product-demand research. "
            "Return JSON only."
        ),
        prompt=f"""Product idea: {idea!r}
Target market: {locale}

Output JSON with these fields:
  "subreddits": 3-6 specific subreddit names (no /r/ prefix). Prefer product-specific subs over generic. Include some adjacent failure-case subs.
  "hn_queries": 3-5 short search queries for Hacker News that would surface real user discussion.
  "marketplace": one of "amazon" | "jd" | "rakuten" | "none" depending on target market.
  "is_existing_market_guess": true/false — your prior on whether this product category already exists at retail.
  "notes": one-line rationale.

Return JSON only, no prose.""",
        max_tokens=600,
        expect_json=True,
    )
    if out.get("json"):
        out["json"]["via"] = "llm"
        return out["json"]
    # LLM call failed → fallback
    return _fallback_queries(idea, locale, via="fallback-after-llm-fail")


def _fallback_queries(idea: str, locale: str, via: str = "fallback") -> dict:
    """Sane defaults when no LLM is available.

    HN strategy: full-idea query AND 2-3 bigrams to maximize hit chances.
    Algolia's full-text search requires every token to appear, so long queries
    return 0; bigrams are much more useful.

    Reddit strategy: empty by default. Generic popular subs (r/gadgets,
    r/technology) are heavily rate-limited and 403 from anonymous fetches.
    Without an LLM to suggest specific niche subs, Reddit collection is
    skipped — the agent reports "Reddit skipped (no LLM)" honestly.
    """
    # Extract bigrams from words ≥3 chars; HN Algolia ANDs all terms so we keep them short.
    words = re.findall(r"[A-Za-z][A-Za-z0-9\-]{2,}", idea)
    bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)]
    # Pick bigrams that look "search-friendly": both words ≥4 chars AND not generic
    stop = {"with", "from", "have", "this", "that", "your", "into", "what", "when", "where"}
    good_bigrams = [
        bg for bg in bigrams
        if all(len(w) >= 4 and w.lower() not in stop for w in bg.split())
    ]
    hn_queries = [idea.strip()] + good_bigrams[:3]
    # Dedupe preserving order
    seen, deduped = set(), []
    for q in hn_queries:
        if q.lower() not in seen:
            seen.add(q.lower())
            deduped.append(q)
    return {
        "subreddits": [],  # don't waste time on generic subs that 403
        "hn_queries": deduped or [idea.strip()],
        "marketplace": "amazon" if locale.upper() == "US" else ("jd" if locale.upper() == "CN" else "none"),
        "is_existing_market_guess": False,
        "via": via,
        "fallback_note": "no LLM → Reddit skipped; HN queries built from bigrams. Set ANTHROPIC_API_KEY for targeted subreddit/community discovery.",
    }


def quick_signal_scan(idea: str, hn_queries: list[str], tmp_path: str = "evidence/.detect_hn.jsonl") -> dict:
    """Cheap HN-only scan to get a hit count quickly. Reddit scan is too unreliable
    to use in the detection phase — we just use HN for the routing decision."""
    res = collect_hn(hn_queries[:3], tags="story", hits=15, out_path=tmp_path)
    return {"hn_hits": res["records"]}


def decide(idea: str, locale: str, mode_override: str | None = None) -> dict:
    """Run the full detection sequence and return a decision dict."""
    if mode_override in ("existing", "non_stock", "hybrid"):
        return {
            "mode": mode_override, "via": "user-override",
            "queries": suggest_queries(idea, locale),
        }

    suggested = suggest_queries(idea, locale)
    scan = quick_signal_scan(idea, suggested.get("hn_queries", [idea]))
    existing_guess = bool(suggested.get("is_existing_market_guess"))
    hn_hits = scan["hn_hits"]

    # Decision rule:
    #   high HN hits + existing-guess → hybrid
    #   high HN hits + non-existing-guess → non_stock (with community evidence)
    #   low HN hits + existing-guess → existing (must rely on marketplace)
    #   low HN hits + non-existing-guess → non_stock (limited community evidence)
    if hn_hits >= 8 and existing_guess:
        mode = "hybrid"
    elif hn_hits >= 8 and not existing_guess:
        mode = "non_stock"
    elif hn_hits < 8 and existing_guess:
        mode = "existing"
    else:
        mode = "non_stock"

    return {
        "mode": mode,
        "via": "auto",
        "rationale": f"HN hits={hn_hits}, existing_guess={existing_guess}",
        "queries": suggested,
        "signal_scan": scan,
    }
