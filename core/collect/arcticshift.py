#!/usr/bin/env python3
"""
arcticshift.py — real Reddit posts + comments via the Arctic Shift archive.

Arctic Shift (arctic-shift.photon-reddit.com) is a Pushshift/pullpush-style Reddit
archive on DIFFERENT infrastructure, so it works when pullpush is rate-limiting or
down, and when reddit.com 403s the proxy IP. No key, no OAuth.

Unlike pullpush's noisy global full-text search, Arctic Shift is strongest at
SUBREDDIT-scoped queries (subreddit listings + in-sub title filters) — which is
also MORE relevant for category research (we already know the product subreddits).

    python3 core/collect/arcticshift.py --subs espresso Coffee CoffeeGear \\
        --queries "portable espresso" "travel espresso" --out evidence/as.jsonl

Output JSONL matches the other collectors:
  { source:"reddit", source_type, subreddit, title, text, url, score, created_utc }
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

POSTS = "https://arctic-shift.photon-reddit.com/api/posts/search"
COMMENTS = "https://arctic-shift.photon-reddit.com/api/comments/search"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"


def _get(url):
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
        time.sleep(1.2 * (attempt + 1))
    return {}


def _url(d):
    pl = d.get("permalink") or ""
    if pl.startswith("/"):
        return "https://www.reddit.com" + pl
    return d.get("url") or ("https://www.reddit.com/r/" + str(d.get("subreddit", "")))


def search(kind, subreddit=None, title=None, size=100, before=None):
    params = {"limit": size, "sort": "desc"}
    if subreddit:
        params["subreddit"] = subreddit
    if title:
        params["title"] = title
    if before:
        params["before"] = int(before)
    base = POSTS if kind == "post" else COMMENTS
    url = f"{base}?{urllib.parse.urlencode(params)}"
    data = _get(url).get("data") or []
    out = []
    for d in data:
        if kind == "post":
            t = (d.get("title") or "").strip()
            if not t:
                continue
            out.append({
                "source": "reddit", "source_type": "post",
                "subreddit": d.get("subreddit", ""), "title": t,
                "text": (d.get("selftext") or "")[:400], "url": _url(d),
                "score": d.get("score") or 0, "created_utc": d.get("created_utc"),
            })
        else:
            body = (d.get("body") or "").strip()
            if not body or body in ("[removed]", "[deleted]"):
                continue
            out.append({
                "source": "reddit", "source_type": "comment",
                "subreddit": d.get("subreddit", ""), "title": body[:90],
                "text": body[:400], "url": _url(d),
                "score": d.get("score") or 0, "created_utc": d.get("created_utc"),
            })
    return out


def paginate(kind, subreddit=None, title=None, size=100, pages=1):
    """Walk back in time (sort=desc + before) to pull more than one page."""
    acc, before = [], None
    for _ in range(pages):
        batch = search(kind, subreddit, title, size, before)
        if not batch:
            break
        acc += batch
        cu = [b.get("created_utc") for b in batch if b.get("created_utc")]
        if not cu:
            break
        nb = min(cu)
        if before is not None and nb >= before:
            break
        before = nb - 1
        if len(batch) < size:
            break
    return acc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subs", nargs="*", default=[])
    ap.add_argument("--queries", nargs="*", default=[])
    ap.add_argument("--size", type=int, default=100)
    ap.add_argument("--pages", type=int, default=3)
    ap.add_argument("--out", required=True)
    ap.add_argument("--target", type=int, default=0)
    args = ap.parse_args()

    from concurrent.futures import ThreadPoolExecutor
    # Build a precise keyword set from the queries (the product/intent words),
    # dropping generic stopwords so the in-sub title filter stays on-topic.
    STOP = {"review","reviews","best","good","under","vs","the","for","and","with",
            "coffee","machine","maker","cheap","affordable","office"}
    kws = []
    for q in (args.queries or []):
        for w in str(q).replace("-", " ").split():
            w = w.strip().lower()
            if len(w) >= 4 and w not in STOP:
                kws.append(w)
    kws = list(dict.fromkeys(kws))[:8] or ["portable"]

    tasks = []
    # PRIMARY: precise in-sub title filters (e.g. r/Coffee title=portable) — these
    # surface the genuinely on-topic threads, not the whole subreddit.
    for sub in (args.subs or [])[:12]:
        for w in kws[:5]:
            tasks.append(("post", sub, w, 2))
    # SECONDARY: recent in-sub comments (product mentions in discussion) + a little
    # broad post listing for context.
    for sub in (args.subs or [])[:10]:
        tasks.append(("comment", sub, None, 2))
        tasks.append(("post", sub, None, 1))

    def run(t):
        kind, sub, title, pages = t
        sys.stderr.write(f"[arcticshift] {kind} r/{sub} title={title}\n")
        return paginate(kind, sub, title, args.size, pages)

    seen, n = set(), 0
    with ThreadPoolExecutor(max_workers=min(6, len(tasks) or 1)) as ex, \
         open(args.out, "w", encoding="utf-8") as f:
        for batch in ex.map(run, tasks):
            for rec in batch:
                u = rec.get("url")
                if not u or u in seen:
                    continue
                seen.add(u)
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                n += 1
                if n % 50 == 0:
                    sys.stderr.write(f"[arcticshift] {n} unique so far…\n")
                    sys.stderr.flush()
            if args.target and n >= args.target:
                break
    sys.stderr.write(f"[arcticshift] done. {n} unique records -> {args.out}\n")


if __name__ == "__main__":
    main()
