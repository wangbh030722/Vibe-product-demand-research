# 配 Reddit 官方 API(5 分钟,强烈推荐)

## 为什么需要

不配的话,采集器是**免授权抓 www.reddit.com** —— 这条路经常被 Reddit 按 IP 封(403),
尤其走代理/VPN 出口时几乎必封。结果:消费类产品(宠物喂食器、睡眠耳塞…)的报告
**只能靠 HN(程序员论坛)撑**,声音稀少(常常 ≤10 条)。

配了官方 API 之后,采集器走 **oauth.reddit.com**:
- 即使你的 IP 被网页端封了,官方 API 照样能读
- 速率额度高得多
- 每份报告的真实用户声音从个位数 → 30-50+ 条

## 怎么配(~5 分钟)

1. 登录 Reddit,打开 **https://www.reddit.com/prefs/apps**
2. 拉到底,点 **"create another app..."** / **"are you a developer? create an app..."**
3. 填写:
   - **name**:随便,如 `vibe-research`
   - **类型**:选 **script**(或 web app,二者都行)
   - **redirect uri**:填 `http://localhost:8200`(随便填个合法 URL,read-only 用不到)
   - 其它留空
4. 点 **create app**
5. 创建后能看到:
   - **client id**:在 app 名字下方那串(`personal use script` 下面的 14 位字符)
   - **secret**:标着 `secret` 的那串
6. 把它们填进项目根目录的 **`.env`**:
   ```
   REDDIT_CLIENT_ID=你的client_id
   REDDIT_CLIENT_SECRET=你的secret
   ```

完成。下次跑 `make app` / `make research`,采集器会自动检测到 → 走官方 API
(终端会打印 `[reddit] OAuth token acquired (official API)`)。

## 验证

```bash
# 直接测采集器(配好 .env 后)
python3 core/collect/reddit.py --subs dogs cats --limit 5 --out /tmp/r.jsonl
wc -l /tmp/r.jsonl    # 应该 > 0(没配 OAuth 时这里常常是 0)
```

## 还是不行?

- 如果连官方 API 都报错,可能是你的**代理出口 IP 连 oauth.reddit.com 都被封**,
  或代理把 Reddit 整个域名屏蔽了。换一个 Clash 节点(住宅 IP)再试。
- 或者干脆走**聊天指令包路径**(`docs/chat-usage.md`):让 Claude/ChatGPT 联网收集,
  它们的搜索基建比本地抓取稳得多,完全绕开 IP 封锁。

## 隐私

`.env` 已被 `.gitignore`,你的 client_id/secret 不会进 git、不会泄漏。
