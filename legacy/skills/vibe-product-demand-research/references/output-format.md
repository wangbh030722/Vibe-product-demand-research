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
    voices_raw: 0           # primary-source user voices ONLY — see evidence-rules.md
    voices_marketplace: 0   # subset of voices_raw, from shopping platforms
    voices_community: 0     # subset of voices_raw, from Reddit/YT/forums/etc.
    workarounds: 0
    payment_signals: 0
    search_signals: 0
    counter_evidence: 0
    editorial_signals: 0    # journalism / analyst / blog / post-mortem — secondary
  missing_layers: []        # e.g. [raw_voice, longitudinal_trend]
  counter_evidence_addressed: false
  conflicts_resolved: null  # hybrid only; true | false | null
```

`status` gating (mirrors `evidence-rules.md`):

- `supported` requires `counter_evidence_addressed: true`, route-appropriate **raw voice** minimums (see evidence-rules.md table), and (for hybrid) `conflicts_resolved: true`.
- `partially_supported` requires at least the `partially_supported` raw-voice minimum AND non-empty counter-evidence.
- **`voices_raw == 0` forces `status: insufficient`**, regardless of how high `editorial_signals` is.
- If `collection_mode: standard` failed to reach raw voice, append `missing_layers: [raw_voice]` and recommend `crawler-pipeline` in the report's method note.

Natural-language verdict examples (the `one_line` field):

- `Demand is supported by repeated user complaints, three independent workarounds, and one funded crowdfunding signal.`
- `Demand is supported by existing retail reviews, but the new use case requires separate validation.`
- `Demand is visible but payment evidence was not collected this run.`
- `Current sample too small; demand judgment withheld.`
- `Evidence contradicts: retail reviews show saturation, but community discussion shows recurring requests for a new form factor.`

## Report shape: lead with the claim, not the method

A demand-research report is not a data dump. It must read like an analyst's note, not a spreadsheet export. The structure below is **mandatory ordering**:

1. **Thesis (hero)** — one or two sentences. The single non-consensus claim of this report. Built from the structured verdict YAML's `one_line` plus the status pill.
2. **Headline insights** — exactly 3–5 callout cards. Each is a sharp, falsifiable claim. Not a category description.
3. **The hinge** — the conflict-resolution section (hybrid) or the central counter-evidence finding (existing/emerging). This is the most-likely-to-be-wrong-or-right part of the report; do not hide it.
4. **Supporting evidence** — compact tables. Reader should be able to skim and skip. Voice rows, competitor ledger, workarounds, etc. live here.
5. **Counter-evidence** — featured, not buried. Often this is where the non-consensus framing comes from.
6. **Method note** — one sentence. Platforms scanned, sample sizes, what's missing. Not a section, not a table — a single line at the bottom.
7. **Sources** — last. A compact footnote-style roll. The reader should not have to wade through sources to reach insights.

`Collection Summary` is no longer a top-of-page section. It collapses into the single-sentence method note. If the reader cares about methodology details, they can read the YAML verdict block.

### Insight style (mandatory)

Headline insights must satisfy:

- **Non-consensus or sharp restatement** — if a smart industry reader would already agree with the sentence without reading the report, drop it. "Privacy is a concern" doesn't qualify. "Bystander privacy is the new asbestos — pricing it today is impossible" does.
- **Falsifiable** — name what would prove it wrong.
- **Specific** — names a product, a number, an event, or a regulatory line.

Each headline insight in the HTML report is rendered as a featured card with three fields:
- `claim` (the sentence)
- `evidence` (one-line citation, with link)
- `falsifier` (what would make this wrong)

### Bilingual rule (CN target reader)

When the report is for a Chinese-speaking reader (default unless overridden), the canonical voice is:

- All narrative, headers, callouts, insights → **Chinese**.
- All source excerpts → **English original kept verbatim**, followed by a short Chinese paraphrase only when the original is non-trivial. Do not translate every English quote — preserve the source voice.
- URLs, brand names, regulatory citations → keep in original (do not transliterate).
- Section labels in the template stay in English (`THESIS`, `INSIGHTS`, `COUNTER-EVIDENCE`) as a typographic anchor — they're labels, not body copy.

For non-CN readers, the same pattern inverts: narrative in the target language, source excerpts verbatim.

### Route-specific evidence layers (gated by `data-route`)

These remain required, but they live in the **supporting evidence** section, not at the top:

| Layer | existing | emerging | hybrid |
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
| Conflict Resolution | — | — | ✅ (the hinge, surface high) |
| Counter-evidence | ✅ | ✅ | ✅ (the hinge, surface high) |

### Per-section rendering rules

- Mark each section's container `data-collected="0"` if no rows were collected. CSS hides `[data-collected="0"]` so the page never shows an empty block.
- Voice rows include: original-language excerpt, source link, theme, an `insight` field. Chinese paraphrase only when the English is non-trivial.
- Every row that asserts a number or a quote must link to a source.
- Tables in supporting evidence use compact density (`data-density="tight"`); reader should be able to skim a 6-row table in 5 seconds.

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
