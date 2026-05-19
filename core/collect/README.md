# Crawler Pipeline (V0)

Minimal raw-VOC collectors that bypass WebSearch's editorial bias and WebFetch's anti-bot blocks. Output JSONL records matching the schema in [`../../skills/method-two-crawler-pipeline/SKILL.md`](../../skills/method-two-crawler-pipeline/SKILL.md).

Python 3.9+, stdlib only. No `pip install` required.

## What works today

| Collector | Status | Notes |
|---|---|---|
| `collect_reddit.py` | ✅ Partial | Hits `reddit.com/r/<sub>/.json` with a polite UA. Some subs return 403 (anti-bot); succeeds on most. |
| `collect_hn.py` | ✅ Reliable | Uses HN's free Algolia search API. No auth, no rate limit observed. |
| `clean.py` | ✅ | Dedupes by normalized-text hash; categorizes by keyword regex into pain / positive / workaround / payment / counter_evidence. |
| Marketplace (Amazon / Best Buy / 京东 reviews) | ❌ Not yet | Heavy anti-bot. Needs paid VOC API, headless browser with rotating proxies, or manual CSV import via `collect_csv.py` (TODO). |
| YouTube comments | ❌ Not yet | Needs YouTube Data API key. |

## Usage

```bash
# 1. Reddit — fetch top posts + top comments
python3 collect_reddit.py \
    --subs RayBanMeta smartglasses Humane \
    --limit 30 --sort top --time year \
    --with-comments --comments-per-post 5 \
    --out evidence/reddit.jsonl

# 2. Hacker News — search stories + comments
python3 collect_hn.py \
    --query "smart glasses" "humane ai pin" "ray-ban meta" \
    --tags story --hits 30 \
    --out evidence/hn_stories.jsonl
python3 collect_hn.py \
    --query "smart glasses" "ray-ban meta" \
    --tags comment --hits 50 \
    --out evidence/hn_comments.jsonl

# 3. Clean + categorize
python3 clean.py \
    --in evidence/reddit.jsonl evidence/hn_stories.jsonl evidence/hn_comments.jsonl \
    --out-dir evidence/pack \
    --min-score 3
```

Output: `evidence/pack/cleaned.jsonl` (deduped raw records with category tags) and `evidence/pack/summary.json` (counts + top-N per category).

The agent then reads `summary.json` as the evidence pack, picks 3–5 verbatim quotes per insight, and produces the final report. Do not feed raw `cleaned.jsonl` into the agent's context directly — it's too noisy.

## Empirical performance (AI smart glasses, 2026-05)

| Layer | Planned | Actual |
|---|---|---|
| Reddit posts | ≥ 30 across 4 subs | 30 from r/RayBanMeta only; r/smartglasses, r/Humane, r/HumaneAI returned 403 |
| Reddit comments | ≥ 100 | 79 (some comment-page fetches also 403/SSL errors) |
| HN records | ≥ 200 | 270 (120 stories + 150 comments, 7 queries) |
| After dedupe + min-score=3 | — | 172 raw voices kept |
| Time | ≤ 5 min | ~2 min wall clock |

This is enough to give `partially_supported` on the community side of a hybrid route. **Marketplace VOC is the remaining gap** — without it, no hybrid route can ever reach `supported` status under the current evidence-rules gating.

## Failure modes & honest disclosure

- **Reddit 403**: some subs are blocked from anonymous fetches. The collector logs the failure and continues. The agent must surface the failure in the Method note, not hide it.
- **SSL EOF errors**: intermittent on Reddit comment pages. Retries are built in (3 with backoff). Final failure → skipped record, logged.
- **Keyword categorization is lightweight**: the cleaner uses regex buckets, not LLM classification. False positives are expected. The agent should re-read the verbatim quote, not trust the bucket label.
- **Self-selection bias on Reddit**: r/<product> subs are buyer-skewed. To find churn voices, also collect from general subs (r/gadgets, r/technology, r/wellthatsucks) — `--subs` accepts multiple values.

## Extending

Adding a new collector means:

1. Write `collect_<source>.py` that emits the shared JSONL schema:
   ```json
   {"source": "<source>", "source_type": "post|comment|review",
    "url": "<permalink>", "title": "...", "text": "...",
    "author": "...", "created_utc": <unix>, "score": <int>,
    "engagement": {...}}
   ```
2. Make sure every record has a working permalink (no search-result URLs).
3. The cleaner picks up new sources automatically by reading any JSONL passed via `--in`.

Priority targets for V1:

- `collect_amazon.py` — even a manual-CSV import variant (`--csv reviews.csv`) closes the marketplace gap.
- `collect_xhs.py` / `collect_smzdm.py` for CN target markets.
- `collect_youtube_comments.py` once API key handling is added.
