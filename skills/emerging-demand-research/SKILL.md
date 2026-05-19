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

Evidence integrity rules (banned language, link integrity, number rules, quote rules, data-status vocabulary) live in [`../../references/evidence-rules.md`](../../references/evidence-rules.md). Follow them; do not restate.

The emerging route additionally requires:

- Cross-community corroboration: a pain claim is only counted as `voice evidence` when it appears in at least two independent communities. Single-thread anecdotes are recorded but flagged.
- Workaround threshold: at least one collected workaround per major pain claim, or that pain claim is downgraded to `signal, not validated demand`.
- Counter-evidence (mandatory): see the section below.

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

7. **Counter-evidence (mandatory)**
   - Failed crowdfunding campaigns for the same idea or near-neighbor.
   - Dead / abandoned open-source or community projects targeting the same pain.
   - High-volume user comments saying current workarounds are good enough or the problem isn't worth solving.
   - Media verdicts that prior attempts at the category failed.
   - If a real counter-evidence search returns nothing, write `Counter-evidence search performed; none found.` plus queries used. Do not leave this section empty.

8. **Demand reality insights**
   - Insights must be derived from evidence rows.
   - Answer whether the pain looks real, whether user behavior exists, what job the product serves, and why current solutions fall short.

9. **Demand verdict**
   - Natural-language sentence + structured YAML block (schema in [`../vibe-product-demand-research/references/output-format.md`](../vibe-product-demand-research/references/output-format.md)).
   - `status: supported` requires non-empty Counter-evidence section and `counter_evidence_addressed: true`.

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
