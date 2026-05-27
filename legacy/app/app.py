#!/usr/bin/env python3
"""真需求/伪需求 research app — local web server.

Runs a Python stdlib HTTP server on localhost. Serves the single-page UI in
web/ and exposes a small JSON API + SSE stream for running a research job.

Usage:
    python3 app.py [--port 8123]
    # then open http://localhost:8123/

No pip install required for the base app. Anthropic SDK is optional — when
absent, LLM-driven panels degrade to "API key not configured" placeholders.
"""
from __future__ import annotations

import argparse
import json
import os
import queue
import sys
import threading
import time
import traceback
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# Add repo root to sys.path so `core.*` imports work
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from core import pipeline  # noqa: E402

# ----------------------------------------------------------------------
# In-memory job registry
# ----------------------------------------------------------------------
JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()


def make_job(idea: str, locale: str, mode_override: str | None) -> str:
    job_id = uuid.uuid4().hex[:12]
    q: queue.Queue = queue.Queue()
    with JOBS_LOCK:
        JOBS[job_id] = {
            "id": job_id,
            "idea": idea,
            "locale": locale,
            "mode_override": mode_override,
            "status": "queued",
            "created_at": time.time(),
            "result": None,
            "error": None,
            "queue": q,
        }
    return job_id


def run_job(job_id: str):
    job = JOBS[job_id]
    q = job["queue"]

    def emit(event: str, data: dict):
        q.put((event, data))

    try:
        emit("status", {"phase": "starting", "msg": "kicking off pipeline"})
        result = pipeline.run(
            idea=job["idea"],
            locale=job["locale"],
            mode_override=job["mode_override"],
            emit=emit,
        )
        job["result"] = result
        job["status"] = "done"
        emit("done", {"result_url": f"/api/result/{job_id}"})
    except Exception as e:
        tb = traceback.format_exc()
        job["error"] = {"message": str(e), "traceback": tb}
        job["status"] = "error"
        emit("error", {"message": str(e)})
        sys.stderr.write(f"[job {job_id}] {tb}\n")
    finally:
        q.put(None)  # sentinel


# ----------------------------------------------------------------------
# HTTP handler
# ----------------------------------------------------------------------
WEB_DIR = ROOT / "web"


class Handler(BaseHTTPRequestHandler):
    server_version = "DemandResearch/0.1"

    def log_message(self, fmt, *args):
        sys.stderr.write("[http] " + fmt % args + "\n")

    # ---- helpers ----
    def _send_json(self, code: int, body: dict):
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def _send_file(self, path: Path, mime: str):
        try:
            data = path.read_bytes()
        except FileNotFoundError:
            self.send_error(404, "Not found")
            return
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    # ---- routing ----
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            return self._send_file(WEB_DIR / "index.html", "text/html; charset=utf-8")
        if path == "/style.css":
            return self._send_file(WEB_DIR / "style.css", "text/css; charset=utf-8")
        if path == "/app.js":
            return self._send_file(WEB_DIR / "app.js", "application/javascript; charset=utf-8")

        if path.startswith("/api/stream/"):
            return self._stream_job(path.split("/", 3)[-1])
        if path.startswith("/api/result/"):
            return self._result_job(path.split("/", 3)[-1])
        if path == "/api/runs":
            return self._list_runs()
        if path == "/api/health":
            return self._send_json(200, {"ok": True, "anthropic_key": bool(os.environ.get("ANTHROPIC_API_KEY"))})

        self.send_error(404, "Not found")

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/run":
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length).decode("utf-8") if length else "{}"
            try:
                req = json.loads(body)
            except json.JSONDecodeError:
                return self._send_json(400, {"error": "invalid JSON"})
            idea = (req.get("idea") or "").strip()
            locale = (req.get("locale") or "US").strip()
            mode_override = req.get("mode") or None
            if not idea:
                return self._send_json(400, {"error": "idea required"})
            job_id = make_job(idea, locale, mode_override)
            t = threading.Thread(target=run_job, args=(job_id,), daemon=True)
            t.start()
            return self._send_json(200, {"job_id": job_id, "stream": f"/api/stream/{job_id}"})

        self.send_error(404, "Not found")

    # ---- SSE stream ----
    def _stream_job(self, job_id: str):
        with JOBS_LOCK:
            job = JOBS.get(job_id)
        if not job:
            return self.send_error(404, "Unknown job")
        q = job["queue"]
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        try:
            while True:
                item = q.get(timeout=300)
                if item is None:
                    break
                event, data = item
                msg = f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
                self.wfile.write(msg.encode("utf-8"))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _result_job(self, job_id: str):
        with JOBS_LOCK:
            job = JOBS.get(job_id)
        if not job:
            return self.send_error(404, "Unknown job")
        if job["status"] != "done":
            return self._send_json(202, {"status": job["status"], "error": job.get("error")})
        return self._send_json(200, job["result"])

    def _list_runs(self):
        with JOBS_LOCK:
            runs = [
                {
                    "id": j["id"], "idea": j["idea"], "locale": j["locale"],
                    "status": j["status"], "created_at": j["created_at"],
                }
                for j in JOBS.values()
            ]
        runs.sort(key=lambda r: r["created_at"], reverse=True)
        return self._send_json(200, {"runs": runs})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8123)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()

    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}/"
    sys.stderr.write(f"[server] listening on {url}\n")
    sys.stderr.write(f"[server] anthropic key: {'set' if os.environ.get('ANTHROPIC_API_KEY') else 'NOT SET (LLM panels will be skipped)'}\n")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        sys.stderr.write("\n[server] stopping\n")
        srv.shutdown()


if __name__ == "__main__":
    main()
