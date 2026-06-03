#!/usr/bin/env python3
"""
Local one-click web app: type an idea in a box → get the interactive report.

    make app           # or: python scripts/app.py
    → opens http://localhost:8200

No copy-paste, no terminal after launch. Uses your .env LLM key.
This is the in-process core that the hosted (Vercel) version will wrap.

Stdlib only (http.server) — no Flask/pip needed.
"""
from __future__ import annotations

import json
import re
import sys
import threading
import webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import research  # the pipeline stages
from validate_data import load_schema, validate_schema, check_cross_refs  # type: ignore

# Port/host are env-driven so the same app runs locally AND on a cloud host
# (Render/Railway/Fly set $PORT). Bind 0.0.0.0 when hosted so the platform can reach it.
import os as _os_cfg
PORT = int(_os_cfg.environ.get("PORT", "8200"))
HOST = _os_cfg.environ.get("HOST") or ("0.0.0.0" if _os_cfg.environ.get("PORT") else "127.0.0.1")


def slugify(idea: str) -> str:
    import hashlib
    s = re.sub(r"[^a-z0-9]+", "-", idea.lower()).strip("-")
    # Chinese/non-ascii ideas collapse to a short/empty slug → append a hash
    # so different ideas don't collide on the same data file.
    if len(s) < 4:
        h = hashlib.sha1(idea.encode("utf-8")).hexdigest()[:6]
        s = (s + "-" + h).strip("-") if s else "report-" + h
    return s[:40]


# --------------------------------------------------------------------------- #
# Pipeline in-process (mirrors research.py main, returns data dict)           #
# --------------------------------------------------------------------------- #

import os
import threading

# Only one research at a time (we override process-global env per request).
# Fine for friend-testing scale; serializes concurrent submits.
_PIPELINE_LOCK = threading.Lock()


def run_pipeline(idea: str, target_market: str, mode: str | None,
                 log, creds: dict | None = None, target_lang: str = "zh", emit=None) -> dict:
    creds = creds or {}
    with _PIPELINE_LOCK:
        # Apply per-request key override (falls back to .env default), restore after.
        saved = {k: os.environ.get(k) for k in ("OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL")}
        try:
            if creds.get("api_key"):    os.environ["OPENAI_API_KEY"]  = creds["api_key"]
            if creds.get("base_url"):   os.environ["OPENAI_BASE_URL"] = creds["base_url"]
            if creds.get("model"):      os.environ["OPENAI_MODEL"]    = creds["model"]
            return _run_pipeline_inner(idea, target_market, mode, log, target_lang=target_lang, emit=emit)
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


def _run_pipeline_inner(idea: str, target_market: str, mode: str | None,
                        log, target_lang: str = "zh", emit=None) -> dict:
    slug = slugify(idea)
    wd = research.work_dir(slug)

    # --- live-feed helpers: a stable per-voice id (url hash) lets the UI track the
    # SAME voice across stages — stream it raw after collect, animate it out if curate
    # drops it, fade Chinese in after translation. ---
    import hashlib as _hl, re as _re_v
    def _vid(u): return "v" + _hl.md5((u or "").encode("utf-8")).hexdigest()[:9]
    def _subof(u):
        m = _re_v.search(r"/r/([A-Za-z0-9_]+)", u or "")
        return ("r/" + m.group(1)) if m else "web"
    def _vpay(v, sent=False):
        d = {"id": _vid(v.get("url")), "title": v.get("title", ""), "url": v.get("url", ""),
             "score": int(v.get("score") or 0), "sub": _subof(v.get("url"))}
        if sent: d["sentiment"] = v.get("sentiment", "pos")
        return d
    streamed_ids: list[str] = []

    log("SCOPE", "判断市场类型 + 找数据源…")
    scope = research.stage_scope(idea, target_market, wd, False, mode or None)
    scope["_idea"] = idea
    research.save(wd / "01-scope.json", scope)

    log("COLLECT", f"联网搜索 {scope.get('subreddits')} + HN…")
    pool = research.stage_collect(scope, wd, False, log=log)

    log("COLLECT", f"已锁定 {len(pool)} 条相关 Reddit 真实评论")
    # Live feed #1: as soon as the real pool lands, stream a sample of raw voices to
    # the right panel (English originals) so the user has real content to read while
    # the slower curate/synthesis runs — then we animate the cull on top of these.
    if emit and pool:
        sample = pool[:80]
        streamed_ids = [_vid(r.get("url")) for r in sample]
        emit("voices_raw", {"voices": [_vpay(r) for r in sample]})
    # Data-driven players: pull in high-frequency brands the upfront scoping missed
    # (e.g. Loop) from the real pool BEFORE curate, so their voices get attributed.
    scope = research.stage_discover_brands(idea, scope, pool, wd, False, log=log)
    if len(pool) < 3:
        raise RuntimeError(
            f"数据源几乎没抓到内容(原始池仅 {len(pool)} 条)。"
            "常见原因:① Reddit 封了你代理出口 IP(403)② HN/网络 TLS 不稳。"
            "解决:换一个 Clash 节点(住宅 IP)再试,或用「聊天指令包」路径"
            "(让 Claude/ChatGPT 联网收集,比本地抓取稳)。"
        )

    log("CURATE", f"从 {len(pool)} 条相关评论里筛选强相关原声…")
    # Floor of 100 real voices (tiered padding from the most keyword-relevant CLEAN
    # pool items — never listings/duplicates — if the LLM keeps fewer), ceiling 150,
    # scaling with pool size. Bounded by what the clean pool actually contains.
    max_voices = max(100, min(200, len(pool) // 2))
    voices = research.stage_curate(idea, scope, pool, wd, max_voices, False, min_voices=100)
    log("CURATE", f"保留 {len(voices)} 条真实原声(从 {len(pool)} 条池子)")
    # Live feed #2: animate the cull on the right panel. The voices we streamed raw
    # that curate REJECTED get a "piu" drop animation; the survivors stay (recoloured
    # by real sentiment) and any survivor we hadn't shown yet flies in. So the user
    # literally watches the filtering happen on the real voices.
    if emit:
        survivor_ids = {_vid(v.get("url")) for v in voices}
        drop_ids = [i for i in streamed_ids if i not in survivor_ids]
        emit("voices_cull", {
            "drop": drop_ids,
            "keep": [_vpay(v, sent=True) for v in voices[:90]],
        })
    if not voices:
        raise RuntimeError(
            f"收集到 {len(pool)} 条原始内容,但没有一条与「{idea}」强相关 "
            "(可能抓到的多是邻近噪声)。换更聚焦的措辞、或换数据源节点再试。"
        )

    log("CLUSTER", "聚类主题…")
    cluster = research.stage_cluster(idea, target_market, scope, voices, wd, False)

    log("CLUSTER", "拆解用户场景 / 需求 / 替代方案…")
    demand = research.stage_decompose(idea, target_market, scope, voices, cluster, wd, False)

    log("SYNTHESIZE", "综合 thesis / verdict / 策略 / 风险…")
    synth = research.stage_synth(idea, target_market, scope, voices, cluster, wd, False)

    log("ASSEMBLE", "组装 + 校验…")
    data = research.stage_assemble(slug, idea, target_market, scope, voices, cluster, synth, demand=demand)
    # record the chosen report language so the template opens in it (voices stay original)
    data.setdefault("meta", {})["target_lang"] = target_lang
    # Discussion-trend chart: derived ONLY from the unified collected pool — the
    # SAME deduped Reddit data (Arctic Shift + pullpush + reddit.py, merged) that
    # produces the voices/counts/share-of-voice. We deliberately do NOT run a
    # separate pullpush trend query: its archive lags ~12 months and would
    # contradict the rest of the report (the bug that showed 2026 = 0). Yearly,
    # self-consistent with the displayed voices; quarterly histogram as a fallback.
    log("ASSEMBLE", "统计讨论热度趋势(按年,与语料同源)…")
    trend = research.corpus_yearly_trend(data.get("voices") or []) \
            or research.corpus_yearly_trend(pool) \
            or research.compute_trend(pool)
    if trend:
        data["trend"] = trend
        data["trend_source"] = "reddit"

    # Data-quality self-check (plan C): flag repeated/listing/single-source spam so
    # a bad run is caught rather than silently shipped.
    data["quality"] = research.compute_quality(data)
    for w in data["quality"]["warnings"]:
        log("ASSEMBLE", f"⚠ 数据质量:{w}")

    # validate
    schema = load_schema()
    errs = validate_schema(data, schema) + check_cross_refs(data)
    if errs:
        raise RuntimeError("生成数据未通过校验:\n" + "\n".join(errs[:6]))

    # save + translate (best effort)
    data_path = ROOT / "data" / f"{slug}.json"
    data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    log("TRANSLATE", "回填英文(可切中英文)…")
    try:
        import translate_data  # type: ignore
        tr = translate_data.translate(data)
        translate_data.apply_translations(data, tr)
        for v in data.get("voices", []):
            if v.get("title") and "title_en" not in v:
                v["title_en"] = v["title"]
        translate_data.translate_voice_titles(data)   # title_zh: subtle CN subtitle
        # Live feed #3: fade the Chinese translation in under each English voice
        # that's still on the panel (English shown first, then 转译成中文).
        if emit and target_lang == "zh":
            zhmap = {_vid(v.get("url")): v["title_zh"]
                     for v in data.get("voices", []) if v.get("title_zh")}
            if zhmap:
                emit("voices_zh", {"map": zhmap})
        # If the user picked a non-zh/en report language, also localise the whole
        # report into it (<field>_<code> + title_<code>); voices stay original.
        if target_lang not in ("zh", "en"):
            log("TRANSLATE", f"翻译为目标语言 {target_lang}…")
            translate_data.localize(data, target_lang)
        data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        log("TRANSLATE", f"跳过英文回填:{e}")

    # Pre-render the self-contained HTML to dist/<slug>.html so the report has a
    # PERSISTENT, SHAREABLE URL (plan A). Frontend then opens that URL in a new
    # tab, leaving the search page intact so users can generate another report.
    try:
        log("RENDER", "渲染静态报告…")
        tpl_path = ROOT / "templates" / "lens-report-template.html"
        dist_path = ROOT / "dist" / f"{slug}.html"
        dist_path.parent.mkdir(parents=True, exist_ok=True)
        tpl = tpl_path.read_text(encoding="utf-8")
        html = tpl.replace("{{REPORT_DATA_JSON}}",
                           json.dumps(data, ensure_ascii=False))
        dist_path.write_text(html, encoding="utf-8")
        data["_report_url"] = f"/dist/{slug}.html"
    except Exception as e:
        log("RENDER", f"渲染静态报告失败(报告仍可用): {e}")

    return data


def expand_pipeline(slug: str, idea: str, market: str, mode: str | None,
                    creds: dict | None = None, log=None) -> dict:
    """Live deeper search for an already-generated report. Appends new real
    voices to data/<slug>.json and returns {new_voices, total}."""
    creds = creds or {}
    data_path = ROOT / "data" / f"{slug}.json"
    if not data_path.exists():
        raise RuntimeError(f"找不到报告数据 data/{slug}.json(请先生成报告再深搜)")
    data = json.loads(data_path.read_text(encoding="utf-8"))
    idea = idea or data.get("meta", {}).get("idea", "")
    market = market or data.get("meta", {}).get("target_market", "US")

    wd = research.work_dir(slug)
    scope_path = wd / "01-scope.json"
    if scope_path.exists():
        scope = json.loads(scope_path.read_text(encoding="utf-8"))
    else:
        scope = {"subreddits": [], "players": data.get("players", []),
                 "hn_queries": [idea]}
    scope["_idea"] = idea

    # Each click goes DEEPER: persist a round counter in a sidecar (no schema impact)
    # so successive expands widen pagination + rotate queries instead of re-spinning.
    rc_file = wd / "_expand.count"
    try:
        rnd = int(rc_file.read_text().strip()) + 1
    except Exception:
        rnd = 1
    try:
        rc_file.write_text(str(rnd))
    except Exception:
        pass

    with _PIPELINE_LOCK:
        saved = {k: os.environ.get(k) for k in ("OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL")}
        try:
            if creds.get("api_key"):  os.environ["OPENAI_API_KEY"]  = creds["api_key"]
            if creds.get("base_url"): os.environ["OPENAI_BASE_URL"] = creds["base_url"]
            if creds.get("model"):    os.environ["OPENAI_MODEL"]    = creds["model"]
            new = research.stage_expand(idea, market, scope, data.get("voices", []),
                                        data.get("themes", []), wd, log=log, depth=rnd)
        finally:
            for k, v in saved.items():
                if v is None: os.environ.pop(k, None)
                else:         os.environ[k] = v

    if new:
        data.setdefault("voices", []).extend(new)
        # voice→theme edges so the graph/lens stay consistent
        for v in new:
            for tid in v.get("themes", []):
                data.setdefault("edges", []).append({"from": v["id"], "to": tid, "w": 1})
        data.setdefault("verdict", {}).setdefault("evidence_counts", {})["raw_voices"] = len(data["voices"])
        if "quality" in data:
            data["quality"] = research.compute_quality(data)
        data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        # re-render the persistent HTML so the shareable URL reflects the grown corpus
        try:
            tpl = (ROOT / "templates" / "lens-report-template.html").read_text(encoding="utf-8")
            (ROOT / "dist" / f"{slug}.html").write_text(
                tpl.replace("{{REPORT_DATA_JSON}}", json.dumps(data, ensure_ascii=False)),
                encoding="utf-8")
        except Exception:
            pass
    return {"new_voices": new, "total": len(data.get("voices", []))}


# --------------------------------------------------------------------------- #
# HTTP handler                                                                 #
# --------------------------------------------------------------------------- #

FORM_HTML = """<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>VIBE · 产品需求研究 Agent</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&family=Inter:wght@400;500;600&family=Noto+Sans+SC:wght@400;500;700&display=swap');
  :root{
    --bg:#ffffff;--surface:#f7f7f4;--ink:#191815;--ink-2:#56564e;--ink-3:#8c8b80;
    --line:#e8e7e1;--line-2:#dcdbd4;--accent:#0a6b43;--accent-soft:#ecf3ef;--accent-line:#cde0d6;--neg:#a8362a;
    --sans:'Inter','Noto Sans SC',-apple-system,system-ui,sans-serif;
    --display:'Plus Jakarta Sans','Inter','Noto Sans SC',sans-serif;
    --mono:'Inter','Noto Sans SC',ui-monospace,monospace;
  }
  *{box-sizing:border-box}
  html{background:#fff}
  /* device-outline texture at 50% (white veil over the image, fixed so it doesn't scroll) */
  body{margin:0;color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.55;
    /* light-gray veil, lighter at center → grayer at edges: shows the texture AND
       makes the white glass cards pop, with a soft spotlight on the content. */
    background:radial-gradient(125% 95% at 50% 32%, rgba(248,248,245,.40) 0%,
               rgba(226,226,221,.60) 52%, rgba(210,210,204,.72) 100%),
               url('/dist/bg-devices.jpg') center center / cover no-repeat fixed;}
  /* fluorescent-outline layer revealed in a soft circle around the cursor.
     Aligned to the same center/cover/fixed as the base image so outlines light
     up in place. JS updates --mx/--my; the radial mask makes only the area near
     the cursor visible, fading out at the edge. */
  /* layer 1 — reveal the glowing outlines in a soft circle around the cursor */
  body::before{content:"";position:fixed;inset:0;z-index:0;pointer-events:none;
    background:url('/dist/bg-glow.png') center center / cover no-repeat fixed;
    -webkit-mask-image:radial-gradient(circle 150px at var(--mx,-1000px) var(--my,-1000px), #000 0%, rgba(0,0,0,.5) 48%, transparent 72%);
    mask-image:radial-gradient(circle 150px at var(--mx,-1000px) var(--my,-1000px), #000 0%, rgba(0,0,0,.5) 48%, transparent 72%);
    opacity:0;transition:opacity .3s ease;}
  /* layer 2 — a brighter spotlight core right at the cursor (screen-blended,
     sits on top of the outlines, fades fast → the "探照灯" hotspot) */
  body::after{content:"";position:fixed;inset:0;z-index:0;pointer-events:none;
    background:radial-gradient(circle 90px at var(--mx,-1000px) var(--my,-1000px),
      rgba(150,255,215,.45) 0%, rgba(70,230,165,.18) 40%, transparent 70%);
    mix-blend-mode:screen;opacity:0;transition:opacity .3s ease;}
  body.glow-on::before,body.glow-on::after{opacity:1}
  @media (hover:none){body::before,body::after{display:none}}   /* skip on touch */
  .wrap{max-width:820px;margin:0 auto;padding:84px 40px 110px;position:relative;z-index:1}
  /* full-width header above the two cards — centered, narrower for readability */
  .page-head{max-width:720px;margin:0 auto;padding:26px 32px 6px;position:relative;z-index:1;text-align:center}
  /* two cards side by side: left = settings, right = live real-voices feed */
  .layout{max-width:1180px;margin:0 auto;padding:10px 32px 44px;position:relative;z-index:1;
    display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:24px;align-items:stretch}
  .col-left{min-width:0;display:flex;flex-direction:column}
  .col-right{min-width:0;display:flex;flex-direction:column;gap:12px}
  /* both sides read as glass cards */
  .card{border:1px solid rgba(255,255,255,.8);border-radius:16px;padding:18px 22px;
    background:rgba(255,255,255,.55);backdrop-filter:blur(20px) saturate(1.3);-webkit-backdrop-filter:blur(20px) saturate(1.3);
    box-shadow:0 14px 40px -16px rgba(40,45,40,.18)}
  .card-title{font-family:var(--mono);font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;
    color:var(--ink-3);margin-bottom:4px}
  .col-left>.card{flex:1}
  .col-left label:first-of-type{margin-top:10px}
  .page-foot{max-width:1180px;margin:0 auto;padding:14px 32px 60px;position:relative;z-index:1}
  /* live voices card — scrollable, roughly the height of the form column */
  .live-card{position:relative;border:1px solid rgba(255,255,255,.8);border-radius:16px;
    background:rgba(255,255,255,.55);backdrop-filter:blur(20px) saturate(1.3);-webkit-backdrop-filter:blur(20px) saturate(1.3);
    box-shadow:0 14px 40px -16px rgba(40,45,40,.22);
    flex:1;min-height:320px;overflow:hidden;display:flex;flex-direction:column}
  .lc-head{flex:none;padding:14px 16px;border-bottom:1px solid var(--line);font-family:var(--mono);
    font-size:10.5px;letter-spacing:.08em;color:var(--accent);text-transform:uppercase}
  .lc-head #lvCount{color:var(--ink-3)}
  .lc-empty{margin:auto;text-align:center;color:var(--ink-3);padding:30px;line-height:1.7}
  .lc-empty-ic{font-size:34px;color:var(--accent-line);margin-bottom:10px}
  .lc-empty-sub{font-size:12px;color:var(--ink-3);margin-top:4px}
  .lv-list{flex:1;min-height:0;overflow-y:auto;padding:12px 14px;display:flex;flex-direction:column;gap:8px}
  .lv-item{display:flex;gap:9px;align-items:flex-start;padding:9px 12px;border:1px solid var(--line);border-radius:9px;
    background:#fff;font-size:13.5px;line-height:1.45;animation:lvIn .4s ease both}
  @keyframes lvIn{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:none}}
  .lv-item .lv-dot{width:7px;height:7px;border-radius:50%;flex:none;margin-top:5px;background:var(--accent);transition:background .35s}
  .lv-item .lv-dot.neg{background:var(--neg)}
  .lv-item .lv-dot.neu{background:var(--ink-3)}   /* sentiment not known until curate */
  .lv-item .lv-body{flex:1;min-width:0;display:flex;flex-direction:column;gap:1px}
  .lv-item .lv-t{min-width:0;color:var(--ink)}
  .lv-item .lv-zh{font-size:11px;color:var(--ink-3);line-height:1.4;max-height:0;opacity:0;overflow:hidden;
    transition:max-height .45s ease,opacity .45s ease,margin-top .45s ease}
  .lv-item .lv-zh.show{max-height:48px;opacity:1;margin-top:2px}
  .lv-item .lv-m{font-family:var(--mono);font-size:10.5px;color:var(--ink-3);white-space:nowrap;flex:none;margin-top:3px}
  /* "piu" — a rejected voice gets flung out to the right, then collapses its slot */
  @keyframes lvDrop{0%{transform:none;opacity:1}
    30%{transform:translateX(8px) scale(1.03);opacity:1}
    100%{transform:translateX(135%) scale(.85);opacity:0;height:0;min-height:0;
         margin-top:-8px;padding-top:0;padding-bottom:0;border-width:0}}
  .lv-item.dropping{animation:lvDrop .5s cubic-bezier(.55,-0.25,.65,.2) forwards;overflow:hidden;pointer-events:none}
  /* clustering beat: a brief sage halo sweeps the surviving voices */
  @keyframes lvClusterTint{0%,100%{box-shadow:none;border-color:var(--line)}
    50%{box-shadow:0 0 0 2px var(--accent-soft);border-color:var(--accent-line)}}
  .lv-list.clustering .lv-item:not(.dropping){animation:lvClusterTint 1.1s ease}
  /* floating step / progress indicator under the card */
  .live-status{flex:none;border:1px solid rgba(255,255,255,.8);border-radius:12px;padding:12px 14px;
    background:rgba(255,255,255,.7);backdrop-filter:blur(16px) saturate(1.3);-webkit-backdrop-filter:blur(16px) saturate(1.3);
    box-shadow:0 8px 24px -12px rgba(40,45,40,.2)}
  .live-status .ls-row{display:flex;align-items:center;gap:9px;margin-bottom:9px}
  .ls-spin{width:13px;height:13px;border-radius:50%;border:2px solid var(--accent-line);border-top-color:var(--accent);
    flex:none;animation:spin 1s linear infinite}
  .live-status.done .ls-spin{border:0;animation:none}
  .live-status.done .ls-spin::before{content:'✓';color:var(--accent);font-weight:700}
  .ls-step{flex:1;min-width:0;font-size:13px;color:var(--ink);font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .ls-elapsed{font-family:var(--mono);font-size:10.5px;color:var(--ink-3);flex:none}
  .brand{font-family:var(--mono);font-size:10.5px;letter-spacing:.16em;color:var(--ink-3);text-transform:uppercase}
  h1{font-family:var(--display);font-size:26px;font-weight:800;letter-spacing:-.02em;margin:4px 0 7px;line-height:1.12}
  /* 999 evidence subtitle — emphasised inline, not a dominating block */
  .basis{font-size:15px;color:var(--ink-2);margin:0 0 4px;line-height:1.5}
  .basis .n{font-family:var(--display);font-weight:800;font-size:1.4em;color:var(--accent);letter-spacing:-.01em}
  .deck{font-size:13.5px;color:var(--ink-3);margin:0 0 10px;line-height:1.55}
  .topline{margin:0}
  .topline .cases-label{font-family:var(--mono);font-size:10px;letter-spacing:.1em;color:var(--ink-3);
    text-transform:uppercase;margin-bottom:6px}
  .case-grid{display:flex;gap:10px;flex-wrap:wrap;justify-content:center}
  /* frosted-glass surfaces over the device-outline backdrop */
  .case-link{display:inline-flex;align-items:center;gap:7px;font-size:13px;font-weight:600;color:var(--accent);
    text-decoration:none;background:rgba(236,243,239,.6);backdrop-filter:blur(14px) saturate(1.3);-webkit-backdrop-filter:blur(14px) saturate(1.3);
    border:1px solid rgba(255,255,255,.7);border-radius:999px;padding:7px 14px;transition:background .15s,border-color .15s}
  .case-link:hover{background:rgba(226,239,232,.8);border-color:var(--accent)}
  label{display:block;font-family:var(--mono);font-size:10px;letter-spacing:.1em;color:var(--ink-3);text-transform:uppercase;margin:9px 0 4px}
  input,select{width:100%;border:1px solid rgba(255,255,255,.9);border-radius:10px;padding:9px 12px;font-size:15px;
    background:rgba(255,255,255,.72);backdrop-filter:blur(18px) saturate(1.4);-webkit-backdrop-filter:blur(18px) saturate(1.4);
    color:var(--ink);font-family:inherit;box-shadow:0 8px 26px -12px rgba(40,45,40,.28)}
  input:focus,select:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-soft)}
  .two{display:flex;gap:12px}.two>div{flex:1}
  .field-note{font-size:11.5px;color:var(--ink-3);margin-top:4px;line-height:1.45}
  button{appearance:none;border:0;background:var(--accent);color:#fff;cursor:pointer;font-family:var(--display);
    font-weight:700;font-size:15px;letter-spacing:.01em;padding:12px 24px;border-radius:9px;margin-top:12px;width:100%}
  button:hover{background:#085536}button:disabled{opacity:.5;cursor:not-allowed}
  /* progress stepper */
  .prog{margin-top:26px;display:none}
  .prog.show{display:block}
  .prog-bar{height:3px;background:var(--line);border-radius:2px;overflow:hidden;margin-bottom:18px}
  .prog-bar i{display:block;height:100%;width:0;background:var(--accent);transition:width .5s ease}
  .step{display:flex;gap:12px;align-items:flex-start;padding:7px 0;opacity:.4;transition:opacity .3s}
  .step.active,.step.done{opacity:1}
  .step .dot{flex-shrink:0;width:20px;height:20px;border-radius:50%;border:1.5px solid var(--line);
    display:flex;align-items:center;justify-content:center;font-size:11px;color:var(--ink-3);margin-top:1px;
    font-family:var(--mono);background:#fff;transition:all .3s}
  .step.done .dot{background:var(--accent);border-color:var(--accent);color:#fff}
  .step.active .dot{border-color:var(--accent);border-style:solid;animation:spin 1s linear infinite;border-top-color:transparent;color:transparent}
  .step.err .dot{background:var(--neg);border-color:var(--neg);color:#fff}
  @keyframes spin{to{transform:rotate(360deg)}}
  .step .st-body{flex:1;min-width:0}
  .step .st-name{font-family:var(--mono);font-size:12px;color:var(--ink);letter-spacing:.02em}
  .step.active .st-name{font-weight:600}
  .step .st-msg{font-family:var(--mono);font-size:10.5px;color:var(--ink-3);margin-top:2px;min-height:13px;
    overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .step.active .st-msg{color:var(--accent)}
  .step.err .st-msg{color:var(--neg);white-space:normal}
  .step.active{animation:breathe 1.8s ease-in-out infinite}
  @keyframes breathe{0%,100%{opacity:1}50%{opacity:.72}}
  .prog-elapsed{font-family:var(--mono);font-size:10px;color:var(--ink-3);text-align:right;margin-top:10px;letter-spacing:.06em}
  /* live real-voices feed during generation */
  .livevoices{margin-top:18px;border-top:1px solid var(--line);padding-top:14px}
  .livevoices .lv-h{font-family:var(--mono);font-size:10.5px;letter-spacing:.06em;color:var(--accent);margin-bottom:10px}
  .lv-list{display:flex;flex-direction:column;gap:7px;max-height:340px;overflow-y:auto}
  .lv-item{display:flex;gap:9px;align-items:baseline;padding:8px 11px;border:1px solid var(--line);border-radius:8px;
    background:rgba(255,255,255,.6);backdrop-filter:blur(10px);font-size:13px;line-height:1.4;
    animation:lvIn .4s ease both}
  @keyframes lvIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
  .lv-item .lv-dot{width:7px;height:7px;border-radius:50%;flex:none;align-self:center;background:var(--accent)}
  .lv-item .lv-dot.neg{background:var(--neg)}
  .lv-item .lv-t{flex:1;min-width:0;color:var(--ink)}
  .lv-item .lv-m{font-family:var(--mono);font-size:10.5px;color:var(--ink-3);white-space:nowrap;flex:none}
  .hint{font-family:var(--mono);font-size:11px;color:var(--ink-3);margin-top:26px;line-height:1.7;border-top:1px solid var(--line);padding-top:18px}
  /* recent-reports panel (plan B) */
  .recent{margin-top:30px;border-top:1px solid var(--line);padding-top:18px}
  .recent-h{display:flex;justify-content:space-between;align-items:baseline;font-family:var(--mono);
    font-size:10.5px;letter-spacing:.1em;color:var(--ink-3);text-transform:uppercase;margin-bottom:10px}
  .recent-h .recent-actions{display:inline-flex;gap:4px}
  .recent-h a{color:var(--ink-3);text-decoration:none;cursor:pointer;font-size:14px;line-height:1;padding:2px 6px;border-radius:6px}
  .recent-h a:hover{background:var(--surface);color:var(--accent)}
  .recent-list{display:flex;flex-direction:column;gap:6px}
  .recent-list a{display:flex;align-items:baseline;justify-content:space-between;gap:10px;
    padding:9px 12px;border:1px solid rgba(255,255,255,.7);border-radius:9px;
    background:rgba(255,255,255,.55);backdrop-filter:blur(14px) saturate(1.4);-webkit-backdrop-filter:blur(14px) saturate(1.4);
    box-shadow:0 4px 14px -8px rgba(40,45,40,.16);
    text-decoration:none;color:var(--ink);font-size:14px;transition:border-color .15s,background .15s}
  .recent-list a:hover{border-color:var(--accent);background:rgba(236,243,239,.78)}
  /* the JUST-generated report glows softly to guide the eye when the popup was blocked */
  @keyframes rNewGlow{0%,100%{box-shadow:0 0 0 1px var(--accent-line),0 0 13px -3px rgba(10,107,67,.35)}
    50%{box-shadow:0 0 0 1px var(--accent),0 0 22px 1px rgba(10,107,67,.5)}}
  .recent-list a.r-new{position:relative;border-color:var(--accent);background:rgba(236,243,239,.7);animation:rNewGlow 1.9s ease-in-out infinite}
  .recent-list a.r-new .r-idea{color:var(--accent)}
  /* a fading arrow on the LEFT of the just-generated card, jabbing toward it — so a
     user who left the tab and came back instantly spots what's new */
  .recent-list a.r-new::before{content:'NEW →';position:absolute;right:100%;top:50%;margin-right:9px;
    transform:translateY(-50%);font-family:var(--mono);font-size:10px;font-weight:700;letter-spacing:.1em;
    color:var(--accent);white-space:nowrap;pointer-events:none;animation:rNewPoint 1.25s ease-in-out infinite}
  @keyframes rNewPoint{0%,100%{opacity:.12;transform:translateY(-50%) translateX(-5px)}
    50%{opacity:1;transform:translateY(-50%) translateX(2px)}}
  @media(max-width:680px){.recent-list a.r-new::before{display:none}}   /* no room beside the card on phones */
  .recent-list a.r-new .r-new-tag{font-family:var(--mono);font-size:9px;letter-spacing:.08em;color:#fff;background:var(--accent);
    border-radius:5px;padding:2px 6px;margin-left:8px;flex:none}
  .recent-list .r-idea{font-weight:600;color:var(--ink);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1;min-width:0}
  .recent-list .r-meta{font-family:var(--mono);font-size:11px;color:var(--ink-3);white-space:nowrap;flex:none}
  .samples{margin-top:8px;display:flex;gap:8px;flex-wrap:wrap}
  .samples button{width:auto;margin:0;background:rgba(255,255,255,.7);backdrop-filter:blur(14px) saturate(1.4);-webkit-backdrop-filter:blur(14px) saturate(1.4);border:1px solid rgba(255,255,255,.9);color:var(--ink-2);font-size:12px;padding:6px 12px;border-radius:999px;font-family:var(--sans);font-weight:500;box-shadow:0 4px 14px -8px rgba(40,45,40,.22)}
  .samples button:hover{border-color:var(--accent);background:var(--accent-soft);color:var(--ink)}
  .adv{margin-top:12px;border:1px solid rgba(255,255,255,.9);border-radius:12px;padding:0 14px;
    background:rgba(255,255,255,.66);backdrop-filter:blur(18px) saturate(1.4);-webkit-backdrop-filter:blur(18px) saturate(1.4);
    box-shadow:0 8px 26px -12px rgba(40,45,40,.26)}
  .adv summary{cursor:pointer;padding:12px 0;font-family:var(--mono);font-size:12px;color:var(--ink-2);list-style:none}
  .adv summary::-webkit-details-marker{display:none}
  .adv summary:before{content:'▸ ';color:var(--ink-3)}
  .adv[open] summary:before{content:'▾ '}
  .adv[open]{padding-bottom:14px}
  .adv-note{font-family:var(--mono);font-size:10.5px;color:var(--ink-3);margin-top:10px;line-height:1.6}
  /* phones: tighter margins, stack the two-up row, keep type readable */
  @keyframes spin{to{transform:rotate(360deg)}}
  /* tablet/phone: stack the two columns (settings on top, live feed below) */
  @media (max-width:900px){
    .layout{grid-template-columns:1fr;gap:22px;padding:32px 22px 72px;align-items:start}
    .col-left>.card{flex:none}
    .live-card{flex:none;height:min(60vh,460px)}
  }
  @media (max-width:560px){
    .wrap{padding:40px 18px 64px}
    .layout{padding:40px 18px 64px}
    h1{font-size:25px}
    .basis{font-size:14.5px}
    .two{flex-direction:column;gap:0}
    input,select{font-size:16px}   /* >=16px stops iOS auto-zoom on focus */
    button{font-size:16px}
  }
</style></head><body>
<!-- FULL-WIDTH HEADER -->
<header class="page-head">
  <div class="brand">VIBE · 产品需求研究 AGENT</div>
  <h1>产品需求研究 Agent</h1>
  <p class="basis">以 <span class="n">1999</span> 条 Reddit 真实用户原声为依据 · 每个结论都可溯源到原帖</p>
  <p class="deck">输入一个产品想法 → 自动联网深搜真实用户原声 → 出一份可交互的洞察报告。约 5 分钟。</p>
  <div class="topline">
    <div class="cases-label">查看案例 / Sample reports</div>
    <div class="case-grid">
      <a class="case-link" href="/dist/portable-espresso-maker.html" target="_blank" rel="noopener">◧ 便携咖啡机 →</a>
      <a class="case-link" href="/dist/ai-sleep-earbuds.html" target="_blank" rel="noopener">◧ AI 睡眠耳塞 →</a>
    </div>
  </div>
</header>

<div class="layout">
  <!-- LEFT: settings card -->
  <div class="col-left card">
    <div class="card-title">研究设置</div>
    <label>产品想法</label>
    <input id="idea" placeholder="例如:AI 睡眠耳塞 / 智能宠物喂食器 / ..." autofocus>
    <div class="samples">
      <button data-s="AI 睡眠耳塞">AI 睡眠耳塞</button>
      <button data-s="智能宠物喂食器">智能宠物喂食器</button>
      <button data-s="便携咖啡机">便携咖啡机</button>
    </div>

    <div class="two">
      <div><label>目标市场</label><input id="market" value="US"></div>
      <div><label>市场类型(可留 auto)</label>
        <select id="mode"><option value="">自动判断</option><option value="EXISTING">EXISTING 存量</option><option value="NON_STOCK">NON_STOCK 非存量</option></select>
      </div>
    </div>

    <label>报告语言 / Report language</label>
    <select id="lang">
      <option value="zh">简体中文(默认)</option>
      <option value="en">English</option>
      <option value="ja">日本語</option>
      <option value="es">Español</option>
      <option value="fr">Français</option>
      <option value="de">Deutsch</option>
    </select>
    <div class="field-note">报告正文与用户原声的译文将使用此语言;Reddit 原声始终保留英文原文。</div>

    <details class="adv">
      <summary>高级:用自己的 API key(可选,留空走默认)</summary>
      <label>API Key</label>
      <input id="apiKey" placeholder="sk-... 留空则用站点默认 key" autocomplete="off">
      <div class="two">
        <div><label>Base URL</label><input id="baseUrl" placeholder="https://api.deepseek.com/v1"></div>
        <div><label>Model</label><input id="model" placeholder="deepseek-chat"></div>
      </div>
      <div class="adv-note">支持任意 OpenAI 兼容 API(DeepSeek / 通义 / Kimi / OpenAI / 本地 Ollama)。key 只在本次请求用,不保存。</div>
    </details>

    <button id="go">开始研究 →</button>
    <button id="stop" style="display:none;margin-top:10px;background:var(--neg)">■ 停止研究</button>

    <div class="recent" id="recentWrap" hidden>
      <div class="recent-h">
        <span>最近生成的报告(本机) / My recent</span>
        <span class="recent-actions"><a id="recentRefresh" title="刷新">↻</a><a id="recentClear" title="清除本机历史">✕</a></span>
      </div>
      <div class="recent-list" id="recentList"></div>
    </div>
  </div>

  <!-- RIGHT: live real-voices feed + floating step indicator -->
  <div class="col-right">
    <div class="live-card">
      <div class="lc-head" id="lcHead" hidden>实时真实原声 <span id="lvCount"></span></div>
      <div class="lc-empty" id="lcEmpty">
        <div class="lc-empty-ic">◔</div>
        <div>在左侧输入想法、点「开始研究」</div>
        <div class="lc-empty-sub">真实用户原声会在这里一条条实时出现 →</div>
      </div>
      <div class="lv-list" id="lvList"></div>
    </div>
    <div class="live-status" id="liveStatus" hidden>
      <div class="ls-row"><span class="ls-spin" id="lsSpin"></span><span class="ls-step" id="lsStep">准备中…</span><span class="ls-elapsed" id="elapsed"></span></div>
      <div class="prog-bar"><i id="progBar"></i></div>
    </div>
  </div>
</div>
<div class="page-foot">
  <div class="hint">默认用站点配置的 key · 报告生成后自动保存,可分享链接 · 报告内可切换语言 / 导出 PDF / 导出原文</div>
</div>

<script>
  const $ = id => document.getElementById(id);
  document.querySelectorAll('.samples button').forEach(b => b.onclick = () => $('idea').value = b.dataset.s);

  // plan B (per-browser private history):
  // History is stored in THIS browser's localStorage, NOT on the server, so each
  // person only sees their own runs. Server is only asked to resolve idea/timestamp
  // for the slugs the browser already knows. A and B don't see each other's lists.
  // (Report URLs themselves remain public — that's needed for sharing.)
  const _esc = s => String(s||'').replace(/[&<>"]/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;"}[c]));
  const HKEY = 'vibe.history.v1';
  const _slugs = () => { try { return JSON.parse(localStorage.getItem(HKEY) || '[]').filter(s=>typeof s==='string'); } catch { return []; } };
  function recordSlug(slug){
    if (!slug || !/^[a-z0-9][a-z0-9-]{1,60}$/.test(slug)) return;
    const list = _slugs().filter(s => s !== slug);   // newest first; no dups
    list.unshift(slug);
    try { localStorage.setItem(HKEY, JSON.stringify(list.slice(0, 24))); } catch {}
  }
  let _justMade = null;   // slug of the report generated THIS session (gets the glow)
  async function loadRecent(){
    const slugs = _slugs(); const wrap = $('recentWrap');
    if (!slugs.length) { wrap.hidden = true; return; }
    try {
      const r = await fetch('/api/recent?slugs=' + encodeURIComponent(slugs.join(',')), { cache: 'no-store' });
      if (!r.ok) return;
      const { items } = await r.json();
      if (!items || !items.length) { wrap.hidden = true; return; }
      $('recentList').innerHTML = items.map(it => {
        const sl = it.slug || (it.url||'').split('/').pop().replace(/\.html$/,'');
        const isNew = sl && sl === _justMade;
        return `<a class="${isNew?'r-new':''}" href="${_esc(it.url)}" target="_blank" rel="noopener">
        <span class="r-idea">${_esc(it.idea)}${isNew?'<span class="r-new-tag">刚生成 ↗</span>':''}</span>
        <span class="r-meta">${_esc(it.target_market)} · ${_esc(it.timestamp)}</span>
      </a>`;}).join('');
      wrap.hidden = false;
    } catch {}
  }
  // Live real-voices feed. Each voice has a stable id so we can track it across
  // stages: stream it RAW after collect → fling it out ("piu") if curate rejects it
  // → fade its Chinese translation in after translate. Staggered so it reads live.
  const lvEls = new Map();        // id -> element (currently shown)
  let _lvQueue = [], _lvDraining = false;
  function lvReset(){
    clearTimeout(_lvDraining); _lvQueue = []; _lvDraining = false;
    lvEls.clear(); $('lvList').innerHTML = ''; $('lvList').classList.remove('clustering');
  }
  function lvCount(){ $('lvCount').textContent = '· ' + lvEls.size + ' 条'; }
  function lvMake(v){
    const el = document.createElement('div');
    el.className = 'lv-item'; el.dataset.id = v.id;
    const sCls = v.sentiment === 'neg' ? 'neg' : (v.sentiment ? '' : 'neu');
    el.innerHTML = `<span class="lv-dot ${sCls}"></span>`
      + `<span class="lv-body"><span class="lv-t">"${_esc(v.title)}"</span>`
      + `<span class="lv-zh"></span></span>`
      + `<span class="lv-m">${_esc(v.sub)} · ↑${v.score}</span>`;
    return el;
  }
  function lvInsert(v){
    if (lvEls.has(v.id)) return;
    const el = lvMake(v);
    lvEls.set(v.id, el);
    $('lvList').insertBefore(el, $('lvList').firstChild);   // newest on top
    lvCount();
  }
  function lvEnqueue(voices){
    if (!voices || !voices.length) return;
    $('lcEmpty').hidden = true; $('lcHead').hidden = false;
    for (const v of voices) _lvQueue.push(v);
    if (_lvDraining) return;
    const tick = () => {
      const v = _lvQueue.shift();
      if (!v) { _lvDraining = false; return; }
      lvInsert(v);
      _lvDraining = setTimeout(tick, 42);
    };
    _lvDraining = true; tick();
  }
  function _lvFlush(){   // insert any still-queued raw items NOW (before culling)
    clearTimeout(_lvDraining);
    while (_lvQueue.length) lvInsert(_lvQueue.shift());
    _lvDraining = false;
  }
  // curate cull: drop rejected ids (piu, cascaded) + keep/recolour survivors
  function lvCull(drop, keep){
    _lvFlush();
    (drop || []).forEach((id, k) => {
      const el = lvEls.get(id); if (!el) return;
      lvEls.delete(id);
      setTimeout(() => {
        el.classList.add('dropping');
        el.addEventListener('animationend', () => el.remove(), { once:true });
      }, k * 28);
    });
    const missing = [];
    (keep || []).forEach(v => {
      const el = lvEls.get(v.id);
      if (el) {                                   // recolour by real sentiment
        const dot = el.querySelector('.lv-dot');
        if (dot) { dot.classList.remove('neu'); dot.classList.toggle('neg', v.sentiment === 'neg'); }
      } else missing.push(v);
    });
    setTimeout(() => { lvEnqueue(missing); lvCount(); }, (drop ? drop.length : 0) * 28 + 120);
  }
  function lvZh(map){
    for (const id in (map || {})) {
      const el = lvEls.get(id); if (!el) continue;
      const z = el.querySelector('.lv-zh');
      if (z && map[id]) { z.textContent = map[id]; z.classList.add('show'); }
    }
  }
  function lvPulse(){ const l = $('lvList'); l.classList.remove('clustering');
    void l.offsetWidth; l.classList.add('clustering'); }
  document.getElementById('recentRefresh').addEventListener('click', e => { e.preventDefault(); loadRecent(); });
  document.getElementById('recentClear').addEventListener('click', e => { e.preventDefault();
    if (confirm('清除这个浏览器记录的历史?(不会删除已发布的报告)')) {
      try { localStorage.removeItem(HKEY); } catch {}
      loadRecent();
    }
  });
  loadRecent();

  // Cursor-following glow: reveal the fluorescent-outline layer in a soft circle
  // around the pointer. rAF-throttled; fades in/out on enter/leave.
  (function(){
    const b = document.body;
    const move = e => {
      if (e.pointerType === 'touch') return;
      b.style.setProperty('--mx', e.clientX + 'px');
      b.style.setProperty('--my', e.clientY + 'px');
      b.classList.add('glow-on');
    };
    window.addEventListener('pointermove', move, { passive: true });
    window.addEventListener('pointerdown', move, { passive: true });
    document.addEventListener('mouseleave', () => b.classList.remove('glow-on'));
  })();

  // ordered stepper: backend stage tag → {label}. RENDER is added by the frontend.
  const STEPS = [
    ['SCOPE',      '判断市场类型 + 找数据源'],
    ['COLLECT',    '联网搜索真实用户声音(目标 1999 条)'],
    ['CURATE',     '筛选相关声音(剔除噪声)'],
    ['CLUSTER',    '聚类成主题'],
    ['SYNTHESIZE', '综合 thesis / 策略 / 风险'],
    ['ASSEMBLE',   '组装 + 校验'],
    ['TRANSLATE',  '回填英文(中英可切)'],
    ['RENDER',     '渲染交互报告'],
  ];
  const stepIndex = {}; STEPS.forEach((s,i) => stepIndex[s[0]] = i);
  const stepLabel = {}; STEPS.forEach(s => stepLabel[s[0]] = s[1]);

  // compact step indicator (right-panel floating status), not a full list
  function setActive(tag, msg){
    const idx = stepIndex[tag]; if (idx == null) return;
    const n = idx + 1, total = STEPS.length;
    $('liveStatus').classList.remove('done');
    $('lsStep').textContent = `${n}/${total} ${stepLabel[tag]}` + (msg ? ` · ${msg}` : '');
    $('progBar').style.width = Math.round(idx / (total - 1) * 100) + '%';
  }
  function allDone(){
    $('progBar').style.width = '100%';
    $('liveStatus').classList.add('done');
    $('lsStep').textContent = '完成 · 完整报告已在新标签打开';
  }
  function setError(tag, msg){
    $('liveStatus').classList.remove('done');
    $('lsSpin').style.display = 'none';
    $('lsStep').innerHTML = '<span style="color:var(--neg)">✗ ' + (msg||'出错了') + '</span>';
  }

  let elapsedTimer = null, lastTag = 'SCOPE', abortCtl = null;
  $('stop').onclick = () => { if (abortCtl) abortCtl.abort(); };
  $('go').onclick = async () => {
    const idea = $('idea').value.trim();
    if (!idea){ $('idea').focus(); return; }
    abortCtl = new AbortController();
    $('go').disabled = true; $('go').textContent = '研究中…(右侧实时显示)';
    $('stop').style.display = 'block';
    // reset + arm the right live panel
    lvReset();
    $('lcEmpty').hidden = true; $('lcHead').hidden = false;
    $('lvCount').textContent = '· 采集中…';
    $('liveStatus').hidden = false; $('lsSpin').style.display = '';
    setActive('SCOPE','提交:'+idea);

    const t0 = Date.now();
    clearInterval(elapsedTimer);
    elapsedTimer = setInterval(() => { $('elapsed').textContent = '已用时 ' + Math.round((Date.now()-t0)/1000) + ' 秒'; }, 500);

    try {
      const r = await fetch('/api/research', {
        method:'POST', headers:{'Content-Type':'application/json'}, signal: abortCtl.signal,
        body: JSON.stringify({ idea, market: $('market').value, mode: $('mode').value,
          target_lang: $('lang').value,
          api_key: $('apiKey').value.trim(), base_url: $('baseUrl').value.trim(), model: $('model').value.trim() })
      });
      if (!r.ok || !r.body) throw new Error('连不上后端');

      // parse Server-Sent Events from the stream
      const reader = r.body.getReader();
      const dec = new TextDecoder();
      let buf = '', finalData = null, errMsg = null;
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        let sep;
        while ((sep = buf.indexOf('\\n\\n')) >= 0) {
          const chunk = buf.slice(0, sep); buf = buf.slice(sep + 2);
          const ev = (chunk.match(/^event: (.+)$/m) || [])[1];
          const dm = (chunk.match(/^data: (.+)$/m) || [])[1];
          if (!dm) continue;
          let payload; try { payload = JSON.parse(dm); } catch { continue; }
          if (ev === 'progress') { lastTag = payload.stage; setActive(payload.stage, payload.msg);
            if (payload.stage === 'CLUSTER') lvPulse(); }
          else if (ev === 'voices_raw') { lvEnqueue(payload.voices || []); }
          else if (ev === 'voices_cull') { lvCull(payload.drop || [], payload.keep || []); }
          else if (ev === 'voices_zh') { lvZh(payload.map || {}); }
          else if (ev === 'voices') { lvEnqueue(payload.voices || []); }   // back-compat
          else if (ev === 'done') { finalData = payload.data; }
          else if (ev === 'error') { errMsg = payload.error; }
        }
      }
      clearInterval(elapsedTimer);
      $('stop').style.display = 'none';

      if (errMsg) { setError(lastTag, errMsg); $('go').disabled=false; $('go').textContent='重试 →'; return; }
      if (!finalData) { setError(lastTag, '未收到结果,请重试'); $('go').disabled=false; $('go').textContent='重试 →'; return; }

      // Plan A: report is already a self-contained HTML at _report_url. Open it in
      // a NEW TAB so the search page stays open — user can keep generating others.
      // Fallback if backend rendering didn't run: fetch the template and write inline.
      setActive('RENDER', '渲染报告…');
      allDone();
      const url = finalData._report_url;
      const slug = (finalData.meta && finalData.meta.slug) || (url && url.split('/').pop().replace(/\.html$/,''));
      if (slug) { recordSlug(slug); _justMade = slug; }     // private to this browser; glows in 最近报告
      if (url) {
        const win = window.open(url, '_blank', 'noopener');
        const blocked = !win || win.closed || typeof win.closed === 'undefined';
        // render the recent list NOW so the just-made report shows with its glow,
        // guiding the user to it (popups are frequently blocked by browsers).
        await loadRecent();
        $('recentWrap')?.scrollIntoView({ behavior:'smooth', block:'nearest' });
        $('go').disabled = false;
        $('go').textContent = blocked
          ? '弹窗被拦截 —— 在下方「最近报告」点开高亮那条 ↓'
          : '报告已在新标签打开 ↗ — 再生成一份 →';
        setTimeout(() => { $('go').textContent = '开始研究 →'; }, blocked ? 6000 : 2200);
      } else {
        const tpl = await fetch('/templates/lens-report-template.html').then(x=>x.text());
        const filled = tpl.replace('{{REPORT_DATA_JSON}}', () => JSON.stringify(finalData));
        document.open(); document.write(filled); document.close();
      }
    } catch(e){
      clearInterval(elapsedTimer);
      $('stop').style.display = 'none';
      if (e.name === 'AbortError'){
        setError(lastTag, '已停止 —— 后台可能仍在跑完这一轮,稍候再重新开始');
        $('go').disabled=false; $('go').textContent='重新开始 →';
        return;
      }
      const hint = /fetch|后端/i.test(e.message)
        ? '连不上后端 — 请确认终端里 make app 还在运行(那个窗口别关),然后重试。'
        : e.message;
      setError(lastTag, hint); $('go').disabled=false; $('go').textContent='重试 →';
    }
  };
</script>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass  # quiet

    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        b = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            return self._send(200, FORM_HTML)
        # /api/recent?slugs=a,b,c — resolve THIS browser's history to metadata.
        # Per-browser privacy: the slug list lives in the user's localStorage; the
        # server only fills in {idea, timestamp, market} for the slugs the browser
        # already knows. No server-side global history → A can't see B's reports.
        # (Report HTMLs themselves are still public URLs — that's how "share link"
        # works; "history" is just personal.)
        if path == "/api/recent":
            from urllib.parse import parse_qs
            qs = parse_qs(urlparse(self.path).query)
            wanted = [s for s in (qs.get("slugs") or [""])[0].split(",")
                      if s and re.match(r"^[a-z0-9][a-z0-9-]{1,60}$", s)][:24]
            items = []
            for slug in wanted:
                d = ROOT / "dist" / f"{slug}.html"
                j = ROOT / "data" / f"{slug}.json"
                if not d.exists() or not j.exists():
                    continue
                try:
                    meta = json.loads(j.read_text(encoding="utf-8")).get("meta", {})
                    items.append({"slug": slug, "url": f"/dist/{slug}.html",
                                  "idea": meta.get("idea", slug),
                                  "timestamp": meta.get("timestamp", ""),
                                  "target_market": meta.get("target_market", "")})
                except Exception:
                    continue
            return self._send(200, json.dumps({"items": items}, ensure_ascii=False),
                              "application/json")
        # serve dist/ + templates/ + assets/ static
        _CT = {".json": "application/json", ".webp": "image/webp", ".png": "image/png",
               ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".svg": "image/svg+xml",
               ".js": "application/javascript", ".css": "text/css"}
        for prefix, base in (("/dist/", ROOT / "dist"), ("/templates/", ROOT / "templates"),
                             ("/data/", ROOT / "data"), ("/assets/", ROOT / "assets")):
            if path.startswith(prefix):
                f = base / path[len(prefix):]
                if f.exists() and f.is_file():
                    ctype = _CT.get(f.suffix, "text/html; charset=utf-8")
                    return self._send(200, f.read_bytes(), ctype)
        return self._send(404, "not found")

    def _do_expand(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            req = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self._send(400, json.dumps({"ok": False, "error": "bad request"}), "application/json")
        slug = (req.get("slug") or "").strip()
        if not slug:
            return self._send(400, json.dumps({"ok": False, "error": "missing slug"}), "application/json")
        creds = {
            "api_key": (req.get("api_key") or "").strip(),
            "base_url": (req.get("base_url") or "").strip(),
            "model": (req.get("model") or "").strip(),
        }
        print(f"\n⊕ expand: {slug}", flush=True)

        # Stream progress as SSE so the report can show a real, moving progress bar
        # during the 30–60s deep search (search → dedup → AI score → merge).
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        import threading as _thr
        _wlock = _thr.Lock()
        def _write(chunk):
            with _wlock:
                try:
                    self.wfile.write(chunk); self.wfile.flush(); return True
                except (BrokenPipeError, ConnectionResetError, ValueError, OSError):
                    return False
        def sse(event, payload):
            _write(f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8"))
        def log(stage, msg):
            print(f"  {stage}: {msg}", flush=True)
            sse("progress", {"stage": stage, "msg": msg})
        # keepalive during silent subprocess stretches so the connection stays open
        _stop = _thr.Event()
        def _hb():
            while not _stop.wait(15):
                if not _write(b": keepalive\n\n"): break
        _t = _thr.Thread(target=_hb, daemon=True); _t.start()
        try:
            res = expand_pipeline(slug, (req.get("idea") or "").strip(),
                                  (req.get("market") or "").strip(),
                                  (req.get("mode") or "").strip() or None, creds, log=log)
            print(f"  + {len(res['new_voices'])} new voices (total {res['total']})", flush=True)
            sse("done", {"ok": True, **res})
        except Exception as e:
            print(f"  ✗ expand {e}", flush=True)
            sse("error", {"ok": False, "error": str(e)})
        finally:
            _stop.set()

    def _do_ask(self):
        """Context-aware Q&A grounded in ONE report's real voices. The report page
        sends a compact voices context + the running conversation; we answer in the
        report's target language, strictly from the evidence."""
        length = int(self.headers.get("Content-Length", 0))
        try:
            req = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self._send(400, json.dumps({"ok": False, "error": "bad request"}), "application/json")
        question = (req.get("question") or "").strip()
        if not question:
            return self._send(400, json.dumps({"ok": False, "error": "missing question"}), "application/json")
        idea = (req.get("idea") or "").strip() or "this product"
        lang = (req.get("lang") or "zh").strip().lower()
        voices = req.get("voices") or []          # [{t, s, sub}] compact, from the report
        history = req.get("history") or []         # [{role, content}] prior turns
        creds = req.get("creds") or {}
        lang_name = {"zh": "简体中文", "en": "English", "ja": "日本語",
                     "es": "español", "fr": "français", "de": "Deutsch"}.get(lang, "English")
        # bound the context so the request stays fast/cheap
        vlist = [{"t": (v.get("t") or "")[:160], "s": v.get("s"), "sub": v.get("sub")}
                 for v in voices[:140] if v.get("t")]
        sys_msg = (
            f"You are a sharp product-research assistant embedded in a report about “{idea}”. "
            f"Below is a sample of REAL user voices (t=title/quote, s=sentiment pos/neg, sub=community) "
            f"collected from Reddit/HN. Answer the user's question USING ONLY evidence from these voices: "
            f"cite what users actually said, surface sentiment patterns and concrete pains/wins, and if the "
            f"voices don't cover it, say so honestly rather than inventing. Be concise (2–6 sentences), "
            f"specific, and conversational. Reply in {lang_name}. "
            f'Output STRICT JSON only: {{"answer": "<your reply>"}}.')
        convo = ""
        for h in history[-8:]:
            role = "用户" if h.get("role") == "user" else "助手"
            convo += f"\n{role}: {(h.get('content') or '')[:600]}"
        user = (f"Real user voices (JSON):\n{json.dumps(vlist, ensure_ascii=False)}\n\n"
                + (f"Conversation so far:{convo}\n\n" if convo else "")
                + f"User question: {question}")
        # per-request creds override (same mechanism as research), else server default
        import os as _os
        saved = {}
        for k, env in (("api_key", "OPENAI_API_KEY"), ("base_url", "OPENAI_BASE_URL"), ("model", "OPENAI_MODEL")):
            if creds.get(k):
                saved[env] = _os.environ.get(env)
                _os.environ[env] = creds[k]
        try:
            from llm_client import chat_json
            res = chat_json(sys_msg, user, temperature=0.4, max_tokens=1200)
            answer = (res.get("answer") or "").strip() if isinstance(res, dict) else ""
            if not answer:
                answer = res.get("text") or res.get("reply") or "" if isinstance(res, dict) else ""
            return self._send(200, json.dumps({"ok": True, "answer": answer}, ensure_ascii=False), "application/json")
        except Exception as e:
            print(f"  ✗ ask {e}", flush=True)
            return self._send(500, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False), "application/json")
        finally:
            for env, v in saved.items():
                if v is None: _os.environ.pop(env, None)
                else: _os.environ[env] = v

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/expand":
            return self._do_expand()
        if path == "/api/ask":
            return self._do_ask()
        if path != "/api/research":
            return self._send(404, "not found")
        length = int(self.headers.get("Content-Length", 0))
        try:
            req = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self._send(400, json.dumps({"ok": False, "error": "bad request"}), "application/json")
        idea = (req.get("idea") or "").strip()
        if not idea:
            return self._send(400, json.dumps({"ok": False, "error": "missing idea"}), "application/json")
        market = (req.get("market") or "US").strip()
        mode = (req.get("mode") or "").strip() or None
        target_lang = (req.get("target_lang") or "zh").strip().lower() or "zh"
        creds = {
            "api_key": (req.get("api_key") or "").strip(),
            "base_url": (req.get("base_url") or "").strip(),
            "model": (req.get("model") or "").strip(),
        }
        custom = "custom-key" if creds["api_key"] else "default-key"
        print(f"\n▶ research: {idea}  (market={market}, mode={mode or 'auto'}, {custom})", flush=True)

        # Stream progress as Server-Sent Events so the UI shows live stages.
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        import threading as _thr
        _wlock = _thr.Lock()
        def _write(chunk: bytes) -> bool:
            with _wlock:
                try:
                    self.wfile.write(chunk); self.wfile.flush()
                    return True
                except (BrokenPipeError, ConnectionResetError, ValueError, OSError):
                    return False

        def sse(event, payload):
            _write(f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8"))

        def log(stage, msg):
            print(f"  {stage}: {msg}", flush=True)
            sse("progress", {"stage": stage, "msg": msg})

        # Keepalive: emit an SSE comment every 15s so the connection never goes idle
        # during the long, silent LLM stages. Without this, the platform/browser cuts
        # the idle connection and the UI shows "未收到结果". Comments (": ...") are
        # ignored by the EventSource/stream parser on the client.
        _stop = _thr.Event()
        def _heartbeat():
            while not _stop.wait(15):
                if not _write(b": keepalive\n\n"):
                    break
        _hb = _thr.Thread(target=_heartbeat, daemon=True)
        _hb.start()
        try:
            data = run_pipeline(idea, market, mode, log=log, creds=creds,
                                target_lang=target_lang, emit=sse)
            sse("done", {"ok": True, "data": data})
        except Exception as e:
            print(f"  ✗ {e}", flush=True)
            sse("error", {"ok": False, "error": str(e)})
        finally:
            _stop.set()


def main():
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    hosted = bool(_os_cfg.environ.get("PORT"))   # running on a cloud platform
    url = f"http://localhost:{PORT}"
    print(f"\n  VIBE 品类研究 · Web App  (host={HOST} port={PORT})")
    print(f"  → {url}\n  (Ctrl+C 退出)\n")
    if not hosted:                                # only pop a browser when local
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  bye")
        srv.shutdown()


if __name__ == "__main__":
    main()
