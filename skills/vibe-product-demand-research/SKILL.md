---
name: vibe-product-demand-research
description: Route and synthesize product demand validation research for existing Amazon/retail markets, emerging markets, new product ideas, non-obvious categories, potential market demand, product-market evidence, user pain validation, workaround analysis, willingness-to-pay signals, and demand reality judgments. Use when the user asks whether a product demand is real, whether a product idea has a market, whether a category is worth researching, or which demand-research path to use.
---

# Vibe Product Demand Research

## Purpose

Use this as the router and synthesis layer for product demand validation. The goal is to judge whether a product demand is real based on evidence, not to produce generic market advice.

Route to:

- The bundled `amazon-voc-research` reference for existing products, mature categories, Amazon/retail categories, competitor review mining, and VOC based on product/review pages.
- The bundled `emerging-demand-research` reference for non-stock, new-category, early-market, new-interaction, or potential products where Amazon reviews are insufficient or misleading.
- Both skills for hybrid markets where some products exist but the actual proposed behavior, interaction, or use case is still emerging.

## Routing Workflow

Start every task with a short routing diagnosis:

| Check | Evidence to look for | Route implication |
|---|---|---|
| Existing Amazon/retail products | Amazon, Best Buy, Walmart, Target, category pages, product reviews | Existing market |
| Clear competitor set | Named brands, review pages, comparison pages, marketplace listings | Existing market or hybrid |
| New interaction/use case | Little Amazon review evidence, new hardware/software behavior, early media coverage, prototypes | Emerging market |
| User pain exists outside shopping context | Reddit complaints, forums, YouTube comments, search behavior, workaround discussions | Emerging market |
| Some product evidence plus new behavior | Retail products exist, but the user asks about a new use case or new product form | Hybrid market |

Output exactly one of:

- `Existing market: use amazon-voc-research`
- `Emerging market: use emerging-demand-research`
- `Hybrid market: use both and synthesize`

Then perform or request the appropriate research path. If producing the final report directly, synthesize the relevant skill outputs into a demand-reality report.

## Evidence Standards

- Do not use vague ratings such as `high`, `medium`, `low`, `strong`, `weak`, or `medium-high` as substitutes for evidence.
- Do not invent counts, reviews, market size, sales, BSR, search volume, or trend claims.
- If a source layer is missing, use a short status such as `Not collected`, `No verifiable link found`, `Current sample too small; not reported`, or `Collected sample does not support a trend claim`.
- Do not explain missing evidence as `no API available` in the user-facing report.
- Demand conclusions must cite concrete evidence: review rows, user-voice rows, workaround rows, payment rows, source links, or exact collected counts.

## Report Synthesis

For existing markets, preserve the `amazon-voc-research` evidence layers:

- Amazon/search/category links.
- Direct product links and official/independent links.
- Top 1-5 positive review voices.
- Top 1-5 negative review voices.
- Listing promise vs review reality.
- Market-entry facts.

For emerging markets, preserve the `emerging-demand-research` evidence layers:

- Problem evidence and raw user voice.
- Existing workarounds.
- Willingness-to-pay signals.
- Search and discovery signals.
- Substitute and competitor map.
- Demand reality insights and verdict.

For hybrid markets, include both:

1. Existing-product VOC evidence.
2. Emerging-demand evidence for the new behavior/use case.
3. A boundary statement explaining which conclusions come from product reviews and which come from early-market signals.

## Final Demand Verdict

Use factual verdicts, not scores:

- `Demand is supported by repeated user complaints and workaround behavior.`
- `Demand is supported by existing retail reviews, but the new use case requires separate validation.`
- `Demand is visible, but payment evidence is not collected.`
- `Current evidence is mostly media attention; user pain evidence is thin.`
- `Current sample too small; demand judgment not reported.`

Each verdict must include an evidence boundary.

## Final Output Format

For complete reports, output both:

1. A concise Markdown research summary in the conversation.
2. A clean, animated HTML report page suitable for sharing or opening locally.

Use `references/output-format.md` for the required report structure and HTML style direction.

The HTML page should be Nothing-inspired: minimal black/white palette, strong typography, thin grid lines, high-contrast evidence cards, source-link chips, subtle scroll/reveal animation, and restrained motion. Do not copy proprietary assets or code from any external design repository.
