# Emerging Demand Research Report Structure

Use this structure for new product ideas, non-stock products, early markets, and categories without enough Amazon/retail review evidence.

## 1. Collection Summary

| Field | Result |
|---|---|
| Query | Exact user query and English variants |
| Collection time | Timestamp |
| Platforms searched | Source names |
| Source links | Markdown links |
| Discussions collected | Exact count |
| User voices collected | Exact count |
| Workarounds collected | Exact count |
| Payment signals collected | Exact count |
| Search/discovery signals collected | Exact count |
| Not reported | Short status rows only |

## 2. Problem Evidence

Top 1-5 user pain voices. Do not invent missing rows.

| Rank | Pain theme | Source type | Source link | English original voice | Chinese translation | User scenario | Insight |
|---:|---|---|---|---|---|---|---|

## 3. Existing Workarounds

| Workaround | User behavior | Friction created | Evidence link | Insight |
|---|---|---|---|---|

Examples: manual workflow, spreadsheet, outsourcing, DIY hardware, multiple apps, notes, reminders, service provider, adjacent product.

## 4. Willingness-to-Pay Signals

| Signal type | Product/source | Evidence | Amount/price/count | Link | Boundary |
|---|---|---|---|---|---|

Examples: Kickstarter backing, Indiegogo preorder, paid app, paid SaaS, subscription, waitlist, paid community, purchase comment, independent-store pricing.

If none is collected, write `Payment signal not collected`.

## 5. Search and Discovery Signals

| Signal | Source | Exact observed evidence | Link | What it proves | What it does not prove |
|---|---|---|---|---|---|

Do not treat search visibility alone as purchase intent.

## 6. Substitute and Competitor Map

| Type | Name/process | Why users use it | Why it falls short | Evidence link | Insight |
|---|---|---|---|---|---|

Types: direct competitor, indirect competitor, adjacent product, manual workaround, service substitute, behavior substitute.

## 7. Counter-evidence (mandatory)

| Counter-signal | Evidence | Source link | Effect on verdict |
|---|---|---|---|

Examples:
- Failed crowdfunding for the same or near-neighbor idea.
- Abandoned open-source projects targeting the same pain.
- High-volume comments saying current workarounds are good enough.
- Editorial / community verdicts that prior attempts at the category failed.

If a real counter-evidence search returns nothing:
`Counter-evidence search performed; none found. | Queries: <list> | <links to empty search-result pages> | Verdict gating still applies.`

The verdict cannot be `supported` if this section is empty without that explicit note.

## 8. Demand Reality Insights

| Rank | Insight | Supporting evidence | Evidence boundary |
|---:|---|---|---|

Insights must cite rows from problem evidence, workarounds, payment signals, search signals, or substitutes.

## 9. Demand Verdict

Natural-language verdict (factual, not a score) plus the structured YAML block from [`../../vibe-product-demand-research/references/output-format.md`](../../vibe-product-demand-research/references/output-format.md).

`status: supported` requires:

- Non-empty Counter-evidence section AND `counter_evidence_addressed: true`.
- `evidence_counts.voices > 0` and `evidence_counts.workarounds > 0`.

Example natural-language verdicts:

- `Demand is supported by repeated user complaints across Reddit and YouTube, three independent workarounds, and one funded crowdfunding signal. Counter-evidence found no comparable failed campaigns in the last 24 months.`
- `Demand is visible, but payment evidence is not collected. Verdict: partially_supported.`
- `Current evidence is mostly media attention; user-pain evidence is thin. Verdict: insufficient.`
- `Current sample too small; demand judgment withheld.`

## 10. Not Reported

| Item | Status |
|---|---|

Examples:

- `Market size | Current sample too small; not reported`
- `Search volume | Not collected`
- `Payment signal | Payment signal not collected`
- `Retention | Not collected`
