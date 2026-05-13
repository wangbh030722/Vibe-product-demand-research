# Output Format

Use this structure for the final product demand research output.

## Conversation Summary

Keep the chat response concise:

1. Route decision.
2. 3-5 most important evidence-backed insights.
3. Demand verdict.
4. Link/path to the generated HTML report.

Do not paste the entire long report into chat if an HTML report is created.

## HTML Report Sections

The HTML report should use this order:

1. **Hero / Verdict**
   - Product idea/category.
   - Route: Existing / Emerging / Hybrid.
   - One-line demand verdict.
   - Evidence boundary chips.

2. **Evidence Sources**
   - Only real collected sources.
   - Each source card must include a working link.
   - No fake links, no placeholder URLs.

3. **Product or Substitute Snapshot**
   - Existing market: product/competitor cards.
   - Emerging market: substitute/workaround cards.
   - Hybrid market: show both when collected.

4. **Voice Evidence**
   - Positive/repeated demand voices.
   - Negative/pain voices.
   - Original language plus Chinese translation when useful.
   - Every row needs a source link.

5. **Insight Grid**
   - Evidence-backed insights only.
   - Each insight links back to source rows or source cards.

6. **Demand Verdict**
   - Factual conclusion, not a score.
   - Include what the evidence supports and what it does not support.

7. **Evidence Boundary**
   - Only include missing evidence that affects the verdict.

## HTML Style

Use a clean Nothing-inspired visual style:

- Background: off-white or near-black.
- Text: black/white with one restrained accent color.
- Layout: spacious but dense, with thin borders, grid lines, and compact evidence cards.
- Typography: strong hierarchy, uppercase section labels, tabular-looking metrics, no decorative gradients.
- Motion: subtle fade/slide-in, scanline or grid shimmer, hover lift on cards, prefers-reduced-motion support.
- Navigation: sticky mini index or top bar when useful.

Avoid:

- Fake dashboard charts.
- Decorative blobs/orbs.
- Marketing hero copy.
- Empty sections.
- Placeholder links.
- Large unexplained scores.

## HTML Delivery Rules

- Produce a self-contained `.html` file when the environment supports file output.
- Use inline CSS and small inline JavaScript only.
- Do not require a build step.
- Ensure all external links are real source links.
- If evidence is insufficient for a section, omit that section rather than showing an empty block.
