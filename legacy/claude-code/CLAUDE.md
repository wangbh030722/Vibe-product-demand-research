# Claude Code Instructions: Product Demand Research

When asked to evaluate a product idea, use the Product Demand Research template.

## Objective

Determine whether the demand is real using evidence from user behavior, not generic market assumptions.

## Workflow

1. Route the idea as `Existing market`, `Emerging market`, or `Hybrid market`.
2. Collect evidence from the appropriate source types.
3. Preserve source links and short user/review voices.
4. Produce a concise demand reality report.
5. State what the evidence supports and what it does not support.
6. When file output is available, create a self-contained HTML report page.

Only render evidence sections that contain collected, linked evidence. Do not include placeholder rows or empty sections.
Do not use fake links or placeholder URLs in evidence tables.

The HTML page should use a clean Nothing-inspired style: black/white, thin grid lines, strong typography, compact evidence cards, and subtle scroll/hover animation.

## Existing Market

Use this path when products and reviews already exist. Research Amazon, retail pages, official product pages, competitor reviews, positive review themes, negative review themes, and listing promise vs review reality.

## Emerging Market

Use this path when the idea is new or lacks mature retail review evidence. Research user complaints, community discussions, search behavior, workarounds, substitutes, crowdfunding, preorders, paid tools, waitlists, and early product pages.

## Method Two Pipeline

If paid Amazon/VOC APIs are too expensive, use a lower-cost pipeline:

```text
collector scripts -> raw JSONL -> cleaner/dedupe/ranker -> evidence pack -> agent report
```

Prioritize Reddit, YouTube comments, Product Hunt, Kickstarter, Indiegogo, App Store, Chrome Web Store, search signals, and lightweight Amazon product discovery. Do not make Amazon review scraping the first bottleneck.

## Rules

- Do not invent evidence.
- Do not use vague scoring labels.
- Do not output market size, sales, or trend claims unless directly supported.
- Include links for important claims.
- Use short original user/review voice plus translation when useful.
- End with a factual demand verdict and evidence boundary.
