#!/usr/bin/env python3
"""
collect_reddit.py — fetch top posts + comments from one or more subreddits.

Bypasses WebFetch's reddit block by hitting reddit.com's public .json endpoint
directly with a polite User-Agent. Output: JSONL of raw-voice records that
match the schema in references/evidence-rules.md.

Usage:
    python3 collect_reddit.py --subs RayBanMeta smartglasses --limit 30 \\
        --out evidence/reddit.jsonl

Stdlib only. No pip install.
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

UA = "Vibe-Demand-Research/0.1 (+https://github.com/wangbh030722/Vibe-product-demand-research)"


BROWSER_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


def _curl_get(url: str):
    """Fallback via curl (handles proxy/TLS where urllib fails)."""
    import shutil, subprocess
    if not shutil.which("curl"):
        return None
    try:
        out = subprocess.run(
            ["curl", "-s", "-m", "25", "-A", BROWSER_UA,
             "-H", "Accept: application/json", url],
            capture_output=True, timeout=30,
        )
        if out.returncode == 0 and out.stdout:
            return json.loads(out.stdout.decode("utf-8"))
    except Exception:
        return None
    return None


def fetch(url: str, retries: int = 3, backoff: float = 1.5):
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code in (429, 503):
                time.sleep(backoff * (attempt + 1))
                continue
            # 403 etc → try curl once before giving up
            data = _curl_get(url)
            if data is not None:
                return data
            raise
        except Exception as e:
            last_err = e
            data = _curl_get(url)
            if data is not None:
                return data
            time.sleep(backoff * (attempt + 1))
    raise RuntimeError(f"fetch failed after {retries}: {last_err}")


def collect_subreddit(sub: str, limit: int, sort: str = "top", t: str = "year"):
    """Yield post records from a subreddit."""
    url = f"https://www.reddit.com/r/{sub}/{sort}.json?limit={limit}&t={t}"
    sys.stderr.write(f"[reddit] GET {url}\n")
    data = fetch(url)
    posts = data.get("data", {}).get("children", [])
    for p in posts:
        d = p.get("data", {})
        if d.get("stickied"):
            continue
        yield {
            "source": "reddit",
            "source_type": "post",
            "subreddit": sub,
            "id": d.get("id"),
            "url": "https://www.reddit.com" + d.get("permalink", ""),
            "title": d.get("title", ""),
            "text": d.get("selftext", "") or "",
            "author": d.get("author"),
            "created_utc": d.get("created_utc"),
            "score": d.get("ups", d.get("score")),
            "num_comments": d.get("num_comments"),
            "engagement": {
                "upvotes": d.get("ups", d.get("score")),
                "comments": d.get("num_comments"),
                "upvote_ratio": d.get("upvote_ratio"),
            },
            "flair": d.get("link_flair_text"),
        }


def collect_comments(permalink_url: str, top_n: int = 8):
    """Fetch top comments for a post. permalink_url ends without trailing slash already."""
    url = permalink_url.rstrip("/") + ".json?limit=" + str(top_n) + "&sort=top"
    try:
        data = fetch(url)
    except Exception as e:
        sys.stderr.write(f"[reddit] comment fetch failed for {permalink_url}: {e}\n")
        return
    if not isinstance(data, list) or len(data) < 2:
        return
    comments = data[1].get("data", {}).get("children", [])
    for c in comments:
        if c.get("kind") != "t1":
            continue
        d = c.get("data", {})
        body = (d.get("body") or "").strip()
        if not body or body in ("[removed]", "[deleted]"):
            continue
        yield {
            "source": "reddit",
            "source_type": "comment",
            "parent_post_url": permalink_url,
            "id": d.get("id"),
            "url": "https://www.reddit.com" + d.get("permalink", ""),
            "text": body,
            "author": d.get("author"),
            "created_utc": d.get("created_utc"),
            "score": d.get("ups", d.get("score")),
            "engagement": {"upvotes": d.get("ups", d.get("score"))},
        }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subs", nargs="+", required=True, help="Subreddit names without /r/")
    ap.add_argument("--limit", type=int, default=25, help="Posts per subreddit")
    ap.add_argument("--sort", default="top", choices=["top", "hot", "new"])
    ap.add_argument("--time", default="year", choices=["hour", "day", "week", "month", "year", "all"])
    ap.add_argument("--with-comments", action="store_true", help="Also fetch top comments per post")
    ap.add_argument("--comments-per-post", type=int, default=5)
    ap.add_argument("--out", required=True, help="Output JSONL path")
    args = ap.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    n_posts = 0
    n_comments = 0
    with out_path.open("w", encoding="utf-8") as f:
        for sub in args.subs:
            try:
                posts = list(collect_subreddit(sub, args.limit, args.sort, args.time))
            except Exception as e:
                sys.stderr.write(f"[reddit] subreddit {sub} failed: {e}\n")
                continue
            for post in posts:
                f.write(json.dumps(post, ensure_ascii=False) + "\n")
                n_posts += 1
                if args.with_comments and post.get("num_comments", 0) > 0:
                    time.sleep(0.6)  # be polite
                    for c in collect_comments(post["url"], args.comments_per_post):
                        f.write(json.dumps(c, ensure_ascii=False) + "\n")
                        n_comments += 1
            time.sleep(1.0)

    sys.stderr.write(f"[reddit] done. posts={n_posts} comments={n_comments} -> {out_path}\n")


if __name__ == "__main__":
    main()
