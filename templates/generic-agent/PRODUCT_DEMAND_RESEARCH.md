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

## Evidence Rules

- Do not invent reviews, comments, counts, sales, trends, market size, or payment signals.
- Do not use vague ratings such as `high`, `medium`, `low`, `strong`, or `weak`.
- Use exact collected values when available.
- If evidence is unavailable, write a short status such as `Not collected`, `No verifiable link found`, or `Current sample too small; not reported`.
- Important claims must cite links, user voices, review rows, source rows, or exact collected counts.

## Verdict Style

Use factual verdicts:

- `Demand is supported by repeated user complaints and workaround behavior.`
- `Demand is visible, but payment evidence is not collected.`
- `Demand is supported by existing retail reviews, but the new use case requires separate validation.`
- `Current evidence is mostly media attention; user pain evidence is thin.`
- `Current sample too small; demand judgment not reported.`
