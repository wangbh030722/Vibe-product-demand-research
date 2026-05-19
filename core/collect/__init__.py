"""Raw-VOC collectors. Public functions wrap the CLI scripts so app.py can
call them in-process without spawning subprocesses.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Iterable

# Re-export the script modules so they can also be invoked from the CLI.
from . import reddit as _reddit  # noqa: F401
from . import hn as _hn          # noqa: F401
from . import clean as _clean    # noqa: F401


def collect_reddit(subs: list[str], limit: int = 30, with_comments: bool = True,
                   comments_per_post: int = 5, out_path: str | Path = "evidence/reddit.jsonl",
                   sort: str = "top", time: str = "year") -> dict:
    """Run the reddit collector in-process and return a counts summary.

    Failures per subreddit are logged but do not raise. Caller inspects the
    returned dict to surface honest status.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n_posts = 0
    n_comments = 0
    failed_subs: list[tuple[str, str]] = []
    with out_path.open("w", encoding="utf-8") as f:
        for sub in subs:
            try:
                posts = list(_reddit.collect_subreddit(sub, limit, sort, time))
            except Exception as e:
                failed_subs.append((sub, str(e)))
                sys.stderr.write(f"[reddit] subreddit {sub} failed: {e}\n")
                continue
            for post in posts:
                f.write(json.dumps(post, ensure_ascii=False) + "\n")
                n_posts += 1
                if with_comments and (post.get("num_comments") or 0) > 0:
                    try:
                        for c in _reddit.collect_comments(post["url"], comments_per_post):
                            f.write(json.dumps(c, ensure_ascii=False) + "\n")
                            n_comments += 1
                    except Exception as e:
                        sys.stderr.write(f"[reddit] comments {post['url']} failed: {e}\n")
    return {
        "posts": n_posts,
        "comments": n_comments,
        "failed_subs": failed_subs,
        "out_path": str(out_path),
    }


def collect_hn(queries: list[str], tags: str = "story", hits: int = 30,
               out_path: str | Path = "evidence/hn.jsonl") -> dict:
    """Run HN collector in-process."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with out_path.open("w", encoding="utf-8") as f:
        for q in queries:
            try:
                for rec in _hn.search(q, tags, hits):
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    n += 1
            except Exception as e:
                sys.stderr.write(f"[hn] query {q!r} failed: {e}\n")
    return {"records": n, "out_path": str(out_path)}


def clean(inputs: Iterable[str | Path], out_dir: str | Path = "evidence/pack",
          min_score: int = 3, min_text_len: int = 40) -> dict:
    """Run cleaner. Returns the summary.json contents."""
    from io import StringIO
    import re
    from collections import defaultdict, Counter
    from hashlib import sha1

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cleaned_path = out_dir / "cleaned.jsonl"
    summary_path = out_dir / "summary.json"

    seen = set()
    by_cat = defaultdict(list)
    source_counts = Counter()
    raw_voice_count = 0

    with cleaned_path.open("w", encoding="utf-8") as out:
        for input_path in inputs:
            p = Path(input_path)
            if not p.exists():
                continue
            with p.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    text = (rec.get("title", "") + "\n" + rec.get("text", "")).strip()
                    if len(text) < min_text_len:
                        continue
                    score = rec.get("score") or 0
                    if score < min_score:
                        continue
                    h = _clean.text_hash(text)
                    if h in seen:
                        continue
                    seen.add(h)
                    rec["categories"] = _clean.categorize(text)
                    rec["text_hash"] = h
                    out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    source_counts[rec.get("source", "?")] += 1
                    raw_voice_count += 1
                    for c in rec["categories"]:
                        by_cat[c].append({
                            "url": rec.get("url"),
                            "source": rec.get("source"),
                            "score": rec.get("score"),
                            "text_excerpt": (rec.get("text") or rec.get("title") or "")[:400],
                            "author": rec.get("author"),
                        })

    top_per_cat = {}
    for c, rows in by_cat.items():
        rows.sort(key=lambda r: r.get("score") or 0, reverse=True)
        top_per_cat[c] = rows[:10]

    summary = {
        "raw_voice_count_total": raw_voice_count,
        "by_source": dict(source_counts),
        "by_category_counts": {c: len(v) for c, v in by_cat.items()},
        "top_per_category": top_per_cat,
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary
