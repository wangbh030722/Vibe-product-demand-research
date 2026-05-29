# LLM 代理(藏你的 key,好友免费用)

一个**极小的 Cloudflare Worker**:好友的本地 app 把 LLM 请求发到这个代理,代理
用**你的 DeepSeek key**(藏在服务器,好友永远看不到)转发给 DeepSeek。

```
好友的机器(本地 app)
  ├─ 抓 Reddit/HN     ← 用好友自己的 IP(Reddit 通)
  └─ LLM 调用 ────────→ 你的 Cloudflare 代理 ──(你的 key)──→ DeepSeek
                          ↑ 一直在线,免费额度,不依赖你的终端
```

满足你的三条:好友的 IP 抓 Reddit ✓ · 你的 key 不暴露 ✓ · 不依赖你终端 ✓ · 好友零 key ✓

---

## 部署(~10 分钟,一次性)

### 前置
- 一个 **Cloudflare 账号**(免费)
- 本机有 Node(`npx` 可用)

### 步骤
```bash
cd proxy

# 1. 登录 Cloudflare(浏览器弹出授权)
npx wrangler login

# 2. 设置两个 secret(交互式输入,不会进 git)
npx wrangler secret put UPSTREAM_KEY
#    粘贴你的真实 DeepSeek key(sk-...)
npx wrangler secret put ACCESS_TOKEN
#    自己编一个分享口令,如 vibe-friends-2026(好友 app 会用它)

# 3. 部署
npx wrangler deploy
```

部署完会打印你的代理地址,形如:
```
https://vibe-llm-proxy.<你的子域>.workers.dev
```

### 验证
```bash
curl -s -X POST https://vibe-llm-proxy.<你的子域>.workers.dev/v1/chat/completions \
  -H "Authorization: Bearer vibe-friends-2026" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"hi"}],"max_tokens":5}'
```
返回正常 JSON = 成了。

---

## 然后:让好友的 app 指向代理

好友的 `.env` 这样填(**不含你的真实 key**):
```bash
OPENAI_BASE_URL=https://vibe-llm-proxy.<你的子域>.workers.dev/v1
OPENAI_API_KEY=vibe-friends-2026          # 就是上面的 ACCESS_TOKEN,不是真 key
OPENAI_MODEL=deepseek-chat
```

你把这份 `.env` 连同代码一起发给好友(见 `docs/share-with-friends.md`)。
里面只有**分享口令**,没有你的真 DeepSeek key —— 泄漏了你也只需在 Cloudflare
改 `ACCESS_TOKEN` 即可作废,真 key 始终安全。

---

## 成本 & 限流

- Cloudflare Workers 免费额度:**10 万次请求/天**,代理转发绰绰有余
- DeepSeek 账单仍是你的(好友用的是你的 key)——一份报告约 5-6 次调用,几分钱
- Worker 内置每 IP 每分钟 40 次限流;想更严可改 `worker.js` 的 `MAX_PER_WINDOW`
- 想停掉:Cloudflare 控制台删掉 Worker,或改 `ACCESS_TOKEN` 让旧口令失效
