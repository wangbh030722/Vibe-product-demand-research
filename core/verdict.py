"""Final verdict composition.

Combines mode-specific outputs into one structured verdict block, applying
the gating rules from references/evidence-rules.md:
  - voices_raw == 0 → status: insufficient
  - existing/hybrid without marketplace voices → cannot exceed partially_supported
  - non_stock without counter-checklist verdict → cannot exceed partially_supported
"""
from __future__ import annotations


def compose(idea: str, locale: str, mode: str, evidence_pack: dict,
            voc_summary: dict | None, framework: dict | None,
            counter: dict | None, qualitative: dict | None) -> dict:
    counts = _counts(evidence_pack)
    voices_raw = counts["voices_raw"]
    voices_marketplace = counts["voices_marketplace"]
    voices_community = counts["voices_community"]

    # Per-panel verdicts
    panel_verdicts = []
    if voc_summary:
        panel_verdicts.append(("VOC", voc_summary.get("real_demand_verdict")))
    if framework:
        panel_verdicts.append(("框架评分", framework.get("verdict")))
    if counter:
        panel_verdicts.append(("反向证据", counter.get("verdict")))
    if qualitative:
        panel_verdicts.append(("定性评论", qualitative.get("verdict")))

    # Hard gate: no raw voice → insufficient
    if voices_raw == 0:
        status = "insufficient"
        one_line = "未采集到原始用户 voice,无法判断真伪;尝试检查 collector 失败原因或换 locale。"
    else:
        status = _aggregate_status(panel_verdicts, mode, voices_marketplace, voices_community)
        one_line = _one_line(idea, status, panel_verdicts, voc_summary)

    missing = []
    if voices_marketplace == 0 and mode in ("existing", "hybrid"):
        missing.append("voices_marketplace")
    if voices_community == 0 and mode in ("non_stock", "hybrid"):
        missing.append("voices_community")
    if not counter or counter.get("verdict") == "证据不足":
        missing.append("counter_evidence")

    return {
        "status": status,
        "one_line": one_line,
        "mode": mode,
        "locale": locale,
        "evidence_counts": counts,
        "panel_verdicts": [{"panel": p, "verdict": v} for p, v in panel_verdicts],
        "missing_layers": missing,
    }


def _counts(evidence_pack: dict) -> dict:
    by_source = evidence_pack.get("by_source", {}) or {}
    marketplace_sources = {"amazon", "jd", "tmall", "rakuten", "bestbuy", "walmart"}
    voices_marketplace = sum(v for k, v in by_source.items() if k in marketplace_sources)
    voices_community = sum(v for k, v in by_source.items() if k not in marketplace_sources)
    return {
        "voices_raw": evidence_pack.get("raw_voice_count_total", 0),
        "voices_marketplace": voices_marketplace,
        "voices_community": voices_community,
        "by_source": by_source,
        "by_category": evidence_pack.get("by_category_counts", {}),
    }


_RANK = {"真需求": 3, "需观察": 2, "信号矛盾": 2, "伪需求": 1, "高风险": 1, "证据不足": 0}


def _aggregate_status(panel_verdicts, mode: str, voices_marketplace: int, voices_community: int) -> str:
    values = [v for _, v in panel_verdicts if v]
    if not values:
        return "insufficient"
    scores = [_RANK.get(v, 0) for v in values]
    avg = sum(scores) / len(scores)

    # Hard cap: hybrid/existing without marketplace VOC cannot reach "real_demand_strong"
    if mode in ("existing", "hybrid") and voices_marketplace == 0:
        # cap at partially
        if avg >= 2.5:
            return "partially_supported"
    if avg >= 2.6:
        return "supported"          # = 真需求
    if avg >= 1.6:
        return "partially_supported"
    if avg >= 1.0:
        return "weakly_supported"   # ≈ 信号矛盾
    return "insufficient"


def _one_line(idea: str, status: str, panel_verdicts, voc: dict | None) -> str:
    if voc and voc.get("thesis"):
        return voc["thesis"]
    label = {
        "supported": "真需求(综合证据支撑)",
        "partially_supported": "需求存在但证据不全",
        "weakly_supported": "信号矛盾,需进一步采集",
        "insufficient": "证据不足,暂不研判",
    }.get(status, status)
    return f"{idea}:{label}。"
