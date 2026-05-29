#!/usr/bin/env python3
"""
Shared OpenAI-compatible LLM client + .env loader.

Used by scripts/research.py and templates/pipeline/cluster_themes.py.
Zero external dependencies (stdlib urllib).
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_dotenv() -> None:
    """Load KEY=VALUE from repo-root .env into os.environ (existing wins)."""
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def chat_json(system: str, user: str, *, temperature: float = 0.3,
              model: str | None = None, timeout: int = 120) -> dict:
    """
    Call an OpenAI-compatible /chat/completions endpoint, force JSON output,
    return the parsed dict. Raises RuntimeError on missing key / bad JSON.
    """
    load_dotenv()
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY not set. Put it in .env (see .env.example)."
        )
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")

    endpoint = f"{base_url}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    print(f"    → LLM {base_url} model={model} ...", file=sys.stderr)

    import shutil, subprocess
    have_curl = bool(shutil.which("curl"))

    def via_curl(direct: bool):
        # Clash/proxy + Python urllib HTTPS is flaky ('EOF in violation of
        # protocol'). curl is reliable. Domestic APIs (DeepSeek) need NO proxy
        # (--noproxy '*'); foreign APIs (OpenAI) need the proxy. Try both.
        if not have_curl:
            return None
        cmd = ["curl", "-s", "-m", str(timeout), "-X", "POST", endpoint]
        if direct:
            cmd += ["--noproxy", "*"]
        for k, v in headers.items():
            cmd += ["-H", f"{k}: {v}"]
        cmd += ["--data-binary", "@-"]
        try:
            out = subprocess.run(cmd, input=body, capture_output=True, timeout=timeout + 10)
            if out.returncode == 0 and out.stdout:
                return json.loads(out.stdout)
        except Exception:
            return None
        return None

    def via_urllib():
        req = urllib.request.Request(endpoint, data=body, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())

    # Order: direct curl (domestic LLM) → proxied curl (foreign LLM) → urllib.
    payload = via_curl(direct=True) or via_curl(direct=False)
    if payload is None:
        try:
            payload = via_urllib()
        except Exception as e:
            raise RuntimeError(
                f"LLM 请求失败(curl 直连/代理 + urllib 都不通): {e}. "
                f"检查 {base_url} 是否可达、key 是否有效、代理设置。"
            ) from e
    if "choices" not in payload:
        raise RuntimeError(f"LLM 返回异常: {json.dumps(payload)[:300]}")
    text = payload["choices"][0]["message"]["content"]
    # Some providers wrap JSON in ```json fences despite response_format
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"LLM returned non-JSON ({e}):\n{text[:600]}") from e
