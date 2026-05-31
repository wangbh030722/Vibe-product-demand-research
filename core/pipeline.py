"""End-to-end pipeline. The HTTP server hands a job in via run(); the pipeline
emits SSE events through the `emit` callback as it progresses.
"""
from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Callable

from . import detect_mode, voc_summarize, non_stock, verdict
from .collect import collect_reddit, collect_hn, clean


def run(idea: str, locale: str, mode_override: str | None,
        emit: Callable[[str, dict], None]) -> dict:
    job_dir = Path("evidence") / f"run-{int(time.time())}-{uuid.uuid4().hex[:6]}"
    job_dir.mkdir(parents=True, exist_ok=True)

    # ---- 1. Mode detection ----
    emit("phase", {"phase": "detect", "status": "running"})
    t0 = time.time()
    decision = detect_mode.decide(idea, locale, mode_override)
    emit("phase", {"phase": "detect", "status": "done", "elapsed": time.time() - t0,
                   "decision": decision})

    queries = decision.get("queries", {})
    mode = decision["mode"]

    # ---- 2. Collect ----
    reddit_path = str(job_dir / "reddit.jsonl")
    hn_story_path = str(job_dir / "hn_stories.jsonl")
    hn_comment_path = str(job_dir / "hn_comments.jsonl")
    inputs = []

    if queries.get("subreddits"):
        emit("phase", {"phase": "collect_reddit", "status": "running",
                       "subs": queries["subreddits"]})
        t0 = time.time()
        r = collect_reddit(queries["subreddits"], limit=25,
                           with_comments=True, comments_per_post=4,
                           out_path=reddit_path)
        inputs.append(reddit_path)
        emit("phase", {"phase": "collect_reddit", "status": "done",
                       "elapsed": time.time() - t0,
                       "posts": r["posts"], "comments": r["comments"],
                       "failed_subs": [s[0] for s in r["failed_subs"]]})

    if queries.get("hn_queries"):
        emit("phase", {"phase": "collect_hn", "status": "running",
                       "queries": queries["hn_queries"]})
        t0 = time.time()
        s = collect_hn(queries["hn_queries"], tags="story", hits=25, out_path=hn_story_path)
        c = collect_hn(queries["hn_queries"], tags="comment", hits=40, out_path=hn_comment_path)
        inputs.append(hn_story_path)
        inputs.append(hn_comment_path)
        emit("phase", {"phase": "collect_hn", "status": "done",
                       "elapsed": time.time() - t0,
                       "stories": s["records"], "comments": c["records"]})

    # ---- 3. Clean / dedupe / categorize ----
    emit("phase", {"phase": "clean", "status": "running"})
    t0 = time.time()
    pack = clean(inputs, out_dir=str(job_dir / "pack"), min_score=2)
    emit("phase", {"phase": "clean", "status": "done", "elapsed": time.time() - t0,
                   "raw_voice_count": pack["raw_voice_count_total"],
                   "by_source": pack["by_source"],
                   "by_category": pack["by_category_counts"]})

    # ---- 4. Analyze ----
    voc = None
    framework = None
    counter = None
    qualitative = None

    if mode in ("existing", "hybrid"):
        emit("phase", {"phase": "analyze_voc", "status": "running"})
        t0 = time.time()
        voc = voc_summarize.summarize(idea, pack)
        emit("phase", {"phase": "analyze_voc", "status": "done",
                       "elapsed": time.time() - t0,
                       "via": voc.get("via")})

    if mode in ("non_stock", "hybrid"):
        emit("phase", {"phase": "framework_score", "status": "running"})
        t0 = time.time()
        framework = non_stock.framework_score(idea, locale, pack)
        emit("phase", {"phase": "framework_score", "status": "done",
                       "elapsed": time.time() - t0, "via": framework.get("via")})

        emit("phase", {"phase": "counter_checklist", "status": "running"})
        t0 = time.time()
        counter = non_stock.counter_checklist(idea, locale, pack)
        emit("phase", {"phase": "counter_checklist", "status": "done",
                       "elapsed": time.time() - t0, "via": counter.get("via")})

        emit("phase", {"phase": "qualitative_review", "status": "running"})
        t0 = time.time()
        qualitative = non_stock.qualitative_review(idea, locale, pack)
        emit("phase", {"phase": "qualitative_review", "status": "done",
                       "elapsed": time.time() - t0, "via": qualitative.get("via")})

    # ---- 5. Verdict ----
    emit("phase", {"phase": "verdict", "status": "running"})
    final = verdict.compose(idea, locale, mode, pack, voc, framework, counter, qualitative)
    emit("phase", {"phase": "verdict", "status": "done"})

    return {
        "idea": idea,
        "locale": locale,
        "mode": mode,
        "decision": decision,
        "evidence_pack": pack,
        "voc": voc,
        "framework": framework,
        "counter": counter,
        "qualitative": qualitative,
        "verdict": final,
        "job_dir": str(job_dir),
    }
