# Output Format

Defines the final shape of every product-demand research report. Evidence integrity rules (banned language, link rules, counter-evidence requirement, verdict gating) live in [`../../../references/evidence-rules.md`](../../../references/evidence-rules.md).

## Conversation Summary

Keep the chat response concise:

1. Routing token block (`route`, `collection_mode`, `target_market`, `rationale`).
2. Collection plan vs actuals — one line summarizing whether sample targets were met.
3. 3-5 evidence-backed insights, each citing a source row.
4. Structured verdict block (see below).
5. Path/link to the generated HTML report.

Do not paste the full long report into chat if an HTML report was produced.

## Structured Verdict (required)

Every report must end with this YAML block. The HTML report's verdict hero is built from it.

```yaml
verdict:
  status: supported | partially_supported | insufficient | contradicted
  route: existing | emerging | hybrid
  collection_mode: standard | crawler-pipeline
  target_market: <code>
  one_line: "<factual sentence, not a score>"
  evidence_counts:
    reviews: 0
    voices: 0
    workarounds: 0
    payment_signals: 0
    search_signals: 0
    counter_evidence: 0
  missing_layers: []          # e.g. [longitudinal_trend, payment_signals]
  counter_evidence_addressed: false
  conflicts_resolved: null    # only used when route == hybrid; true | false | null
```

`status` gating (mirrors `evidence-rules.md`):

- `supported` requires `counter_evidence_addressed: true`, route-appropriate counts > 0, and (for hybrid) `conflicts_resolved: true`.
- Otherwise downgrade to the next-highest applicable status.

Natural-language verdict examples (the `one_line` field):

- `Demand is supported by repeated user complaints, three independent workarounds, and one funded crowdfunding signal.`
- `Demand is supported by existing retail reviews, but the new use case requires separate validation.`
- `Demand is visible but payment evidence was not collected this run.`
- `Current sample too small; demand judgment withheld.`
- `Evidence contradicts: retail reviews show saturation, but community discussion shows recurring requests for a new form factor.`

## HTML Report Sections

The HTML report is generated from [`../../../templates/html-report/index.html`](../../../templates/html-report/index.html). Section visibility is driven by `<body data-route="...">`:

### Shared (all routes)

1. **Verdict Hero** — built from the structured verdict YAML. Renders status pill, route + collection_mode + target_market chips, the `one_line`, an evidence-counts row, and a `missing_layers` strip.
2. **Collection Summary** — planned vs actual platforms, sample counts, time spent, and what was not reported.
3. **Evidence Sources** — every source must have a working link. No placeholder URLs.

### Route-specific (gated by `data-route`)

| Section | existing | emerging | hybrid |
|---|---|---|---|
| Competitor Ledger | ✅ | — | ✅ |
| Listing Promise vs Review Reality | ✅ | — | ✅ |
| Top Positive Review Voices | ✅ | — | ✅ |
| Top Negative Review Voices | ✅ | — | ✅ |
| Problem Evidence / Raw User Voice | — | ✅ | ✅ |
| Existing Workarounds | — | ✅ | ✅ |
| Willingness-to-Pay Signals | — | ✅ | ✅ |
| Search & Discovery Signals | — | ✅ | ✅ |
| Substitute & Competitor Map | — | ✅ | ✅ |
| Conflict Resolution | — | — | ✅ (required) |
| Counter-evidence | ✅ | ✅ | ✅ |
| Insight Grid | ✅ | ✅ | ✅ |

### Per-section rendering rules

- Mark each section's container `data-collected="0"` if no rows were collected. CSS hides `[data-collected="0"]` so the page never shows an empty block.
- Voice rows include: original-language excerpt, Chinese translation (when useful), source type label, source link, theme, and an `insight` field.
- Every row that asserts a number or a quote must link to a source.

## HTML Style

Visual style is fully parameterized via CSS custom properties on `<body>`. Do not prescribe a visual look here in prose; pick a style token instead:

- `data-style="minimal"` — default. Restrained, near-monochrome, thin grid, subtle motion.
- `data-style="editorial"` — warmer paper background, serif display type, wider measure.
- `data-style="data-dense"` — denser grid, smaller type scale, stronger separators, no motion.

Token definitions live in [`../../../templates/html-report/index.html`](../../../templates/html-report/index.html). To add or change a style, edit the template, not this doc.

## HTML Delivery Rules

- Produce a self-contained `.html` file when the environment supports file output.
- Inline CSS + small inline JS only. No build step. No external assets.
- All external links must resolve to real sources.
- The template's inline validator logs `[demand-report] warn:` lines to the console for placeholder links, empty `data-collected="1"` sections, and a missing verdict block. Fix warnings before sharing.
