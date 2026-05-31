# Method Two Pipeline Structure

Use this structure for the cheaper crawler-based demand research path.

## Display Rule

Only render sections that contain collected, source-linked evidence. Do not display empty sections or placeholder rows in the main report. Placeholder links such as `https://reddit.com/...`, `https://youtube.com/watch?v=...`, `https://example.com`, or any URL containing `...` must not appear in evidence tables. If a missing source affects the verdict, mention it briefly in the final evidence boundary.

## 1. Collection Plan

| Field | Result |
|---|---|
| Query | Product idea, category, and keyword variants |
| Market route | Existing / emerging / hybrid |
| Time window | Requested period or `Not specified` |
| Primary sources | Reddit, YouTube, Product Hunt, crowdfunding, search, Amazon light, etc. |
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

Include a row only if the source and link are available.

## 5. Workaround Evidence

| Workaround | Source | Link | User behavior | Friction | Insight |
|---|---|---|---|---|---|

Include a row only if the source and link are available.

## 6. Payment Signal Evidence

| Signal type | Source/product | Amount/price/count | Link | What it proves | Boundary |
|---|---|---|---|---|---|

Examples: crowdfunding backers, preorder, paid app, subscription, paid community, purchase comment, independent-store pricing.

Omit this section if no linked payment signal was collected.

## 7. Search and Discovery Evidence

| Signal | Source | Observed phrase/result | Link | What it proves | What it does not prove |
|---|---|---|---|---|---|

Include a row only if the source and link are available.

## 8. Amazon Light Snapshot

| Product | Amazon/search link | Official link | ASIN | Price | Rating | Review count | Visible claims | Status |
|---|---|---|---|---:|---:|---:|---|---|

This section is for product discovery only. Do not treat it as review VOC unless review text was actually collected or imported.

Omit this section if no Amazon product/search evidence was collected.

## 9. Evidence Pack Verdict Inputs

| Verdict input | Evidence | Boundary |
|---|---|---|

Examples:

- repeated pain across independent communities
- users using manual workarounds
- payment/preorder evidence
- only media coverage, no user voice
- Amazon products exist but review text not collected

## 10. Evidence Boundary

Use this section only for missing evidence that affects the verdict. Keep it short.

| Boundary | Impact |
|---|---|

Examples:

- `Amazon review text was not collected | Do not present mature Amazon VOC conclusions`
- `No linked payment evidence collected | Do not claim purchase intent`
- `No time-series data collected | Do not claim growth trend`
