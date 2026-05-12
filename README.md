# Vibe Product Demand Research

Codex skill pack for validating whether a product demand is real.

## Skills

- `vibe-product-demand-research`: Router and synthesis layer. Decides whether a product idea should be researched as an existing market, emerging market, or hybrid market.
- `amazon-voc-research`: Existing-market VOC reference for Amazon/retail product review evidence.
- `emerging-demand-research`: Emerging-market reference for user pain, workaround, search, and willingness-to-pay evidence.

## Install

Copy the desired skill folder into your Codex skills directory:

```bash
cp -R skills/vibe-product-demand-research ~/.codex/skills/
```

For the full pack:

```bash
cp -R skills/* ~/.codex/skills/
```

Restart Codex after installation so the new skill metadata is loaded.

## Default Use

Invoke:

```text
$vibe-product-demand-research Research whether this product demand is real: <your product idea>
```

The skill will route the research to:

- Existing market: Amazon/retail VOC evidence.
- Emerging market: user pain, workaround, search, and payment evidence.
- Hybrid market: both paths with a clear evidence boundary.
