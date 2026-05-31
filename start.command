#!/bin/bash
# Vibe 品类研究 · 一键启动(好友双击此文件即可,macOS)
# 自动:检查 Python → 装依赖 → 启动网页版 → 打开浏览器
cd "$(dirname "$0")" || exit 1

echo "▶ Vibe 品类研究 — 启动中…"

# 1. 找 Python 3
PY=""
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then
  echo "✗ 没找到 Python。请先装 Python 3:https://www.python.org/downloads/"
  echo "  装完后再双击本文件。"
  read -r -p "按回车退出…" _
  exit 1
fi

# 2. 依赖
echo "▶ 安装依赖(jsonschema)…"
"$PY" -m pip install -q -r requirements.txt 2>/dev/null || "$PY" -m pip install -q jsonschema

# 3. .env 检查
if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    cp .env.example .env
    echo "⚠ 没有 .env,已从模板创建。如果作者没预填,请编辑 .env 填 OPENAI_BASE_URL/KEY。"
  fi
fi

# 4. 启动
echo "▶ 启动网页版,浏览器将自动打开 http://localhost:8200"
echo "  (关闭此窗口即停止)"
"$PY" scripts/app.py
