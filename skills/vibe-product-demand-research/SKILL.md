---
name: vibe-product-demand-research
description: Route and synthesize product demand validation research for existing Amazon/retail markets, emerging markets, new product ideas, non-obvious categories, potential market demand, product-market evidence, user pain validation, workaround analysis, willingness-to-pay signals, and demand reality judgments. Use when the user asks whether a product demand is real, whether a product idea has a market, whether a category is worth researching, or which demand-research path to use.
---

# Vibe Product Demand Research

## Purpose

Router + synthesis layer for product demand validation. The goal is to judge whether a product demand is real based on evidence, not to produce generic market advice.

Sub-skills:

- `amazon-voc-research` — mature categories with retail review coverage.
- `emerging-demand-research` — new categories with pain / workaround / willingness-to-pay signals.
- `method-two-crawler-pipeline` — collection mode for cost-constrained or API-blocked runs (modifier, not a separate market type).

Shared rules:

- Evidence integrity: see [`references/evidence-rules.md`](../../references/evidence-rules.md). All evidence-language, link-integrity, counter-evidence, and verdict requirements live there. Do not restate them here.
- Output format: see [`references/output-format.md`](references/output-format.md).
- HTML style: parameters are defined in [`templates/html-report/index.html`](../../templates/html-report/index.html) via CSS custom properties (`--bg`, `--accent`, `--type-scale`, etc.). Do not prescribe visual style in prose; reference the template tokens instead.

## Required Inputs

Before routing, collect or assume:

- `product_idea` — short description of the product / use case.
- `target_market` — one of `US | CN | JP | EU | global | other:<code>`. Required. Drives platform selection.
- `budget_mode` — `standard` (default) or `crawler-pipeline` (when the user says "no paid APIs", "cheap", "self-host", or when the major retail layer for the target market is blocked).

If `target_market` is missing, ask the user once, then proceed.

## Routing Workflow

### Step 1 — Quantitative diagnosis

Run a fast scan and count the following signals before declaring a route:

| Signal | Threshold | Implies |
|---|---|---|
| Direct product hits on the relevant marketplace's first 2 result pages (Amazon for US, 京东/天猫 for CN, etc.) | ≥ 5 distinct listings AND combined visible reviews ≥ 200 | Existing-market candidate |
| Same pain phrase appearing across independent communities (Reddit / YouTube / forums / niche communities) | ≥ 3 distinct sources, each with ≥ 1 organic discussion thread | Emerging-market candidate |
| Both rows above satisfied | — | Hybrid |
| Neither row satisfied after a real scan | — | `insufficient` — return early; do not fabricate a route |

`budget_mode = crawler-pipeline` is **orthogonal** to the route. It stacks on whichever main route was chosen.

### Step 2 — Output the routing token

Output exactly one block:

```yaml
route: existing | emerging | hybrid | insufficient
collection_mode: standard | crawler-pipeline
target_market: <code>
rationale: <one short sentence citing the counts that satisfied the threshold>
```

### Step 3 — Pre-research collection plan

Before any deep collection, output a plan:

```yaml
collection_plan:
  platforms: [reddit, youtube, product_hunt, amazon, ...]   # adjusted by target_market
  sample_targets:
    voices: 12
    workarounds: 5
    payment_signals: 3
    counter_evidence: 3
  time_budget_minutes: 20
```

Platform list is locale-aware. Examples:

- `target_market: US` → reddit, youtube, x, hacker_news, amazon, best_buy, walmart, target, product_hunt, kickstarter, indiegogo.
- `target_market: CN` → 小红书, 什么值得买, B站, 知乎, 京东, 天猫, 淘宝, 微博, 抖音.
- `target_market: JP` → twitter_jp, amazon_jp, 価格.com, 楽天, note, makuake.

If `collection_mode = crawler-pipeline`, follow [`../method-two-crawler-pipeline/SKILL.md`](../method-two-crawler-pipeline/SKILL.md) for the collector flow regardless of route.

Reconcile planned vs actual in the final `Collection Summary`.

### Step 4 — Run the route

- `existing` → follow [`../amazon-voc-research/SKILL.md`](../amazon-voc-research/SKILL.md).
- `emerging` → follow [`../emerging-demand-research/SKILL.md`](../emerging-demand-research/SKILL.md).
- `hybrid` → run both, then synthesize per the next section.

### Step 5 — Synthesize and emit reports

Output formats and required layers are defined in [`references/output-format.md`](references/output-format.md), including:

- Required evidence layers per route.
- The structured YAML verdict block.
- Conflict-resolution section (hybrid only).
- HTML report shape (sections gated by `data-route`).

## Hybrid: Conflict Resolution (required)

When a hybrid run produces contradictions across layers (e.g. Amazon reviews suggest the feature has no demand while Reddit shows recurring requests), the report must include a `Conflict resolution` section that lists, for each contradiction:

- The two evidence rows in tension (with links).
- The most plausible explanations (saturation in old form factor vs demand for new form factor; pro vs casual segment; regional difference; etc.).
- The single piece of additional evidence that would settle it.

Without this section, hybrid verdicts cannot be `supported`; downgrade to `partially_supported`.

## Verdict

See the YAML schema and natural-language phrasing rules in [`references/output-format.md`](references/output-format.md). Counter-evidence and `status` gating rules are in [`references/evidence-rules.md`](../../references/evidence-rules.md).

## Final Output

For complete reports, output both:

1. A concise Markdown summary in the conversation: route token, collection plan reconciliation, 3-5 evidence-backed insights, the structured verdict, link to the HTML report.
2. A self-contained HTML report based on [`templates/html-report/index.html`](../../templates/html-report/index.html), with `data-route` and `data-style` set on `<body>`.

Do not paste the full long report into chat if an HTML report was produced.
