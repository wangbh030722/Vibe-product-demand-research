#!/usr/bin/env python3
"""
collect_hn.py — fetch Hacker News stories + comments matching a query.

Uses the public Algolia HN search API (no auth, no rate limit). Output: JSONL.

Usage:
    python3 collect_hn.py --query "smart glasses" "humane ai pin" \\
        --tags story --hits 30 --out evidence/hn.jsonl
"""
import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

UA = "Vibe-Demand-Research/0.1"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def search(query: str, tags: str = "story", hits: int = 30):
    qs = urllib.parse.urlencode({
        "query": query,
        "tags": tags,
        "hitsPerPage": hits,
    })
    url = f"https://hn.algolia.com/api/v1/search?{qs}"
    sys.stderr.write(f"[hn] GET {url}\n")
    data = fetch(url)
    for h in data.get("hits", []):
        text = (h.get("story_text") or h.get("comment_text") or "").strip()
        title = h.get("title") or h.get("story_title") or ""
        if not (title or text):
            continue
        yield {
            "source": "hacker_news",
            "source_type": "comment" if tags == "comment" else "story",
            "query": query,
            "id": h.get("objectID"),
            "url": h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}",
            "title": title,
            "text": text,
            "author": h.get("author"),
            "created_utc": h.get("created_at_i"),
            "score": h.get("points"),
            "num_comments": h.get("num_comments"),
            "engagement": {"points": h.get("points"), "comments": h.get("num_comments")},
        }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", nargs="+", required=True)
    ap.add_argument("--tags", default="story", help="story | comment | story,comment")
    ap.add_argument("--hits", type=int, default=30)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    n = 0
    with out_path.open("w", encoding="utf-8") as f:
        for q in args.query:
            try:
                for rec in search(q, args.tags, args.hits):
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    n += 1
            except Exception as e:
                sys.stderr.write(f"[hn] query {q!r} failed: {e}\n")
            time.sleep(0.5)

    sys.stderr.write(f"[hn] done. records={n} -> {out_path}\n")


if __name__ == "__main__":
    main()
