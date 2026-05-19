"""Non-stock mode: 3 parallel analyses.

  - framework_score: 5-dimension structured score
  - counter_checklist: historical failure cases + are we repeating their premises
  - qualitative_review: AI-written critique (clearly labeled subjective)

All three accept the same inputs (idea + locale + any evidence pack). They run
independently so the UI can render them as they complete or hide a column.
"""
from __future__ import annotations

import json
from . import llm


# ----------------------------------------------------------------------
# 1. Structured 5-dimension scoring
# ----------------------------------------------------------------------
DIMENSIONS = [
    ("jtbd_exists", "Job-to-be-done 是否真实存在,且足够"),
    ("workaround_present", "是否能观察到用户的 workaround / 替代行为"),
    ("analog_validation", "是否有相邻 / 类比产品验证过类似需求"),
    ("payment_signal", "是否有付费信号(预购 / 订阅 / 高价替代品)"),
    ("failure_conditions", "是否能讲清这个想法的失败条件 / 何时不该做"),
]


def framework_score(idea: str, locale: str, evidence_pack: dict | None = None) -> dict:
    if not llm.available():
        return {
            "ok": False, "via": "no-llm",
            "dimensions": [{"key": k, "label": l, "score": None,
                            "reasoning": "(LLM 未启用)"} for k, l in DIMENSIONS],
            "overall": None,
            "verdict": "证据不足",
        }
    excerpts = _evidence_summary(evidence_pack)
    out = llm.call(
        system=(
            "You are a hard-edged demand-research analyst. You score product "
            "ideas across 5 dimensions, 0-3 each. You favor specific reasoning "
            "over generic optimism. Return JSON only, in Chinese (except "
            "preserved English source quotes)."
        ),
        prompt=f"""产品想法: {idea!r}
目标市场: {locale}

参考的原始 voice 摘要(可能为空):
{excerpts}

按以下 5 个维度各给 0-3 分(0=完全没有 / 3=非常充分),每个维度写一句中文 reasoning。

维度:
{json.dumps(DIMENSIONS, ensure_ascii=False, indent=2)}

输出 JSON:
{{
  "dimensions": [
    {{ "key": "jtbd_exists", "score": <0-3>, "reasoning": "中文一句" }},
    ...每个维度一条
  ],
  "overall": <0-15 总分>,
  "verdict": "真需求" | "伪需求" | "证据不足" | "信号矛盾"
}}

约束:
- 不允许 reasoning 出现 "感觉""可能""或许""大概"——必须用具体的例子或者反例。
- 如果某维度没有任何证据,score 给 0 而不是猜。
- 只返回 JSON,无 markdown 围栏。""",
        max_tokens=1200,
        expect_json=True,
    )
    if out.get("json"):
        return {"ok": True, "via": "llm", **out["json"]}
    return {"ok": False, "via": "llm-fail", "error": out.get("error"),
            "dimensions": [], "overall": None, "verdict": "证据不足"}


# ----------------------------------------------------------------------
# 2. Counter-evidence checklist (historical failures)
# ----------------------------------------------------------------------
def counter_checklist(idea: str, locale: str, evidence_pack: dict | None = None) -> dict:
    if not llm.available():
        return {"ok": False, "via": "no-llm",
                "items": [],
                "premise_repeat": "(LLM 未启用,无法分析前提复用)"}
    out = llm.call(
        system=(
            "You are a contrarian researcher. Your job is to NOT prove the "
            "product can succeed — only to surface what could make it fail. "
            "You name specific dead products, failed companies, and shut-down "
            "projects from the past decade. Return JSON, Chinese narrative."
        ),
        prompt=f"""产品想法: {idea!r}
目标市场: {locale}

请列出 4-7 个**具体历史失败案例**或反向信号,并对每条评估"本产品是否在复用同样的失败前提"。

输出 JSON:
{{
  "items": [
    {{
      "case": "产品/公司名(具体的,不要'某些产品')",
      "year": "<年份或区间>",
      "why_failed": "中文一句",
      "shared_premise_with_idea": true | false,
      "premise_detail": "如果 true,这个前提是什么"
    }}
  ],
  "premise_repeat_summary": "一句中文:本产品在哪些前提上重蹈覆辙;若都不在则点明区别。",
  "verdict": "真需求" | "伪需求" | "证据不足" | "高风险"
}}

约束:
- case 必须是真实历史产品/项目(Humane AI Pin、Google Glass、Juicero、Quibi、Vine、Theranos 等都是合格)。
- 不要给抽象的"市场没准备好"。给具体的失败模式。
- 只返回 JSON。""",
        max_tokens=1500,
        expect_json=True,
    )
    if out.get("json"):
        return {"ok": True, "via": "llm", **out["json"]}
    return {"ok": False, "via": "llm-fail", "error": out.get("error"),
            "items": [], "premise_repeat_summary": "", "verdict": "证据不足"}


# ----------------------------------------------------------------------
# 3. AI qualitative review (explicitly subjective)
# ----------------------------------------------------------------------
def qualitative_review(idea: str, locale: str, evidence_pack: dict | None = None) -> dict:
    if not llm.available():
        return {"ok": False, "via": "no-llm",
                "strengths": [], "weaknesses": [], "founder_pitch_red_flags": [],
                "verdict": "证据不足"}
    out = llm.call(
        system=(
            "You are a senior product critic. You write opinionated qualitative "
            "reviews. You ALWAYS label your output as subjective. You read between "
            "the lines of founder pitches and flag rhetorical patterns. Return JSON, "
            "Chinese narrative."
        ),
        prompt=f"""产品想法: {idea!r}
目标市场: {locale}

输出 JSON:
{{
  "strengths": ["3-5 条中文,每条一句,有具体性"],
  "weaknesses": ["3-5 条中文,每条一句"],
  "founder_pitch_red_flags": [
    "如果这个产品提出来时常见的话术陷阱,3-5 条。例如'AI 原生''重新定义体验''下一个 iPhone''X 还没做到的事我们能做到'。"
  ],
  "what_would_change_your_mind": "一句中文:什么样的具体证据会让你的判断翻转。",
  "verdict": "真需求" | "伪需求" | "证据不足" | "需观察",
  "subjective_disclaimer": "本列输出基于 LLM 的定性判断,不能作为独立证据。"
}}

只返回 JSON。""",
        max_tokens=1500,
        expect_json=True,
    )
    if out.get("json"):
        return {"ok": True, "via": "llm", **out["json"]}
    return {"ok": False, "via": "llm-fail", "error": out.get("error"),
            "strengths": [], "weaknesses": [], "founder_pitch_red_flags": [],
            "what_would_change_your_mind": "", "verdict": "证据不足",
            "subjective_disclaimer": ""}


# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------
def _evidence_summary(evidence_pack: dict | None) -> str:
    if not evidence_pack:
        return "(无)"
    by_cat = evidence_pack.get("top_per_category", {})
    if not by_cat:
        return f"raw_voice_count={evidence_pack.get('raw_voice_count_total', 0)},但未分类。"
    lines = [f"raw_voice_count={evidence_pack.get('raw_voice_count_total', 0)}"]
    for cat in ("pain", "positive", "counter_evidence", "workaround"):
        rows = by_cat.get(cat, [])
        if not rows:
            continue
        lines.append(f"\n[{cat} top {min(3, len(rows))}]")
        for r in rows[:3]:
            ex = (r.get("text_excerpt") or "")[:180].replace("\n", " ")
            lines.append(f"  - score={r.get('score')} | {ex}")
    return "\n".join(lines)
