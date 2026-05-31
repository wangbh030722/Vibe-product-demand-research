"""Existing-mode VOC summarization.

Takes the cleaned evidence pack and produces:
  - 3-5 themed top voices (positive + pain)
  - 3-5 counter-evidence rows
  - 1 thesis sentence

Each themed voice keeps the verbatim original quote + permalink. The LLM
restates the theme and writes a one-line insight per row, but never invents
a quote.
"""
from __future__ import annotations

import json
from . import llm


def summarize(idea: str, evidence_pack: dict) -> dict:
    """Return summary dict suitable for the existing-market panel."""
    if not llm.available():
        return _skeleton_no_llm(idea, evidence_pack)

    # Compact: top 6 per category, just url + score + excerpt
    compact = {}
    for cat, rows in evidence_pack.get("top_per_category", {}).items():
        compact[cat] = [
            {"url": r.get("url"), "score": r.get("score"),
             "excerpt": (r.get("text_excerpt") or "")[:300]}
            for r in rows[:6]
        ]
    compact_json = json.dumps(compact, ensure_ascii=False)

    out = llm.call(
        system=(
            "You are an industry researcher. You read raw user voices from "
            "Reddit and Hacker News and produce a sharp, evidence-backed "
            "summary. You NEVER invent quotes. You quote verbatim from the "
            "excerpts you are given. Output is in Chinese for the narrative "
            "fields, with English quotes preserved as-is. Return JSON only."
        ),
        prompt=f"""产品想法: {idea!r}

下面是按类别(pain/positive/counter_evidence/workaround/payment_signal)分组的原始用户发言。每条带 url、score、英文原文片段。

```json
{compact_json}
```

请按以下结构输出 JSON,字段命名固定:

{{
  "thesis": "一句话(中文)非共识结论,必须基于上面的原话。",
  "real_demand_verdict": "真需求" | "伪需求" | "证据不足",
  "verdict_reasoning": "一句话(中文)解释为什么。",
  "top_pain": [
    {{
      "theme": "中文主题",
      "quote_en": "原话 verbatim,从上面 excerpt 里挑",
      "url": "permalink",
      "score": <int>,
      "insight": "中文一句话"
    }}
  ],  // 最多 3 条
  "top_positive": [...],  // 同结构,最多 3 条
  "counter_evidence": [...]  // 同结构,最多 3 条,从 counter_evidence 桶里选,如该桶为空可从 pain 桶里挑负面信号
}}

约束:
- 每条 quote_en 必须从给定 excerpt 复制,不允许重写或翻译。
- 不允许编造任何不在 excerpt 里的事实。
- thesis 必须是非共识的——如果一个聪明读者看了你的话立刻同意而不需要证据,就重写。
- 如果数据完全不足以判断,real_demand_verdict 直接给"证据不足",其他字段尽量保守。

只返回 JSON,不要 markdown 围栏。""",
        max_tokens=2500,
        expect_json=True,
    )

    if out.get("json"):
        return {"ok": True, "via": "llm", **out["json"]}
    return _skeleton_no_llm(idea, evidence_pack, llm_error=out.get("error") or out.get("json_error"))


def _skeleton_no_llm(idea: str, evidence_pack: dict, llm_error: str | None = None) -> dict:
    """When LLM is unavailable, surface raw top voices without summarization."""
    def top(cat, n=3):
        return [
            {"theme": cat, "quote_en": (r.get("text_excerpt") or "")[:200],
             "url": r.get("url"), "score": r.get("score"),
             "insight": "(无 LLM,未生成洞察)"}
            for r in evidence_pack.get("top_per_category", {}).get(cat, [])[:n]
        ]
    return {
        "ok": False,
        "via": "no-llm",
        "thesis": "(LLM 未启用,无法生成 thesis)",
        "real_demand_verdict": "证据不足",
        "verdict_reasoning": "ANTHROPIC_API_KEY 未配置;只能呈现原始 VOC,无法做综合判断。" + (f" 错误: {llm_error}" if llm_error else ""),
        "top_pain": top("pain"),
        "top_positive": top("positive"),
        "counter_evidence": top("counter_evidence"),
    }
