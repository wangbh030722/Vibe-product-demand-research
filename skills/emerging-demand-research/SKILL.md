---
name: emerging-demand-research
description: Research whether demand is real for emerging products, new categories, non-stock products, early markets, new interactions, potential product ideas, and categories without enough Amazon or retail review evidence. Use when the user asks to validate a new product idea, uncover real pain points, inspect workaround behavior, collect willingness-to-pay signals, or distinguish user demand from media hype.
---

# Emerging Demand Research

## Core Standard

Validate whether a non-stock or emerging-market product demand is real. Do not force Amazon VOC logic onto products that lack mature retail review evidence.

The core question is not whether competitors sell well. The core question is whether users already show real behavior around the problem:

- Complaining about the problem.
- Searching for a solution.
- Using awkward substitutes or manual workarounds.
- Paying, preordering, subscribing, joining waitlists, backing crowdfunding, or buying adjacent products.
- Repeating the same pain across independent communities.

## Required Collection

Always perform broad web search and community/source collection unless blocked.

Search for the product idea, problem phrase, user scenario, existing substitutes, competitor names, and English keyword variants across:

- Reddit, YouTube, TikTok, X, Quora, Hacker News, Discord/forum pages, and vertical communities.
- Google Trends, search suggestions, SEO pages, and search result clusters.
- Product Hunt, Kickstarter, Indiegogo, App Store, Chrome Web Store, Shopify/independent stores, Gumroad, and waitlist/preorder pages.
- Blogs, media reviews, comment sections, competitor FAQs, changelogs, docs, and public communities.

Use Amazon/retail pages only when they help identify adjacent substitutes or hybrid-market evidence. Do not treat missing Amazon reviews as a reason to stop.

## Evidence Rules

- Every source, user voice, product, workaround, payment signal, and trend/discovery signal must include a link when available.
- Do not use placeholders such as `X`, `xx%`, `many`, `several`, `high`, `medium`, `low`, `strong`, or `weak`.
- Use exact collected values. If a value is unavailable, write a short status or omit the metric.
- Do not output market size, exact sales, search volume, or growth claims unless the collected data directly supports them.
- Do not invent user comments, quotes, reviews, waitlist counts, backing amounts, or payment behavior.
- Quote only short source-faithful excerpts. Put interpretation in the insight field, not in the original voice field.
- Do not explain missing evidence as `no API available` in the report.

## Mandatory Output Layers

Use `references/report-structure.md` for full reports.

At minimum, include:

1. **Collection summary**
   - Query variants, collection time, platforms searched, source links, discussion/comment count, workaround count, payment-signal count, and unreported items.

2. **Problem evidence**
   - Top 1-5 user pain voices.
   - Include source link, source type, English original, Chinese translation, complained problem, scenario, and insight.

3. **Existing workarounds**
   - How users solve the problem now: substitutes, manual workflows, service outsourcing, software substitutes, hardware substitutes, or behavior changes.
   - This is a key proof of real pain: if users spend effort to solve it, the problem may be real.

4. **Willingness-to-pay signals**
   - Crowdfunding, preorder, paid app, subscription product, independent-store pricing, paid community, purchase comments, enterprise procurement, or paid adjacent tools.
   - If not collected, write `Payment signal not collected`.

5. **Search and discovery signals**
   - Search terms, Google Trends/search suggestions, SEO pages, YouTube searches, Reddit recurring questions, and repeated community phrases.
   - Do not equate search visibility with demand; describe what it does and does not prove.

6. **Substitute and competitor map**
   - Direct competitors, indirect competitors, adjacent substitutes, and workaround flows.

7. **Demand reality insights**
   - Insights must be derived from evidence rows.
   - Answer whether the pain looks real, whether user behavior exists, what job the product serves, and why current solutions fall short.

8. **Demand verdict**
   - Use factual verdicts, not numeric or vague scores.
   - Include evidence boundaries.

## Demand Verdict Style

Good verdicts:

- `Demand is supported by repeated user complaints and workaround behavior across Reddit and YouTube comments. Payment evidence was not collected.`
- `Demand is visible as search and media interest, but collected user-pain evidence is thin.`
- `Demand is supported by crowdfunding/preorder behavior, but long-term retention evidence is not collected.`

Avoid:

- `The market is high potential.`
- `This is a good idea.`
- `Demand is strong` without source rows.
- `Users will pay` without payment evidence.
