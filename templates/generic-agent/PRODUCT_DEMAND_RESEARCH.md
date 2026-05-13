# Product Demand Research Agent Template

Use this template to evaluate whether a product demand is real.

## Goal

Judge whether a product idea, category, or use case is supported by real user behavior.

Do not produce generic market advice. Produce evidence-backed demand research.

## Route the Research

Start with one routing decision:

- `Existing market`: products and reviews already exist.
- `Emerging market`: the product/category is new and has weak retail evidence.
- `Hybrid market`: existing products exist, but the proposed behavior or use case is new.

## Existing Market Evidence

Use when the market has products and reviews.

Collect:

- Amazon search/category/product/review links.
- Official product links.
- Retail pages such as Best Buy, Walmart, Target, or brand stores.
- Top 1-5 positive review themes with short original voice and translation.
- Top 1-5 negative review themes with short original voice and translation.
- Listing promise vs review reality.
- Market-entry facts supported by evidence.

## Emerging Market Evidence

Use when Amazon/retail reviews are insufficient or misleading.

Collect:

- Reddit, YouTube, TikTok, X, Quora, Hacker News, Discord/forum, and vertical community discussions.
- Product Hunt, Kickstarter, Indiegogo, App Store, Chrome Web Store, independent stores, waitlists, and preorder pages.
- Search/discovery signals such as Google Trends, search suggestions, SEO pages, and recurring search phrases.
- User pain voices.
- Existing workarounds.
- Willingness-to-pay signals.
- Substitute and competitor map.

## Output Requirements

Include:

- Collection summary.
- User pain or review evidence.
- Workarounds or substitute products.
- Payment or purchase signals when collected.
- Demand reality insights.
- Demand verdict with evidence boundary.
- A self-contained HTML report page when file output is available.

Only show sections with collected evidence. Evidence rows require source links. Do not include placeholder rows or empty sections.
Do not use fake links or placeholder URLs in evidence tables.

## HTML Report

When creating the HTML report:

- Use a clean Nothing-inspired style: black/white, thin grid lines, strong type hierarchy, compact evidence cards.
- Add subtle animation such as scroll reveal and hover motion.
- Keep it self-contained with inline CSS and small inline JavaScript.
- Do not include empty sections, placeholder links, fake charts, or unsupported scores.

## Method Two: Low-Cost Crawler Pipeline

When paid review APIs are too expensive, use a staged crawler pipeline:

```text
collector scripts -> raw JSONL -> cleaner/dedupe/ranker -> evidence pack -> agent report
```

Prioritize:

- Reddit for complaints, workarounds, and raw user language.
- YouTube comments for product experience and creator-audience feedback.
- Product Hunt for early product feedback.
- Kickstarter / Indiegogo for preorder and payment signals.
- App Store / Chrome Web Store for app and extension reviews.
- Search/SEO pages for discovery signals and problem phrases.
- Amazon search/product pages for lightweight product discovery.

Do not make Amazon review scraping the V1 bottleneck. Treat Amazon reviews as optional manual import or later paid data.

## Evidence Rules

- Do not invent reviews, comments, counts, sales, trends, market size, or payment signals.
- Do not use vague ratings such as `high`, `medium`, `low`, `strong`, or `weak`.
- Use exact collected values when available.
- If evidence is unavailable, do not show it in the main evidence tables. Mention it only in the final evidence boundary if it affects the verdict.
- Important claims must cite links, user voices, review rows, source rows, or exact collected counts.

## Verdict Style

Use factual verdicts:

- `Demand is supported by repeated user complaints and workaround behavior.`
- `Demand is visible, but payment evidence is not collected.`
- `Demand is supported by existing retail reviews, but the new use case requires separate validation.`
- `Current evidence is mostly media attention; user pain evidence is thin.`
- `Current sample too small; demand judgment not reported.`
