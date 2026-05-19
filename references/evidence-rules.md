# Evidence Rules

Single source of truth for evidence integrity across all skills in this repo. The router and every sub-skill (`amazon-voc-research`, `emerging-demand-research`, `method-two-crawler-pipeline`) reference this file. Do not restate these rules inside individual `SKILL.md` files — link here instead.

## Banned language in user-facing reports

Do not use any of the following as substitutes for evidence:

- Vague ratings: `high`, `medium`, `low`, `medium-high`, `relatively high`, `good`, `bad`, `strong`, `weak`.
- Vague counts: `many`, `several`, `a few`, `most`, `a lot of`.
- Placeholder values: `X`, `xx`, `xx%`, `N/A` (without an explicit reason).
- Internal tool excuses: do not write `no API available`, `couldn't scrape`, `rate-limited` in the user-facing report. Use a neutral data status instead (see below).

Comparative descriptors (`more`, `fewer`, `higher than X`) are allowed **only** when the compared items are both shown in the report with concrete values.

## Required data-status vocabulary

When a layer cannot be filled, use exactly one of:

- `Not collected` — work was not attempted this run.
- `Not visible on page` — the page exists but the field is hidden / missing.
- `No verifiable link found` — claim exists but cannot be sourced.
- `Current sample too small; not reported` — collected but below threshold for a claim.
- `Collected sample does not support a trend claim` — used when refusing a longitudinal claim from a one-shot snapshot.

## Link integrity

- Every product, brand, review, voice row, workaround, payment signal, search/discovery signal, and competitor must include a working link when available.
- No placeholder URLs (`#`, `example.com`, `TBD`, empty `href`).
- Amazon search-result pages are not equivalent to product pages. Label search entries as `Amazon search entry` if no direct product page is collected.
- Prefer direct product pages over search/category pages; prefer customer reviews over editorial reviews; prefer original-source quotes over paraphrase.

## Numbers

- Use exact collected values only.
- Do not output market size, exact sales, BSR history, search volume, growth rate, or any trend claim unless the collected data directly supports it.
- A single-page snapshot is a snapshot, not a trend.
- If precision is unavailable, use a data-status string; do not invent precision.

## Quote handling

- Quote source-faithful excerpts only. Keep them short enough to comply with fair-use / copyright limits.
- Put interpretation in the `insight` field, not in the original-voice field.
- For non-English voices, include both the original-language quote and a Chinese translation when useful.

## Disconfirming evidence (required)

Every report must include a `Counter-evidence` layer. The verdict cannot be `supported` until this layer is non-empty and addressed.

Counter-evidence includes:

- Dead or discontinued products in the same category.
- Failed crowdfunding campaigns for similar ideas.
- Low-rated substitutes that already cover the proposed use case.
- Long-abandoned open-source / community projects targeting the same problem.
- User comments explicitly saying the problem isn't worth solving / a workaround is already good enough.

If counter-evidence cannot be found after a real attempt, write `Counter-evidence search performed; none found.` plus the queries used. Do **not** leave the layer empty.

## Verdict requirements

Every report ends with both:

1. A factual natural-language verdict (see `skills/vibe-product-demand-research/references/output-format.md`).
2. A structured YAML block (schema defined in the same file).

`status: supported` requires:

- `counter_evidence_addressed: true`
- At least one evidence count > 0 in each of the layers the route requires (e.g. emerging route requires `voices` and `workarounds`; existing route requires `reviews`).
- No critical layer marked in `missing_layers` without explanation.

Otherwise downgrade to `partially_supported`, `insufficient`, or `contradicted`.
