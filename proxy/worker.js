/**
 * Vibe LLM Proxy — Cloudflare Worker
 *
 * Holds YOUR DeepSeek (or any OpenAI-compatible) key server-side so friends
 * can use the tool free WITHOUT ever seeing your key. Friends' local app
 * points OPENAI_BASE_URL at this Worker and sends a shared access token; the
 * Worker checks the token, then forwards to DeepSeek with the real key.
 *
 * Deploy: see proxy/README.md (2 secrets: UPSTREAM_KEY, ACCESS_TOKEN).
 *
 * Endpoints:
 *   POST /v1/chat/completions   (and /chat/completions) → forwarded upstream
 *   GET  /                      → health check
 *
 * Protections:
 *   - Access token gate (friends' app must send Bearer <ACCESS_TOKEN>)
 *   - Per-IP sliding rate limit (in-memory per isolate; coarse but enough)
 *   - Only proxies chat/completions; nothing else
 */

const UPSTREAM_DEFAULT = "https://api.deepseek.com/v1";

// coarse in-memory rate limit (per Worker isolate)
const HITS = new Map();
const WINDOW_MS = 60_000;
const MAX_PER_WINDOW = 40; // per IP per minute

function rateLimited(ip) {
  const now = Date.now();
  const arr = (HITS.get(ip) || []).filter((t) => now - t < WINDOW_MS);
  arr.push(now);
  HITS.set(ip, arr);
  return arr.length > MAX_PER_WINDOW;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // CORS preflight (in case called from a browser)
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: cors() });
    }

    if (request.method === "GET" && url.pathname === "/") {
      return json({ ok: true, service: "vibe-llm-proxy" });
    }

    if (request.method !== "POST" || !url.pathname.endsWith("/chat/completions")) {
      return json({ error: "not found" }, 404);
    }

    // 1) access-token gate
    const auth = request.headers.get("Authorization") || "";
    const token = auth.replace(/^Bearer\s+/i, "").trim();
    if (!env.ACCESS_TOKEN || token !== env.ACCESS_TOKEN) {
      return json({ error: "unauthorized: bad or missing access token" }, 401);
    }

    // 2) rate limit
    const ip = request.headers.get("CF-Connecting-IP") || "unknown";
    if (rateLimited(ip)) {
      return json({ error: "rate limited, slow down" }, 429);
    }

    // 3) forward to upstream with the REAL key (never exposed to caller)
    if (!env.UPSTREAM_KEY) {
      return json({ error: "server misconfigured: UPSTREAM_KEY unset" }, 500);
    }
    const upstream = (env.UPSTREAM_BASE_URL || UPSTREAM_DEFAULT).replace(/\/$/, "");
    const body = await request.text();

    const resp = await fetch(`${upstream}/chat/completions`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.UPSTREAM_KEY}`,
        "Content-Type": "application/json",
      },
      body,
    });

    // pass through status + body, add CORS
    const out = await resp.text();
    return new Response(out, {
      status: resp.status,
      headers: { "Content-Type": "application/json", ...cors() },
    });
  },
};

function cors() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
    "Access-Control-Allow-Headers": "Authorization, Content-Type",
  };
}
function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json", ...cors() },
  });
}
