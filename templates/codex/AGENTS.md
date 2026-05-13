# Product Demand Research

When the task is to evaluate whether a product idea or category has real demand, use the `vibe-product-demand-research` skill pack in this repository.

## Default Behavior

Route the idea first:

- Existing market -> use Amazon/retail VOC evidence.
- Emerging market -> use user pain, workaround, search, and payment evidence.
- Hybrid market -> use both and clearly separate the evidence boundaries.

## Evidence Standards

- Prefer source-linked evidence over general summaries.
- Include short user/review voices with translation when useful.
- Do not invent reviews, comments, counts, trends, market size, or payment signals.
- Avoid vague demand scores.
- Only display evidence rows that have source links.
- Do not show empty sections or placeholder rows.
- Do not use fake links or placeholder URLs in evidence tables.
- End with a factual demand verdict.

## Method Two Pipeline

If the request mentions cheap crawlers, avoiding expensive APIs, or method two, use the method-two crawler pipeline:

```text
collector scripts -> raw JSONL -> cleaner/dedupe/ranker -> evidence pack -> agent report
```

Use Reddit, YouTube comments, Product Hunt, crowdfunding, app/extension stores, search signals, and Amazon light product discovery before considering paid Amazon review APIs.
