# Method Two Pipeline Structure

Use this structure for the cheaper crawler-based demand research path.

## 1. Collection Plan

| Field | Result |
|---|---|
| Query | Product idea, category, and keyword variants |
| Market route | Existing / emerging / hybrid |
| Time window | Requested period or `Not specified` |
| Primary sources | Reddit, YouTube, Product Hunt, crowdfunding, search, Amazon light, etc. |
| Excluded sources | Sources skipped with short reason |
| Collection mode | Scripted crawl / manual import / mixed |

## 2. Raw Collection Summary

| Source | Records collected | Links collected | Comments/reviews collected | Status |
|---|---:|---:|---:|---|

Use exact counts only.

## 3. Cleaned Evidence Summary

| Evidence category | Records kept | Records dropped | Reason for drops |
|---|---:|---:|---|

Categories:

- user pain
- workaround
- payment signal
- search/discovery signal
- product/competitor
- positive voice
- negative voice

## 4. User Pain Evidence

| Rank | Pain theme | Source | Link | Original voice | Chinese translation | Scenario | Insight |
|---:|---|---|---|---|---|---|---|

## 5. Workaround Evidence

| Workaround | Source | Link | User behavior | Friction | Insight |
|---|---|---|---|---|---|

## 6. Payment Signal Evidence

| Signal type | Source/product | Amount/price/count | Link | What it proves | Boundary |
|---|---|---|---|---|---|

Examples: crowdfunding backers, preorder, paid app, subscription, paid community, purchase comment, independent-store pricing.

## 7. Search and Discovery Evidence

| Signal | Source | Observed phrase/result | Link | What it proves | What it does not prove |
|---|---|---|---|---|---|

## 8. Amazon Light Snapshot

| Product | Amazon/search link | Official link | ASIN | Price | Rating | Review count | Visible claims | Status |
|---|---|---|---|---:|---:|---:|---|---|

This section is for product discovery only. Do not treat it as review VOC unless review text was actually collected or imported.

## 9. Evidence Pack Verdict Inputs

| Verdict input | Evidence | Boundary |
|---|---|---|

Examples:

- repeated pain across independent communities
- users using manual workarounds
- payment/preorder evidence
- only media coverage, no user voice
- Amazon products exist but review text not collected

## 10. Not Reported

| Item | Status |
|---|---|

Examples:

- `Amazon review text | Not collected`
- `Exact sales | Not collected`
- `Market size | Current sample too small; not reported`
- `Growth trend | Collected sample does not support a trend claim`
