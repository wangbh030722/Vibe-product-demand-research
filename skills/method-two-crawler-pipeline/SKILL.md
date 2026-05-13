---
name: method-two-crawler-pipeline
description: Plan and use a method-two demand research pipeline that separates crawler scripts, source-specific collectors, local cleaning, evidence-pack generation, and final agent reporting. Use when the user wants a cheaper alternative to paid Amazon/VOC APIs, wants to test crawler-based product demand research, or wants to validate emerging demand using Reddit, YouTube, Product Hunt, crowdfunding, search signals, and lightweight Amazon product discovery without relying on expensive review APIs.
---

# Method Two Crawler Pipeline

## Purpose

Use this as the more complete, lower-cost architecture for product demand research when paid review APIs are too expensive or unreliable.

The core idea:

```text
collector scripts -> raw JSONL -> cleaner/dedupe/ranker -> evidence pack -> agent report
```

The agent should not directly consume huge raw crawls. Scripts collect and normalize data first; the agent reads a compact evidence pack and applies the demand-research rules.

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
- Missing or unsupported claims.

See `references/pipeline-structure.md` for the default evidence-pack structure.

## Agent Reporting

After the evidence pack exists, use `vibe-product-demand-research` rules:

- Route the market as existing, emerging, or hybrid.
- For existing-market evidence, preserve VOC-style positives/negatives.
- For emerging-market evidence, emphasize pain, workarounds, search, and payment behavior.
- End with a factual demand verdict and evidence boundary.

## Guardrails

- Do not describe this as a full database or complete market coverage.
- Do not output exact sales, market size, BSR history, or growth trend unless collected evidence supports it.
- Do not claim official Amazon data when using public-page collection or third-party crawlers.
- Do not let the agent infer from noisy raw crawl data; clean first.
- If a source fails, record the failure briefly and continue with other sources.
