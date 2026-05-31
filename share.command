#!/usr/bin/env bash
# ============================================================================
# VIBE 产品需求研究 · 一键内测分享
# 双击本文件(或终端运行 ./share.command):
#   1. 在本机启动 App
#   2. 开一条 Cloudflare 免费公网隧道
#   3. 打印一个 https 链接 —— 把它发给好友,他们用浏览器打开就能用,零安装。
# 关掉这个窗口 / 按 Ctrl+C → 链接立即失效。
# ============================================================================
set -uo pipefail
cd "$(cd "$(dirname "$0")" && pwd)"

PORT=8200
BIN_DIR="./bin"
CF="$BIN_DIR/cloudflared"
APP_LOG="/tmp/vibe-app.log"
CF_LOG="/tmp/vibe-tunnel.log"

cleanup() { echo; echo "正在停止…"; kill "${APP_PID:-}" "${CF_PID:-}" 2>/dev/null; exit 0; }
trap cleanup INT TERM

# 0) sanity: .env with a default key
if [ ! -f .env ]; then
  echo "⚠ 未找到 .env(里面要有 OPENAI_API_KEY)。先配置好 .env 再分享。"
  exit 1
fi

# 1) ensure cloudflared (tiny one-time download, no account needed)
if [ ! -x "$CF" ]; then
  mkdir -p "$BIN_DIR"
  case "$(uname -m)" in arm64) A=arm64 ;; x86_64) A=amd64 ;; *) A=amd64 ;; esac
  echo "首次使用:下载公网隧道工具 cloudflared ($A)…"
  URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-${A}.tgz"
  if ! curl -L --fail --silent --show-error -o /tmp/cf.tgz "$URL"; then
    echo "✗ 下载失败,请检查网络后重试。"; exit 1
  fi
  tar xzf /tmp/cf.tgz -C "$BIN_DIR" && chmod +x "$CF"
fi

# 2) start the local app
echo "启动本地 App(端口 $PORT)…"
python3 scripts/app.py >"$APP_LOG" 2>&1 &
APP_PID=$!
sleep 2
if ! curl -s -o /dev/null "http://localhost:$PORT/"; then
  echo "✗ App 没起来,看日志:$APP_LOG"; cat "$APP_LOG"; cleanup
fi

# 3) open the public tunnel
echo "开启公网链接(Cloudflare,免费)…"
: > "$CF_LOG"
"$CF" tunnel --url "http://localhost:$PORT" >"$CF_LOG" 2>&1 &
CF_PID=$!

# 4) wait for the URL, then show it prominently
URL=""
for _ in $(seq 1 40); do
  URL="$(grep -Eo 'https://[a-z0-9-]+\.trycloudflare\.com' "$CF_LOG" | head -1)"
  [ -n "$URL" ] && break
  sleep 1
done

echo
echo "════════════════════════════════════════════════════════════"
if [ -n "$URL" ]; then
  echo "  ✅ 把这个链接发给好友,浏览器打开即可使用:"
  echo
  echo "      $URL"
  echo
  echo "  · 零安装,不用配 key(用你的默认 key,注意 API 用量)"
  echo "  · 好友也可在「高级」里填自己的 key"
else
  echo "  ✗ 没拿到链接,日志在 $CF_LOG"
fi
echo "  ⚠ 这个窗口别关 —— 关掉或 Ctrl+C,链接就失效。"
echo "════════════════════════════════════════════════════════════"
echo
wait "$CF_PID"
