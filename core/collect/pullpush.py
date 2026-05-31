#!/usr/bin/env python3
"""
collect_pullpush.py — real Reddit posts + comments via pullpush.io.

pullpush.io is a Pushshift successor (Reddit archive). It lives on a DIFFERENT
domain (api.pullpush.io), so it is NOT subject to the anti-scraping IP bans on
www.reddit.com — works even when reddit.com 403s your proxy exit IP. No key,
no OAuth.

    python3 core/collect/pullpush.py --queries "automatic pet feeder" \\
        --subs dogs cats homeautomation --out evidence/pullpush.jsonl

Output JSONL matches the other collectors:
  { source:"reddit", title, text, url, score, subreddit, source_type, created_utc }
Stdlib only; curl-first (proxy/TLS reliability).
"""
import argparse
import json
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request

BASE = "https://api.pullpush.io/reddit/search"
UA = "vibe-research/0.1"


def _get(url):
    # pullpush.io is a community service and gets slow/rate-limited under load.
    # Retry a few times with backoff before giving up, so a transient timeout
    # doesn't collapse the whole pool to a few records.
    have_curl = bool(shutil.which("curl"))
    for attempt in range(3):
        if have_curl:
            try:
                out = subprocess.run(["curl", "-s", "-m", "30", "-A", UA, url],
                                     capture_output=True, timeout=35)
                if out.returncode == 0 and out.stdout:
                    return json.loads(out.stdout.decode("utf-8", "replace"))
            except Exception:
                pass
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception:
            pass
        time.sleep(1.5 * (attempt + 1))   # backoff: 1.5s, 3s
    return {}


def _permalink(d):
    pl = d.get("permalink") or ""
    if pl.startswith("/"):
        return "https://www.reddit.com" + pl
    return d.get("full_link") or d.get("url") or ("https://www.reddit.com/r/" + str(d.get("subreddit", "")))


def search_submissions(query, subreddit=None, size=40, before=None):
    params = {"q": query, "size": size, "sort": "desc", "sort_type": "created_utc"}
    if subreddit:
        params["subreddit"] = subreddit
    if before:
        params["before"] = int(before)
    url = f"{BASE}/submission/?{urllib.parse.urlencode(params)}"
    sys.stderr.write(f"[pullpush] sub {subreddit or '*'} q={query!r}\n")
    try:
        data = _get(url).get("data", [])
    except Exception as e:
        sys.stderr.write(f"[pullpush] submission fail: {e}\n")
        return []
    out = []
    for d in data:
        title = (d.get("title") or "").strip()
        if not title:
            continue
        out.append({
            "source": "reddit", "source_type": "post",
            "subreddit": d.get("subreddit", ""),
            "title": title, "text": (d.get("selftext") or "")[:400],
            "url": _permalink(d), "score": d.get("score") or 0,
            "num_comments": d.get("num_comments"), "created_utc": d.get("created_utc"),
        })
    return out


def search_comments(query, subreddit=None, size=40, before=None):
    params = {"q": query, "size": size, "sort": "desc", "sort_type": "created_utc"}
    if subreddit:
        params["subreddit"] = subreddit
    if before:
        params["before"] = int(before)
    url = f"{BASE}/comment/?{urllib.parse.urlencode(params)}"
    sys.stderr.write(f"[pullpush] comment q={query!r}\n")
    try:
        data = _get(url).get("data", [])
    except Exception as e:
        sys.stderr.write(f"[pullpush] comment fail: {e}\n")
        return []
    out = []
    for d in data:
        body = (d.get("body") or "").strip()
        if not body or body in ("[removed]", "[deleted]"):
            continue
        out.append({
            "source": "reddit", "source_type": "comment",
            "subreddit": d.get("subreddit", ""),
            "title": body[:90], "text": body[:400],
            "url": _permalink(d), "score": d.get("score") or 0,
            "created_utc": d.get("created_utc"),
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--queries", nargs="+", required=True)
    ap.add_argument("--subs", nargs="*", default=[])
    ap.add_argument("--size", type=int, default=40)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sleep", type=float, default=0.6)
    ap.add_argument("--target", type=int, default=0,
                    help="stop early once this many unique records are written")
    args = ap.parse_args()

    # pullpush.io is slow per request (~20-30s) AND its global full-text search
    # is noisy. Improve precision by ALSO searching inside the product-relevant
    # subreddits. Fire everything CONCURRENTLY so total ≈ slowest request.
    # Fan out widely (many query × sub combos) so we can accumulate ~1000 unique
    # relevant records for the "999 real comments" base.
    from concurrent.futures import ThreadPoolExecutor
    tasks = []
    for q in args.queries[:8]:
        tasks.append(("comment", q, None))         # global comment search
        tasks.append(("submission", q, None))      # global submission search
    # sub-scoped searches (precise): each query × each sub, posts + comments.
    # Each task paginates back in time, so this fans out to thousands. Cover up
    # to 10 communities for breadth.
    for sub in (args.subs or [])[:10]:
        for q in args.queries[:2]:
            tasks.append(("submission", q, sub))
            tasks.append(("comment", q, sub))

    def run(t):
        # Paginate back through time (sort by created_utc desc + `before`) so each
        # query yields far more than one page — key to reaching ~999 unique.
        kind, q, sub = t
        fn = search_comments if kind == "comment" else search_submissions
        acc, before, PAGES = [], None, 6
        for _ in range(PAGES):
            batch = fn(q, sub, args.size, before)
            if not batch:
                break
            acc += batch
            cutoffs = [b.get("created_utc") for b in batch if b.get("created_utc")]
            if not cutoffs:
                break
            nb = min(cutoffs)
            if before is not None and nb >= before:
                break
            before = nb - 1
        return acc

    seen, n = set(), 0
    # Gentler concurrency: pullpush rate-limits bursts (429). Fewer workers +
    # the per-request retry/backoff in _get keeps the collection from collapsing.
    with ThreadPoolExecutor(max_workers=min(6, len(tasks) or 1)) as ex, \
         open(args.out, "w", encoding="utf-8") as f:
        for batch in ex.map(run, tasks):
            for rec in batch:
                if rec["url"] in seen:
                    continue
                seen.add(rec["url"])
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                n += 1
                if n % 25 == 0:
                    sys.stderr.write(f"[pullpush] {n} unique so far…\n")
                    sys.stderr.flush()
            if args.target and n >= args.target:
                break
    sys.stderr.write(f"[pullpush] done. {n} unique records -> {args.out}\n")


if __name__ == "__main__":
    main()
