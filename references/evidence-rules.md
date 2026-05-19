# Evidence Rules

Single source of truth for evidence integrity across all skills in this repo. The router and every sub-skill (`amazon-voc-research`, `emerging-demand-research`, `method-two-crawler-pipeline`) reference this file. Do not restate these rules inside individual `SKILL.md` files — link here instead.

## Source class: raw voice vs editorial (hard distinction)

Demand research is a primary-source artifact. Editorial coverage is a secondary signal at best. The two are tracked in **separate counters** and gated separately.

### Raw voice (the only thing that counts as `voices`)

A row qualifies as raw voice **only if all four** are true:

1. **Primary user platform** — Reddit / YouTube comments / X / Quora / Hacker News / Discord-or-forum / 小红书 / B站 / 知乎 / 微博 / 抖音 / TikTok / marketplace review (Amazon, 京东, 天猫, Best Buy, Walmart, Target, App Store, Play Store, Chrome Web Store) / crowdfunding-campaign comments / vendor-page reviews.
2. **Identifiable poster** — username, handle, or anonymized-but-stable reviewer ID. "Some users" / "many people" does not qualify.
3. **Permalink to the post or comment** — not the platform home page, not a search result.
4. **Verbatim quote** — original-language text, source-faithful. Paraphrase belongs in the `insight` field, not in the voice field.

A marketplace product page that exposes review themes with counts (e.g. Best Buy theme tags) counts as **one** voice row, not as N.

### Editorial signals (separate counter)

Anything written by a journalist, analyst, blogger, reviewer-site, post-mortem author, or industry-newsletter writer about the product. Useful, but downstream — it cites the same user voices a few hops removed. Editorial gives you the shape of the conversation; it does not prove the conversation exists.

Editorial rows **cannot** count toward `evidence_counts.voices`. They count toward `evidence_counts.editorial_signals`.

### Route-specific minimums

| Route | Required raw voice for `partially_supported` | Required for `supported` |
|---|---|---|
| existing | ≥ 5 marketplace customer reviews with verbatim quotes and permalinks | ≥ 12, drawn from ≥ 2 marketplaces or marketplace + community |
| emerging | ≥ 5 community-post voices across ≥ 2 independent communities | ≥ 12, across ≥ 3 communities, with ≥ 3 distinct workarounds attached |
| hybrid | both rows above | both rows above |

If raw voice cannot reach these minimums after a real collection attempt, **status must be `insufficient`** regardless of how strong the editorial pile looks.

### Auto-downgrade and crawler-pipeline fallback

If two or more direct fetches to primary user platforms fail in `collection_mode: standard` (anti-bot block, login required, host unreachable):

1. Record the failure as a `data-status: Not collected — host blocked` line.
2. Switch `collection_mode` to `crawler-pipeline` and try again, OR
3. If crawler-pipeline is unavailable in this environment, emit the verdict as `insufficient` with `missing_layers: [raw_voice]` and explicitly recommend re-running under crawler-pipeline mode.

Standard mode is editorial-dominant by nature (WebSearch indexes prefer it). Do not let an editorial-heavy collection masquerade as evidence-backed demand research.

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
