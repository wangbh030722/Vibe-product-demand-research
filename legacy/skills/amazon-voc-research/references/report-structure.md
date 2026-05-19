# Amazon VOC Research Report Structure

Use this structure for a full Amazon category/VOC report. Keep only sections supported by collected evidence.

## 1. Collection Summary

| Field | Result |
|---|---|
| Marketplace | Amazon US / other marketplace |
| Query | Exact user query and search variants |
| Collection time | Timestamp |
| Amazon search links | Markdown links |
| Amazon direct product links | Markdown links or `Not collected` |
| Brand/product search links | Markdown links |
| Best Sellers/New Releases links | Markdown links or `Not collected` |
| Product cards collected | Exact count |
| Product pages opened | Exact count |
| Products with reviews collected | Exact count |
| Total reviews collected | Exact count |
| Recent reviews collected | Exact count and window, if collected |
| Positive reviews collected | Exact count and rating definition |
| Negative reviews collected | Exact count and rating definition |
| Positive themes collected | Exact count out of 5 |
| Negative themes collected | Exact count out of 5 |
| Not reported | Short status rows only |

## 2. Competitor Ledger

| Product | Amazon link | Official/independent link | Review/source link | Brand | Price | Rating | Review count | Visible listing claims | Status |
|---|---|---|---|---|---:|---:|---:|---|---|

Include only values visible or collected. Use `Not collected` for missing fields.

## 3. Listing Claims

| Product | Product link | Claim | Where visible | Review evidence status |
|---|---|---|---|---|

Examples of claims: no subscription, long battery life, sleep tracking, waterproof, HRV, heart rate, sizing kit, app insights.

## 4. Top Positive Review Evidence

Mandatory for VOC reports. Rank by collected sample count. Include up to 5 rows. If Amazon reviews are unavailable or insufficient, use other verifiable public review sources and label the source type. Do not use placeholders or invented reviews.

| Rank | Positive theme | Review count | Product count | Product link | Review/source link | Source type | English customer voice | Chinese translation | Insight |
|---:|---|---:|---:|---|---|---|---|---|---|

## 5. Top Negative Review Evidence

Mandatory for VOC reports. Rank by collected sample count. Include up to 5 rows. If Amazon reviews are unavailable or insufficient, use other verifiable public review sources and label the source type. Do not use placeholders or invented reviews.

| Rank | Negative theme | Review count | Product count | Product link | Review/source link | Source type | English customer voice | Chinese translation | Insight |
|---:|---|---:|---:|---|---|---|---|---|---|

## 6. User Segments

| Segment | Evidence | Main desired outcome | Main concern | Source links |
|---|---|---|---|---|

Segments must come from review language, listing targeting, Q&A, or external sources. Do not invent demographic profiles.

## 7. Usage Scenarios

| Scenario | User task | Positive evidence | Negative evidence | Insight |
|---|---|---|---|---|

Examples: sleeping, training recovery, daily wear, travel, gifting, health tracking.

## 8. Jobs To Be Done

| Job | What user is trying to accomplish | Current substitute | Substitute weakness | Evidence |
|---|---|---|---|---|

Use only jobs visible from review language or source evidence.

## 9. Purchase Barriers

| Barrier | Stage | Evidence | Source links | Insight |
|---|---|---|---|---|

Stages can include discovery, checkout, setup, first week, long-term use, exchange/return.

## 10. Listing Promise vs Review Reality

| Product | Product link | Listing promise | Positive validation | Negative contradiction | Evidence links | Insight |
|---|---|---|---|---|---|---|

This is often the highest-value section for product research.

## 11. Attribute Importance

| Attribute | Positive review count | Negative review count | Product count | Evidence links | Insight |
|---|---:|---:|---:|---|---|

Examples: sizing, battery, accuracy, app, comfort, waterproofing, subscription, design, charging.

## 12. Unmet Needs

| Unmet need | Evidence | Products involved | Source links | Confidence boundary |
|---|---|---|---|---|

Use confidence boundaries such as `Supported by collected negative reviews from 4 products` instead of vague adjectives.

## 13. Substitute Map

| Substitute | Why users use it | Why users leave it | Evidence links | Insight |
|---|---|---|---|---|

Only output if substitutes are mentioned in reviews, listings, or external sources.

## 14. Value Perception

| Price/value theme | Evidence | Products involved | Source links | Insight |
|---|---|---|---|---|

Do not infer value perception from price alone. Tie it to review language.

## 15. Evidence-Backed Insights

| Rank | Insight | Supporting evidence | Links |
|---:|---|---|---|

Keep insights concise and descriptive. Do not give unsupported product instructions. Insights must be derived from the collected product rows, review rows, source links, or exact counts.

## 16. Counter-evidence (mandatory)

| Counter-signal | Evidence | Source link | Effect on verdict |
|---|---|---|---|

Examples of counter-signals:
- Discontinued or out-of-stock-for-months products in the same niche.
- Established alternatives with high review volume and persistent low ratings.
- Negative review themes that argue the underlying job is not worth solving.
- Editorial verdicts that the category is in decline.

If a real counter-evidence search returns nothing, output a single row:
`Counter-evidence search performed; none found. | Queries: <list> | <links to the empty search result pages> | Verdict gating still applies.`

The verdict cannot be `supported` if this section is empty without that explicit note.

## 17. Market-Entry Facts

| Fact | Evidence | Boundary |
|---|---|---|

State objective observations only. Do not turn this section into advice unless the user asks for recommendations.

Example boundaries:
- `Based only on 62 collected product pages`
- `No time-series collection; trend not reported`
- `Review sample includes 1-3 star reviews only`

## 18. Structured Verdict

End the report with the YAML verdict block defined in [`../../vibe-product-demand-research/references/output-format.md`](../../vibe-product-demand-research/references/output-format.md). `status: supported` requires the Counter-evidence section to be non-empty and `counter_evidence_addressed: true`.

## 19. Not Reported

| Item | Status |
|---|---|

Examples:
- `Sales trend | Collected sample does not support a trend claim`
- `Exact sales | Not collected`
- `BSR history | Not collected`
- `Market size | Current sample too small; not reported`
