---
name: amazon-voc-research
description: Create evidence-backed Amazon category and VOC research reports for product research, user research, market-entry evaluation, review mining, competitor comparison, and Amazon product opportunity analysis. Use when the user asks to research an Amazon category, product niche, ASIN set, keyword, competitor group, customer reviews, good/bad review themes, user pain points, market entry facts, or a VOC-style report based on Amazon pages and broad web search.
---

# Amazon VOC Research

## Core Standard

Produce a linked, evidence-backed VOC and category research report. Combine broad web search with marketplace public-page collection. The report must include objective collected data, linked evidence, review voice, translations when useful, and concise insights derived from the evidence.

Do not present the work as a proprietary company methodology. Do not name any specific product-methodology brand unless the user explicitly asks.

The report should read like a real user-research and product-research artifact, not a generic market overview. It must preserve the raw evidence layer and then derive insights from it.

Evidence integrity rules (banned language, link rules, number rules, quote rules, counter-evidence requirement, verdict gating) are defined once in [`../../references/evidence-rules.md`](../../references/evidence-rules.md). Follow them; do not restate them here.

## Required Collection

Always perform both collection tracks unless blocked:

1. **Broad web search**
   - Search the open web for the category, major brands, product names, reviews, launch/news pages, marketplace pages, and relevant public reports.
   - Prefer official brand pages, marketplace pages, public marketplaces, review pages, and credible third-party pages.
   - Record links used in the report.

2. **Marketplace public-page collection**
   - Pick the marketplace appropriate to `target_market` (Amazon for US/EU/JP English-speaking buyers, 京东/天猫 for CN, etc.). Search for the user keyword and relevant keyword variants in the target language.
   - Collect search result pages, product pages, review pages when accessible, brand/store links when visible, Best Sellers / New Releases / category leaderboards when relevant.
   - Prefer direct product links over search links. Use search links only as fallback when direct product pages are not verifiably collected.
   - Include all collected marketplace links in the report.

3. **Product identity collection**
   - For every competitor product, collect both the marketplace link and the official/independent product-site link when available.
   - Include retailer/review links separately from official links.
   - Do not treat a search-result link as equivalent to a product page. Label it as a search entry if no direct product page is collected.

Use browser automation, web search, page inspection, screenshots, or manual link construction as appropriate. Respect site limits, avoid aggressive scraping, and do not bypass access controls.

## Review Voice Requirement

Top positive and top negative review voice are mandatory output modules for VOC reports.

- Always output Top 1-5 positive themes and Top 1-5 negative themes from collected review evidence.
- Do not omit these sections just because marketplace original reviews are unavailable.
- If marketplace review pages are not accessible or the sample is too small, expand review collection to other verifiable public sources: Best Buy, Walmart, Target, Google Shopping, official brand-site reviews, Reddit threads, YouTube comments, app-store reviews for companion apps, and credible long-form review pages. For CN: 京东评价, 天猫问大家, 小红书笔记评论, B站视频评论.
- Clearly label the source type for each voice row, for example `Amazon review`, `京东 review`, `Best Buy review`, `Reddit comment`, `YouTube comment`, `App Store review`, or `Editorial review excerpt`.
- Prefer customer-generated reviews over editorial sources. Use editorial sources only when customer-generated review evidence is not enough; label them as editorial rather than customer voice.
- Each row must include the original-language voice, Chinese translation when useful, product link, review/source link, source type, theme, count when count is actually collected, and a concise insight.
- Keep voice excerpts short and source-faithful. Put interpretation in the `insight` field, not in the customer-voice field.
- If fewer than 5 positive or fewer than 5 negative themes are collected after expanding sources, output all collected rows and state the exact shortfall in the collection summary (e.g. `Positive themes collected: 3 of 5`).
- Do not fill missing rows with placeholders, guessed sentiment, or invented reviews.

## Counter-evidence (mandatory)

Per [`../../references/evidence-rules.md`](../../references/evidence-rules.md), every VOC report must include a `Counter-evidence` layer:

- Discontinued products in the same category (with marketplace links showing the listing is dead or out of stock long-term).
- Low-rated established alternatives that already cover the proposed use case.
- High-volume negative review themes that argue the underlying problem isn't worth solving.
- Editorial / review-site verdicts that the category is in decline.

If a real counter-evidence search returns nothing, write `Counter-evidence search performed; none found.` plus the queries used. The verdict cannot be `supported` if this layer is empty without that note.

## Output Completeness Checklist

Before finalizing a full report, make sure it includes these layers when evidence exists:

- Collection summary with exact query variants, collection time, source links, counts, and planned-vs-actual reconciliation against the router's `collection_plan`.
- Competitor ledger with product name, marketplace link, official/independent link, review/source link, price, rating, review count, listing claims, and collection status.
- Marketplace category/search/Best Sellers links, clearly separated from direct product links.
- Top 1-5 positive review evidence with original-language voice and Chinese translation when useful.
- Top 1-5 negative review evidence with original-language voice and Chinese translation when useful.
- Listing claims and review reality comparison.
- User segments, usage scenarios, jobs to be done, purchase barriers, substitutes, attribute importance, unmet needs, and value perception when supported.
- **Counter-evidence layer (mandatory).**
- Evidence-backed insights that cite review rows, product rows, counts, or source links.
- Market-entry facts stated as objective observations, not advice.
- Not-reported section for unsupported trends, exact sales, BSR history, market size, or any missing source layer.
- Structured verdict YAML (schema in [`../vibe-product-demand-research/references/output-format.md`](../vibe-product-demand-research/references/output-format.md)).

## Report Shape

Use the structure in [`references/report-structure.md`](references/report-structure.md) as the default. Load it when producing a full report or when the user asks what the output should include.

## Insight Style

Write insights as observed patterns, not recommendations. Good:

- `Positive reviews frame smart rings as a sleep-time alternative to watches, not simply as another health tracker.`
- `Negative reviews treat sizing mismatch as a product failure, not a minor fit issue, because it creates exchange friction and low-star reviews.`
- `Listing claims around long battery life require verification against reviews because low-star reviews repeatedly compare advertised battery life with actual use.`

Avoid generic competitive-intensity statements, unsupported prescriptions, growth claims without time-series evidence, and pain claims without counts or source links.
