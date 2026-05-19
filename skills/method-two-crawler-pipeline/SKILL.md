---
name: method-two-crawler-pipeline
description: Plan and use a method-two demand research pipeline that separates crawler scripts, source-specific collectors, local cleaning, evidence-pack generation, and final agent reporting. Use when the user wants a cheaper alternative to paid Amazon/VOC APIs, wants to test crawler-based product demand research, or wants to validate emerging demand using Reddit, YouTube, Product Hunt, crowdfunding, search signals, and lightweight Amazon product discovery without relying on expensive review APIs.
---

# Method Two Crawler Pipeline

## Position in the router

**This is a collection mode, not a market type.** It stacks on whichever main route (`existing`, `emerging`, `hybrid`) was selected by [`../vibe-product-demand-research/SKILL.md`](../vibe-product-demand-research/SKILL.md).

Triggers `collection_mode: crawler-pipeline` when any of these hold:

- The user explicitly says "no paid APIs", "cheap", "self-host", "free", or "budget".
- The target marketplace is blocked, rate-limited, or unavailable for the `target_market` (e.g. Amazon US access from a region without access; Amazon refuses scraping for the IP class).
- The user wants reproducible local re-runs against the same raw corpus.

The route still drives **which evidence layers** are required (VOC layers for existing, pain/workaround/payment for emerging, both + conflict resolution for hybrid). This skill only changes **how the evidence gets collected**.

Evidence integrity rules: [`../../references/evidence-rules.md`](../../references/evidence-rules.md).

## Purpose

Lower-cost architecture for evidence collection when paid review APIs are too expensive or unreliable.

The core flow:

```text
collector scripts -> raw JSONL -> cleaner/dedupe/ranker -> evidence pack -> agent report
```

The agent should not directly consume huge raw crawls. Scripts collect and normalize data first; the agent reads a compact evidence pack and applies the demand-research rules for the active route.

**Reference implementation: [`../../templates/crawler/`](../../templates/crawler/)**

Python stdlib collectors that bypass WebFetch's anti-bot blocks:

- `collect_reddit.py` — direct `reddit.com/r/<sub>/.json` with polite UA. Partial success (some subs 403).
- `collect_hn.py` — HN Algolia search API. Reliable.
- `clean.py` — dedupe + keyword categorization → `summary.json` evidence pack.

Marketplace collectors (Amazon/Best Buy/京东) are **not yet implemented** — see `templates/crawler/README.md` for honest status and extension priorities. Until marketplace VOC is available, no `hybrid` route can reach `status: supported` under the gating in `references/evidence-rules.md`. This is by design.

## Source Priority

Do not make Amazon reviews the V1 bottleneck.

Prioritize sources by feasibility and demand value:

| Source | V1 role | Why |
|---|---|---|
| Reddit | Primary demand signal | Complaints, workarounds, raw user language |
| YouTube comments | Primary demand signal | Product experience, long comments, creator-audience feedback |
| Product Hunt | Early-product signal | Launch feedback and alternatives |
| Kickstarter / Indiegogo | Payment signal | Backers, preorder behavior, campaign comments |
| App Store / Chrome Web Store | Product feedback signal | Reviews for software, apps, extensions, companion apps |
| Google/search/SEO pages | Discovery signal | Problem phrases, search intent, alternatives |
| Brand/independent pages | Product identity and pricing | Claims, price, waitlist, preorder |
| Amazon search/product pages | Lightweight competitor discovery | Titles, ASINs, prices, ratings, review counts |
| Amazon review pages | Optional/manual/paid later | Valuable but unstable and costly |

## Amazon Policy

Amazon is useful, but should be staged:

1. **V1: Amazon light collector**
   - Collect product URL, ASIN, title, price, rating, review count, brand/store link, visible claims.
   - Do not promise review text extraction.

2. **V1.5: Manual import**
   - Support user-pasted review text, CSV, copied page text, or third-party exports.
   - The system cleans and analyzes the imported evidence.

3. **V2: Paid or specialized source**
   - Consider paid review APIs only after the demand research product itself is validated.
   - Treat third-party data as sampled public-page collection, not official Amazon data.

## Collector Design

Each collector should output JSONL records with a shared minimum shape:

```json
{
  "source": "reddit",
  "source_type": "community_thread",
  "query": "smart ring sleep tracking",
  "url": "https://...",
  "title": "...",
  "text": "...",
  "author": "optional",
  "created_at": "optional",
  "engagement": {"upvotes": 12, "comments": 8},
  "product": "optional",
  "metadata": {}
}
```

Keep source-specific fields in `metadata`. Do not force every source into an Amazon review schema.

## Cleaning Layer

Before the agent sees the data:

- Remove duplicates by URL, normalized text hash, and repeated snippets.
- Drop very short, spammy, boilerplate, navigation, and SEO-filler content.
- Keep source URL, source type, timestamp when available, and raw text excerpt.
- Split records into evidence categories:
  - user pain
  - workaround
  - payment signal
  - search/discovery signal
  - product/competitor
  - positive review/voice
  - negative review/voice
- Prefer recent records when the user requests recent demand.
- Preserve original English voice separately from interpretation.

## Evidence Pack

The evidence pack is the only artifact the agent should summarize.

It should include:

- Collection summary and counts.
- Source coverage by platform.
- Top user pain voices.
- Existing workarounds.
- Payment signals.
- Search/discovery signals.
- Substitute and competitor map.
- Amazon light product snapshot when available.

See `references/pipeline-structure.md` for the default evidence-pack structure.

## Display Rules

- Main report sections should only show collected evidence.
- Do not display empty sections just to preserve the template.
- Do not show rows such as `Not collected`, `No verifiable link found`, or `Current sample too small` inside primary evidence tables.
- Evidence rows require a source and link. If no source link is available, do not include the row in the evidence table.
- Placeholder links such as `https://example.com`, `https://reddit.com/...`, `https://youtube.com/watch?v=...`, or any URL containing `...` must never appear in evidence tables.
- If showing a template-only example, label it clearly as a structure example and do not present it as collected evidence.
- Use a short final `Evidence boundary` or `Not covered` note only when missing evidence affects the verdict.
- Do not pad Top lists. If only 3 linked evidence rows were collected, output 3 rows.
- Every insight must point back to a linked evidence row, source, or exact collected count.

## Agent Reporting

After the evidence pack exists, hand off to the route declared in the routing token:

- `route: existing` → apply [`../amazon-voc-research/SKILL.md`](../amazon-voc-research/SKILL.md) layers (Competitor Ledger, Listing Claims, Top Positive/Negative Voices, Counter-evidence, etc.).
- `route: emerging` → apply [`../emerging-demand-research/SKILL.md`](../emerging-demand-research/SKILL.md) layers (Problem Evidence, Workarounds, Willingness-to-Pay, Counter-evidence, etc.).
- `route: hybrid` → both layer sets plus the required Conflict Resolution section.
- End with the structured YAML verdict from [`../vibe-product-demand-research/references/output-format.md`](../vibe-product-demand-research/references/output-format.md).

Counter-evidence is required regardless of route. The crawler pipeline must run an explicit counter-evidence search pass (failed Kickstarters, abandoned repos, discontinued listings, "this isn't worth solving" comments) and feed those records into the evidence pack.

## Guardrails

- Do not describe this as a full database or complete market coverage.
- Do not output exact sales, market size, BSR history, or growth trend unless collected evidence supports it.
- Do not claim official Amazon data when using public-page collection or third-party crawlers.
- Do not let the agent infer from noisy raw crawl data; clean first.
- If a source fails, record the failure briefly and continue with other sources.
