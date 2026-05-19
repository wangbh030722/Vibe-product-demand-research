#!/usr/bin/env python3
"""
clean.py — dedupe + categorize raw JSONL into an evidence pack.

Input: one or more JSONL files produced by collect_*.py.
Output:
  - cleaned.jsonl    — deduped, filtered records
  - summary.json     — counts per category, top voices, top counter-evidence

Categorization is keyword-based (lightweight; see CATEGORY_KEYS). The agent does
the final interpretation; this just sorts buckets.

Usage:
    python3 clean.py --in evidence/reddit.jsonl evidence/hn.jsonl \\
        --out-dir evidence/pack --min-score 5
"""
import argparse
import json
import re
import sys
from collections import defaultdict, Counter
from hashlib import sha1
from pathlib import Path

CATEGORY_KEYS = {
    "workaround": [
        r"\bworkaround\b", r"\binstead i\b", r"\bi just\b", r"\bi use\b", r"\bi end up\b",
        r"\bmanually\b", r"\bsimpl(y|er) (use|do)\b", r"\bi switched to\b", r"\bduct tape\b",
    ],
    "payment_signal": [
        r"\bpre[- ]?order\b", r"\bbacked\b", r"\bkickstarter\b", r"\bindiegogo\b",
        r"\bwaitlist\b", r"\bsubscription\b", r"\b\$\d+", r"\bbought\b", r"\bordered\b",
    ],
    "counter_evidence": [
        r"\brefund(ed|ing)?\b", r"\breturn(ed|ing)?\b", r"\bregret\b", r"\bwaste of money\b",
        r"\bdiscontinued\b", r"\bdead\b", r"\bfailed\b", r"\babandoned\b", r"\bgave up\b",
        r"\bdoesn'?t (work|do)\b", r"\bnot worth\b", r"\bsold (it|mine)\b",
    ],
    "pain": [
        r"\bbattery\b", r"\bovrheat", r"\boverheat\b", r"\bcrash(es|ed|ing)?\b",
        r"\bbug\b", r"\blag(s|gy)?\b", r"\bprivacy\b", r"\brecording\b",
        r"\bcreepy\b", r"\bcamera\b", r"\bbroken?\b", r"\buncomfortab", r"\bhurts?\b",
        r"\bannoying\b", r"\bdisappoint", r"\bissue\b", r"\bproblem\b",
    ],
    "positive": [
        r"\blove (it|mine|these)\b", r"\bawesome\b", r"\bgame[- ]changer\b",
        r"\bworth (it|every)\b", r"\bamazing\b", r"\bsurprisingly good\b",
        r"\bcouldn'?t (live|go) without\b", r"\bgreat for\b",
    ],
}

COMPILED = {k: [re.compile(p, re.I) for p in v] for k, v in CATEGORY_KEYS.items()}


def text_hash(t: str) -> str:
    return sha1(re.sub(r"\s+", " ", t.strip().lower()).encode("utf-8")).hexdigest()[:16]


def categorize(text: str):
    cats = set()
    for cat, regs in COMPILED.items():
        for r in regs:
            if r.search(text):
                cats.add(cat)
                break
    return sorted(cats)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inputs", nargs="+", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--min-score", type=int, default=2, help="Drop posts/comments below this score")
    ap.add_argument("--min-text-len", type=int, default=40, help="Drop very short text")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cleaned_path = out_dir / "cleaned.jsonl"
    summary_path = out_dir / "summary.json"

    seen = set()
    by_cat = defaultdict(list)
    source_counts = Counter()
    raw_voice_count = 0

    with cleaned_path.open("w", encoding="utf-8") as out:
        for input_path in args.inputs:
            p = Path(input_path)
            if not p.exists():
                sys.stderr.write(f"[clean] skip missing: {p}\n")
                continue
            with p.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    text = (rec.get("title", "") + "\n" + rec.get("text", "")).strip()
                    if len(text) < args.min_text_len:
                        continue
                    score = rec.get("score") or 0
                    if score < args.min_score:
                        continue
                    h = text_hash(text)
                    if h in seen:
                        continue
                    seen.add(h)
                    rec["categories"] = categorize(text)
                    rec["text_hash"] = h
                    out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    source_counts[rec.get("source", "?")] += 1
                    raw_voice_count += 1
                    for c in rec["categories"]:
                        by_cat[c].append({
                            "url": rec.get("url"),
                            "source": rec.get("source"),
                            "score": rec.get("score"),
                            "text_excerpt": (rec.get("text") or rec.get("title") or "")[:280],
                            "author": rec.get("author"),
                        })

    # Top-N per category by score
    top_per_cat = {}
    for c, rows in by_cat.items():
        rows.sort(key=lambda r: r.get("score") or 0, reverse=True)
        top_per_cat[c] = rows[:8]

    summary = {
        "raw_voice_count_total": raw_voice_count,
        "by_source": source_counts,
        "by_category_counts": {c: len(v) for c, v in by_cat.items()},
        "top_per_category": top_per_cat,
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    sys.stderr.write(f"[clean] done. raw_voice={raw_voice_count} -> {cleaned_path}, {summary_path}\n")


if __name__ == "__main__":
    main()
