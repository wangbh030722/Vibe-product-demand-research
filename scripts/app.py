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

PORT = 8200


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
                 log, creds: dict | None = None) -> dict:
    creds = creds or {}
    with _PIPELINE_LOCK:
        # Apply per-request key override (falls back to .env default), restore after.
        saved = {k: os.environ.get(k) for k in ("OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL")}
        try:
            if creds.get("api_key"):    os.environ["OPENAI_API_KEY"]  = creds["api_key"]
            if creds.get("base_url"):   os.environ["OPENAI_BASE_URL"] = creds["base_url"]
            if creds.get("model"):      os.environ["OPENAI_MODEL"]    = creds["model"]
            return _run_pipeline_inner(idea, target_market, mode, log)
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


def _run_pipeline_inner(idea: str, target_market: str, mode: str | None,
                        log) -> dict:
    slug = slugify(idea)
    wd = research.work_dir(slug)

    log("SCOPE", "判断市场类型 + 找数据源…")
    scope = research.stage_scope(idea, target_market, wd, False, mode or None)
    scope["_idea"] = idea
    research.save(wd / "01-scope.json", scope)

    log("COLLECT", f"联网抓取 {scope.get('subreddits')} + HN…")
    pool = research.stage_collect(scope, wd, False)

    log("COLLECT", f"原始池 {len(pool)} 条")
    if len(pool) < 3:
        raise RuntimeError(
            f"数据源几乎没抓到内容(原始池仅 {len(pool)} 条)。"
            "常见原因:① Reddit 封了你代理出口 IP(403)② HN/网络 TLS 不稳。"
            "解决:换一个 Clash 节点(住宅 IP)再试,或用「聊天指令包」路径"
            "(让 Claude/ChatGPT 联网收集,比本地抓取稳)。"
        )

    log("CURATE", "筛选相关用户声音(剔除噪声)…")
    voices = research.stage_curate(idea, scope, pool, wd, 24, False)
    if not voices:
        raise RuntimeError(
            f"收集到 {len(pool)} 条原始内容,但没有一条与「{idea}」强相关 "
            "(可能抓到的多是邻近噪声)。换更聚焦的措辞、或换数据源节点再试。"
        )

    log("CLUSTER", "聚类主题…")
    cluster = research.stage_cluster(idea, target_market, scope, voices, wd, False)

    log("SYNTHESIZE", "综合 thesis / verdict / 策略 / 风险…")
    synth = research.stage_synth(idea, target_market, scope, voices, cluster, wd, False)

    log("ASSEMBLE", "组装 + 校验…")
    data = research.stage_assemble(slug, idea, target_market, scope, voices, cluster, synth)

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
        data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        log("TRANSLATE", f"跳过英文回填:{e}")

    return data


# --------------------------------------------------------------------------- #
# HTTP handler                                                                 #
# --------------------------------------------------------------------------- #

FORM_HTML = """<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>VIBE · 品类研究</title>
<style>
  :root{--bg:#faf8f4;--ink:#1c1d20;--ink-2:#3d3e44;--ink-3:#737277;--line:#e3ddcf;
    --mono:'SF Mono',Menlo,Monaco,monospace;--serif:'Iowan Old Style',Cambria,serif;--sage:#5b7a52;--rust:#a0533c;}
  *{box-sizing:border-box}html,body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,system-ui,sans-serif}
  .wrap{max-width:680px;margin:0 auto;padding:64px 24px}
  .brand{font-family:var(--mono);font-size:11px;letter-spacing:.18em;color:var(--ink-3);text-transform:uppercase}
  h1{font-family:var(--serif);font-size:32px;font-weight:600;margin:8px 0 6px}
  .deck{font-family:var(--serif);font-style:italic;color:var(--ink-2);margin:0 0 30px}
  label{display:block;font-family:var(--mono);font-size:10.5px;letter-spacing:.1em;color:var(--ink-3);text-transform:uppercase;margin:18px 0 6px}
  input,select{width:100%;border:1px solid var(--line);border-radius:7px;padding:12px 14px;font-size:15px;background:#fff;color:var(--ink);font-family:inherit}
  input:focus,select:focus{outline:none;border-color:var(--ink-3)}
  .two{display:flex;gap:12px}.two>div{flex:1}
  button{appearance:none;border:0;background:var(--ink);color:#fff;cursor:pointer;font-family:var(--mono);font-size:14px;letter-spacing:.04em;padding:14px 26px;border-radius:7px;margin-top:24px;width:100%}
  button:hover{background:#000}button:disabled{opacity:.5;cursor:not-allowed}
  .log{margin-top:24px;font-family:var(--mono);font-size:12px;color:var(--ink-2);line-height:1.9;display:none}
  .log.show{display:block}
  .log .step{display:flex;gap:10px;align-items:baseline}
  .log .step .tag{color:var(--sage);min-width:96px}
  .log .step.err .tag{color:var(--rust)}
  .hint{font-family:var(--mono);font-size:11px;color:var(--ink-3);margin-top:26px;line-height:1.7;border-top:1px solid var(--line);padding-top:18px}
  .samples{margin-top:10px;display:flex;gap:8px;flex-wrap:wrap}
  .samples button{width:auto;margin:0;background:#fff;border:1px solid var(--line);color:var(--ink-2);font-size:11px;padding:6px 11px}
  .samples button:hover{border-color:var(--ink-3);background:#fff;color:var(--ink)}
  .adv{margin-top:18px;border:1px solid var(--line);border-radius:8px;padding:0 14px;background:#fff}
  .adv summary{cursor:pointer;padding:12px 0;font-family:var(--mono);font-size:12px;color:var(--ink-2);list-style:none}
  .adv summary::-webkit-details-marker{display:none}
  .adv summary:before{content:'▸ ';color:var(--ink-3)}
  .adv[open] summary:before{content:'▾ '}
  .adv[open]{padding-bottom:14px}
  .adv-note{font-family:var(--mono);font-size:10.5px;color:var(--ink-3);margin-top:10px;line-height:1.6}
</style></head><body>
<div class="wrap">
  <div class="brand">VIBE · CATEGORY DEEP DIVE</div>
  <h1>品类需求研究</h1>
  <p class="deck">输入一个产品想法,自动联网调研 → 出可交互报告。约 40-60 秒。</p>

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
  <div class="log" id="log"></div>

  <div class="hint">默认用站点配置的 key · 生成的数据存到 data/&lt;slug&gt;.json · 报告渲染后右上角可切中英文 / 下载 PDF</div>
</div>

<script>
  const $ = id => document.getElementById(id);
  document.querySelectorAll('.samples button').forEach(b => b.onclick = () => $('idea').value = b.dataset.s);

  function addLog(tag, msg, err){
    const d = document.createElement('div');
    d.className = 'step' + (err?' err':'');
    d.innerHTML = `<span class="tag">${tag}</span><span>${msg}</span>`;
    $('log').appendChild(d);
  }

  $('go').onclick = async () => {
    const idea = $('idea').value.trim();
    if (!idea){ $('idea').focus(); return; }
    $('go').disabled = true; $('go').textContent = '研究中… 约 40-60 秒,请勿关闭';
    $('log').className = 'log show'; $('log').innerHTML = '';
    addLog('START', '提交:' + idea);

    try {
      const r = await fetch('/api/research', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ idea, market: $('market').value, mode: $('mode').value,
          api_key: $('apiKey').value.trim(), base_url: $('baseUrl').value.trim(), model: $('model').value.trim() })
      });
      const out = await r.json();
      if (!out.ok){ addLog('ERROR', out.error || '失败', true); $('go').disabled=false; $('go').textContent='重试 →'; return; }
      addLog('DONE', '渲染报告…');
      // fetch template, inject, swap document
      const tpl = await fetch('/dist/_template.html').then(x=>x.text());
      const filled = tpl.replace('{{REPORT_DATA_JSON}}', () => JSON.stringify(out.data));
      document.open(); document.write(filled); document.close();
    } catch(e){
      const hint = /fetch/i.test(e.message)
        ? '连不上后端 — 请确认终端里 `make app` 还在运行(那个窗口别关),然后重试。'
        : e.message;
      addLog('ERROR', hint, true); $('go').disabled=false; $('go').textContent='重试 →';
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
        # serve dist/ + templates/ static
        for prefix, base in (("/dist/", ROOT / "dist"), ("/templates/", ROOT / "templates"), ("/data/", ROOT / "data")):
            if path.startswith(prefix):
                f = base / path[len(prefix):]
                if f.exists() and f.is_file():
                    ctype = "application/json" if f.suffix == ".json" else "text/html; charset=utf-8"
                    return self._send(200, f.read_bytes(), ctype)
        return self._send(404, "not found")

    def do_POST(self):
        if urlparse(self.path).path != "/api/research":
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
        creds = {
            "api_key": (req.get("api_key") or "").strip(),
            "base_url": (req.get("base_url") or "").strip(),
            "model": (req.get("model") or "").strip(),
        }
        custom = "custom-key" if creds["api_key"] else "default-key"
        print(f"\n▶ research: {idea}  (market={market}, mode={mode or 'auto'}, {custom})", flush=True)
        try:
            data = run_pipeline(idea, market, mode,
                                log=lambda t, m: print(f"  {t}: {m}", flush=True),
                                creds=creds)
            return self._send(200, json.dumps({"ok": True, "data": data}, ensure_ascii=False), "application/json")
        except Exception as e:
            print(f"  ✗ {e}", flush=True)
            return self._send(200, json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False), "application/json")


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://localhost:{PORT}"
    print(f"\n  VIBE 品类研究 · 本地 Web App")
    print(f"  → {url}\n  (Ctrl+C 退出)\n")
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  bye")
        srv.shutdown()


if __name__ == "__main__":
    main()
