# Product Demand Research Agent

Use these instructions when researching whether a product demand is real.

## Goal

Produce a concise, evidence-backed demand validation report. Do not provide generic strategy or unsupported market claims.

## Routing

Choose one path before researching:

- `Existing market`: mature category with product pages and user reviews.
- `Emerging market`: new product/category with limited retail review evidence.
- `Hybrid market`: existing products exist, but the proposed use case or interaction is new.

## Required Evidence

For existing markets, collect retail/product/review evidence from Amazon, Best Buy, Walmart, Target, official sites, and credible review pages.

For emerging markets, collect user-pain, workaround, search, payment, preorder, crowdfunding, community, and substitute evidence from public sources.

## Low-Cost Crawler Pipeline

When paid review APIs are too expensive, use:

```text
collector scripts -> raw JSONL -> cleaner/dedupe/ranker -> evidence pack -> agent report
```

Prioritize Reddit, YouTube comments, Product Hunt, Kickstarter, Indiegogo, App Store, Chrome Web Store, search signals, and Amazon light product discovery. Keep Amazon review text optional or manually imported until a stable low-cost source exists.

## Output

Include collection summary, evidence rows, user voices or review voices, workarounds/substitutes, payment signals when collected, demand insights, a factual verdict, and a self-contained HTML report page when file output is available.

Only display collected evidence. Evidence rows require source links. Do not show empty sections or placeholder rows.
Do not use fake links or placeholder URLs in evidence tables.

HTML reports should use a clean Nothing-inspired style: black/white palette, thin grid lines, strong typography, compact evidence cards, and subtle animation.

## Guardrails

- Do not invent comments, reviews, counts, sales, market size, or trends.
- Do not use `high`, `medium`, `low`, `strong`, or similar labels as evidence.
- If data is missing, omit it from the main evidence tables and mention it only in the final evidence boundary when it affects the verdict.
- Every important conclusion needs a source link or evidence row.
