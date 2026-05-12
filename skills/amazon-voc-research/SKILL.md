---
name: amazon-voc-research
description: Create evidence-backed Amazon category and VOC research reports for product research, user research, market-entry evaluation, review mining, competitor comparison, and Amazon product opportunity analysis. Use when the user asks to research an Amazon category, product niche, ASIN set, keyword, competitor group, customer reviews, good/bad review themes, user pain points, market entry facts, or a VOC-style report based on Amazon pages and broad web search.
---

# Amazon VOC Research

## Core Standard

Produce a linked, evidence-backed VOC and category research report. Combine broad web search with Amazon public-page collection. The report must include objective collected data, linked evidence, review voice, translations when useful, and concise insights derived from the evidence.

Do not present the work as a proprietary company methodology. Do not name any specific product-methodology brand unless the user explicitly asks.

The report should read like a real user-research and product-research artifact, not a generic market overview. It must preserve the raw evidence layer and then derive insights from it.

## Required Collection

Always perform both collection tracks unless blocked:

1. **Broad web search**
   - Search the open web for the category, major brands, product names, reviews, launch/news pages, marketplace pages, and relevant public reports.
   - Prefer official brand pages, Amazon pages, public marketplaces, review pages, and credible third-party pages.
   - Record links used in the report.

2. **Amazon public-page collection**
   - Search Amazon for the user keyword and relevant English keyword variants.
   - Collect Amazon search result pages, product pages, review pages when accessible, brand/store links when visible, Best Sellers/New Releases/Movers & Shakers pages when relevant.
   - Prefer direct Amazon product links over search links. Use search links only as fallback when direct product pages are not verifiably collected.
   - Include all collected Amazon links in the report.
   - If a page, review, or module is not collected, state only a short data status such as `Not collected`, `Not visible on page`, `Current sample too small; not reported`, or `No verifiable link found`.

3. **Product identity collection**
   - For every competitor product, collect both the Amazon link and the official/independent product-site link when available.
   - Include retailer/review links separately from official links.
   - Do not treat an Amazon search result link as equivalent to a product page. Label it as an Amazon search entry if no direct product page is collected.

Use browser automation, web search, page inspection, screenshots, or manual link construction as appropriate. Respect site limits, avoid aggressive scraping, and do not bypass access controls.

## Evidence Rules

- Every product, brand, review, search page, Best Sellers page, and quoted review must have a link when available.
- Do not use placeholders such as `X`, `xx%`, `many`, `several`, `high`, `medium`, `low`, `relatively high`, or `medium-high`.
- Use exact collected values. If a value is unavailable, write `Not collected` or omit that metric.
- Do not output sales trend, market size, exact sales, BSR history, or growth claims unless the collected data supports them.
- If there is only one-time page data, call it a current page snapshot, not a trend.
- Do not invent reviews. If using a demo/sample, label it clearly as simulated and keep it separate from real evidence.
- Quote review snippets only when collected from the source and keep quotes short enough to comply with copyright limits. Prefer short excerpts plus paraphrase.
- Do not use vague scoring labels such as `high`, `medium`, `low`, `medium-high`, `good`, `bad`, `strong`, or `weak` as stand-ins for evidence. Use exact counts, named sources, concrete patterns, and source-linked observations. Only use comparative descriptors when directly comparing collected categories/products and the basis is shown.
- Do not use placeholder counts or fake precision. If the exact number is not collected, use a short status or omit the metric.
- Do not write explanations such as `no API available` inside the report. The user-facing report should say only that the evidence was not collected, not visible, insufficient, or not supported by the current sample.

## Review Voice Requirement

Top positive and top negative review voice are mandatory output modules for VOC reports.

- Always output Top 1-5 positive themes and Top 1-5 negative themes from collected review evidence.
- Do not omit these sections just because Amazon original reviews are unavailable.
- If Amazon review pages are not accessible or the Amazon sample is too small, expand review collection to other verifiable public sources, such as Best Buy, Walmart, Target, Google Shopping, official brand-site reviews, Reddit threads, YouTube comments, app-store reviews for companion apps, and credible long-form review pages.
- Clearly label the source type for each voice row, for example `Amazon review`, `Best Buy review`, `Walmart review`, `Reddit comment`, `YouTube comment`, `App Store review`, or `Editorial review excerpt`.
- Prefer customer-generated reviews over editorial sources. Use editorial sources only when customer-generated review evidence is not enough, and label them as editorial rather than customer voice.
- Each row must include the original English voice, Chinese translation, product link, review/source link, source type, theme, count when count is actually collected, and a concise insight.
- Keep voice excerpts short and source-faithful. Do not paraphrase inside the `English customer voice` field; put interpretation in the insight field.
- If fewer than 5 positive or fewer than 5 negative themes are collected after expanding sources, output all collected rows and state the exact shortfall in the collection summary, such as `Positive themes collected: 3 of 5` or `Negative themes collected: 2 of 5`.
- Do not fill missing rows with placeholders, guessed sentiment, or invented reviews.

## Output Completeness Checklist

Before finalizing a full report, make sure it includes these layers when evidence exists:

- Collection summary with exact query variants, collection time, source links, and counts.
- Competitor ledger with product name, Amazon link, official/independent link, review/source link, price, rating, review count, listing claims, and collection status.
- Amazon category/search/Best Sellers links, clearly separated from direct product links.
- Top 1-5 positive review evidence with English original voice and Chinese translation.
- Top 1-5 negative review evidence with English original voice and Chinese translation.
- Listing claims and review reality comparison.
- User segments, usage scenarios, jobs to be done, purchase barriers, substitutes, attribute importance, unmet needs, and value perception when supported.
- Evidence-backed insights that cite review rows, product rows, counts, or source links.
- Market-entry facts stated as objective observations, not advice.
- Not-reported section for unsupported trends, exact sales, BSR history, market size, or any missing source layer.

## Report Shape

Use the structure in `references/report-structure.md` as the default. Load it when producing a full report or when the user asks what the output should include.

At minimum, include:

1. **Collection summary**
   - Query, marketplace, collection time, source links, Amazon entry links, collected product count, collected review count, and unreported items.

2. **Competitor ledger**
   - Product name, Amazon link, official/independent link, review/source link, brand, price, rating, review count, visible listing claims, and collection status.

3. **Top positive review evidence**
   - Mandatory. Output up to Top 5 themes by collected sample count.
   - Include theme, count when actually collected, involved product count, product link, review/source link, source type, short English customer voice, Chinese translation, and insight.

4. **Top negative review evidence**
   - Mandatory. Output up to Top 5 themes by collected sample count.
   - Include theme, count when actually collected, involved product count, product link, review/source link, source type, short English customer voice, Chinese translation, and insight.

5. **User research layers**
   - User segments, scenarios, jobs-to-be-done, purchase barriers, substitutes, attribute importance, unmet needs, listing promise vs review reality, and value perception.
   - Only output layers supported by collected evidence.

6. **Insights**
   - Provide concise insights, not generic advice.
   - Each insight must cite evidence via links, counts, review snippets, or source rows.
   - Keep insights descriptive and evidence-based. Avoid unsupported prescriptions.

7. **Market-entry facts**
   - Summarize what the collected evidence says about whether the category looks accessible, crowded, risky, or under-served.
   - Tie every claim to collected data. If evidence is insufficient, write `Current sample too small; market-entry judgment not reported`.
   - State objective facts and evidence-backed constraints. Do not give step-by-step strategy unless the user asks for recommendations.

## Insight Style

Write insights as observed patterns, not recommendations. Good:

- `Positive reviews frame smart rings as a sleep-time alternative to watches, not simply as another health tracker.`
- `Negative reviews treat sizing mismatch as a product failure, not a minor fit issue, because it creates exchange friction and low-star reviews.`
- `Listing claims around long battery life require verification against reviews because low-star reviews repeatedly compare advertised battery life with actual use.`

Avoid:

- `The market is medium-high competition.`
- `You should make a better app.`
- `This category is growing` without time-series evidence.
- `Top 5 not output because Amazon reviews were not collected.`
- `There are many complaints about battery` without counts, links, or source rows.

## Missing Data

When data is missing, be brief:

- `Not collected`
- `Not visible on page`
- `No verifiable link found`
- `Current sample too small; not reported`
- `Collected sample does not support a trend claim`

Do not explain missing data by blaming lack of paid APIs unless the user asks about data-source strategy.
