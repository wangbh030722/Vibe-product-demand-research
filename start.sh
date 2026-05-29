#!/bin/bash
# Vibe 品类研究 · 一键启动(Linux/macOS 终端:bash start.sh)
cd "$(dirname "$0")" || exit 1
PY=""
for c in python3 python; do command -v "$c" >/dev/null 2>&1 && { PY="$c"; break; }; done
[ -z "$PY" ] && { echo "✗ 需要 Python 3,请先安装。"; exit 1; }
echo "▶ 安装依赖…"; "$PY" -m pip install -q -r requirements.txt 2>/dev/null || "$PY" -m pip install -q jsonschema
[ ! -f .env ] && [ -f .env.example ] && cp .env.example .env
echo "▶ 启动 http://localhost:8200(Ctrl+C 停止)"
exec "$PY" scripts/app.py
