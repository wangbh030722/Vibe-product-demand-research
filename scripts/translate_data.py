#!/usr/bin/env python3
"""
Backfill English (*_en) fields into a category-research data JSON so the
report's CN/EN toggle shows translated content.

The base fields stay Chinese (default UI lang = zh). We add <field>_en next
to each translatable field. Voice titles are already English → title_en = title.

Usage:
  python scripts/translate_data.py data/health-ring.json          # in place
  python scripts/translate_data.py --all                          # every data/*.json
  python scripts/translate_data.py data/health-ring.json --dry-run

Env: OPENAI_* via .env (same as the rest of the pipeline).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from llm_client import chat_json  # type: ignore

# Which fields get translated, per object location.
# We send the LLM a compact map of {path: chinese_text} and get back English.


def collect_strings(data: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    m = data.get("meta", {})
    for f in ("idea", "thesis", "deck"):
        if m.get(f): out[f"meta.{f}"] = m[f]
    v = data.get("verdict", {})
    if v.get("rationale"): out["verdict.rationale"] = v["rationale"]
    for i, kf in enumerate(v.get("key_findings", [])):
        out[f"verdict.key_findings.{i}"] = kf
    for i, p in enumerate(data.get("players", [])):
        if p.get("name"): out[f"players.{i}.name"] = p["name"]
        if p.get("summary"): out[f"players.{i}.summary"] = p["summary"]
    for i, t in enumerate(data.get("themes", [])):
        if t.get("label"): out[f"themes.{i}.label"] = t["label"]
        if t.get("summary"): out[f"themes.{i}.summary"] = t["summary"]
    o = data.get("opportunity", {})
    if o.get("label"): out["opportunity.label"] = o["label"]
    if o.get("summary"): out["opportunity.summary"] = o["summary"]
    si = data.get("section_insights", {})
    for k in ("market", "user", "competitive", "opportunity", "risk"):
        if si.get(k): out[f"section_insights.{k}"] = si[k]
    for i, p in enumerate(data.get("paths", [])):
        for f in ("label", "core", "description", "hypothesis", "evidence", "risk"):
            if p.get(f): out[f"paths.{i}.{f}"] = p[f]
        for j, q in enumerate(p.get("open_questions", []) or []):
            if q: out[f"paths.{i}.open_questions.{j}"] = q
    ud = data.get("user_demand", {})
    if ud.get("jtbd"): out["user_demand.jtbd"] = ud["jtbd"]
    if ud.get("wtp"):  out["user_demand.wtp"] = ud["wtp"]
    for grp, fields in (("scenarios", ("name", "summary")), ("personas", ("name", "summary")),
                        ("unmet_needs", ("need", "summary")), ("workarounds", ("approach", "summary"))):
        for i, item in enumerate(ud.get(grp, []) or []):
            for f in fields:
                if item.get(f): out[f"user_demand.{grp}.{i}.{f}"] = item[f]
    for i, r in enumerate(data.get("risks", [])):
        for f in ("title", "scenario", "mitigation"):
            if r.get(f): out[f"risks.{i}.{f}"] = r[f]
    for i, fl in enumerate(data.get("failures", [])):
        for f in ("name", "what", "lesson"):
            if fl.get(f): out[f"failures.{i}.{f}"] = fl[f]
    return out


def apply_translations(data: dict, tr: dict[str, str]) -> None:
    def setp(path: str, val: str):
        parts = path.split(".")
        # locate
        if parts[0] == "meta":
            data["meta"][parts[1] + "_en"] = val
        elif parts[0] == "verdict" and parts[1] == "rationale":
            data["verdict"]["rationale_en"] = val
        elif parts[0] == "verdict" and parts[1] == "key_findings":
            data["verdict"].setdefault("key_findings_en", [])
            idx = int(parts[2])
            kf = data["verdict"]["key_findings_en"]
            while len(kf) <= idx: kf.append("")
            kf[idx] = val
        elif parts[0] == "opportunity":
            data["opportunity"][parts[1] + "_en"] = val
        elif parts[0] == "section_insights":
            data.setdefault("section_insights", {})[parts[1] + "_en"] = val
        elif parts[0] == "paths" and len(parts) == 4 and parts[2] == "open_questions":
            p = data["paths"][int(parts[1])]; p.setdefault("open_questions_en", [])
            j = int(parts[3]); oq = p["open_questions_en"]
            while len(oq) <= j: oq.append("")
            oq[j] = val
        elif parts[0] == "user_demand":
            ud = data.setdefault("user_demand", {})
            if len(parts) == 2:
                ud[parts[1] + "_en"] = val
            elif len(parts) == 4:
                arr = ud.get(parts[1], []); idx = int(parts[2])
                if idx < len(arr): arr[idx][parts[3] + "_en"] = val
        elif parts[0] in ("players", "themes", "paths", "risks", "failures"):
            arr = data[parts[0]]; idx = int(parts[1]); field = parts[2]
            if idx < len(arr): arr[idx][field + "_en"] = val
    for path, val in tr.items():
        if val: setp(path, val)


def translate(data: dict) -> dict:
    strings = collect_strings(data)
    if not strings:
        return {}
    sys_msg = ("You are a professional EN translator for market-research reports. "
               "Translate each Chinese value to natural, concise English. "
               "Keep product/brand names as-is. Keep technical terms (FDA, RAG, "
               "prompt, token) untranslated. Output STRICT JSON only: same keys, "
               "English values.")
    user = ("Translate the values of this JSON map to English. Return a JSON "
            "object with the SAME keys and translated string values:\n\n"
            + json.dumps(strings, ensure_ascii=False, indent=1))
    res = chat_json(sys_msg, user, temperature=0.2)
    return res


def translate_voice_titles(data: dict) -> None:
    """Add title_zh (Chinese) to each voice — the subtle subtitle shown under the
    English original when the report is in zh mode. Batched, best-effort."""
    voices = data.get("voices", [])
    todo = [(i, v["title"]) for i, v in enumerate(voices)
            if v.get("title") and not v.get("title_zh")]
    if not todo:
        return
    sys_msg = ("You translate short English Reddit post titles into natural, "
               "concise 简体中文. Keep brand/product names in English. Do not add "
               "quotes or commentary. Output STRICT JSON only: same keys, Chinese "
               "string values.")
    CHUNK = 60
    for s in range(0, len(todo), CHUNK):
        part = {str(i): t for i, t in todo[s:s + CHUNK]}
        user = ("Translate each English title to Chinese. Return a JSON object "
                "with the SAME keys:\n\n" + json.dumps(part, ensure_ascii=False))
        try:
            res = chat_json(sys_msg, user, temperature=0.2, max_tokens=6000)
        except Exception as e:
            print(f"  ! voice-title zh translate skipped: {e}", file=sys.stderr)
            continue
        for k, zh in (res or {}).items():
            try:
                idx = int(k)
            except (TypeError, ValueError):
                continue
            if 0 <= idx < len(voices) and zh:
                voices[idx]["title_zh"] = str(zh).strip()


def process(path: Path, dry: bool) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    print(f"translating {path.name} ...")
    tr = translate(data)
    if not tr:
        print("  (nothing to translate)")
        return
    apply_translations(data, tr)
    # voice titles are already English (title_en = title), and we add a Chinese
    # subtitle (title_zh) for the zh-mode subtitle under each voice.
    for v in data.get("voices", []):
        if v.get("title") and "title_en" not in v:
            v["title_en"] = v["title"]
    translate_voice_titles(data)
    if dry:
        print(json.dumps(data["meta"], ensure_ascii=False, indent=2))
        return
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✓ wrote {len(tr)} translations into {path.name}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.all:
        files = sorted((ROOT / "data").glob("*.json"))
    elif args.path:
        files = [Path(args.path)]
    else:
        ap.print_help(); return 2
    for f in files:
        process(f, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
