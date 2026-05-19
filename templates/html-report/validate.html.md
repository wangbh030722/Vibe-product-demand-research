# HTML Report Validator

The template at [`index.html`](index.html) ships an inline validator that runs in the browser console on every report load. It does not block rendering — it logs warnings so reviewers see the same red flags whether they open the report locally or share it.

## What it checks

1. **Placeholder links**
   `<a href>` matching any of: empty string, `#`, `example.com`, `placeholder` (any case), URLs ending in `...`, or bare-domain forms like `https://reddit.com/` / `https://youtube.com/` / `https://amazon.com/`.

2. **Empty "collected" sections**
   Any `<section data-collected="1">` whose body contains zero `<tbody><tr>`, zero `article.card`, and zero direct children of `.grid`. If you mark a section as collected, it must have evidence rows.

3. **Missing or malformed verdict block**
   The `<script id="verdict" type="application/json">` block is required. Missing block → warning. JSON parse failure → warning with the parse error.

All warnings are prefixed `[demand-report] warn:` so they're easy to grep in the console output.

## What it does not check

- It does not fetch links or verify that pages still return 200. Use a separate link checker for that.
- It does not validate the verdict YAML against the schema field-by-field. The agent must produce a well-formed block; the validator only confirms it exists and parses.
- It does not enforce the route-section contract (e.g. "hybrid reports must have Conflict Resolution"). That's the agent's responsibility — see [`../../skills/vibe-product-demand-research/references/output-format.md`](../../skills/vibe-product-demand-research/references/output-format.md).

## Suppressing a warning

Don't suppress. Fix the underlying issue:

- Placeholder link → collect the real source or remove the row.
- Empty collected section → set `data-collected="0"` (the section will then hide via CSS), or fill the rows.
- Missing verdict → emit the verdict block; it's required by the output format.

## CLI alternative (optional)

For automated checks in CI, the same rules can be run with a tiny Node script using `cheerio` or `linkedom`. Not included in this repo. Keep the validator inline so the canonical HTML is self-checking when opened anywhere.
