# Reddit API Key 详细配置方案(~5 分钟)

> 配完后,采集器走 Reddit **官方 API**,绕开网页端的 IP 封锁,消费类产品报告的
> 用户声音从个位数 → 30-50+ 条。这把 key 只读公开数据,不发帖、不是机器人。

---

## 第一步:登录 Reddit

用你的 Reddit 账号登录 https://www.reddit.com 。
(没有账号就先注册一个,邮箱验证即可。)

---

## 第二步:打开开发者应用页

访问 **https://www.reddit.com/prefs/apps**
(打不开就用老版:https://old.reddit.com/prefs/apps )

页面拉到最底部,点蓝色按钮:
**「are you a developer? create an app...」** 或 **「create another app...」**

---

## 第三步:填表(关键,逐字段说明)

| 字段 | 填什么 | 说明 |
|---|---|---|
| **name** | `vibe-research` | 随便,自己认得就行 |
| **类型(单选按钮)** | 选 **script** | ⚠️ 必须选 script(个人脚本用) |
| **description** | 留空 | 不用填 |
| **about url** | 留空 | 不用填 |
| **redirect uri** | `http://localhost:8200` | ⚠️ 必填项,随便填个合法 URL,只读用不到它 |

填完点底部 **「create app」**。

---

## 第四步:复制凭证(这步最多人踩坑)

创建后,页面出现一个灰框,长这样:

```
  vibe-research
  personal use script
  abcd1234EFGH56            ← 【这串没有标签的字符 = client_id】⚠️
  
  secret    xy9876_ZyXwVuTsRqPoNmLkJiHg   ← 【这个 = client_secret】
  ...
```

**两个最容易搞错的点:**
1. **client_id** 是名字下方、`personal use script` 那行下面那串**没有任何标签**的字符(约 14-22 位)。很多人找不到它,因为它没写"client_id"。
2. **secret** 是明确标着 `secret` 的那串。

---

## 第五步:填进 `.env`

打开项目根目录的 `.env` 文件(没有就 `cp .env.example .env`),填:

```bash
REDDIT_CLIENT_ID=abcd1234EFGH56
REDDIT_CLIENT_SECRET=xy9876_ZyXwVuTsRqPoNmLkJiHg
```

**(推荐)再加上你的 Reddit 登录** —— script 类型 app 用密码授权最稳:
```bash
REDDIT_USERNAME=你的reddit用户名
REDDIT_PASSWORD=你的reddit密码
```
> 加了用户名密码 → 走官方推荐的 password grant(最可靠)
> 不加 → 走 app-only client_credentials(只填 id+secret 也能用,但偶尔拿不到 token)

---

## 第六步:验证

```bash
python3 core/collect/reddit.py --subs dogs cats --limit 5 --out /tmp/r.jsonl
```

- 成功:终端打印 `[reddit] OAuth token acquired (official API)`,`/tmp/r.jsonl` 有内容
- 看行数:`wc -l /tmp/r.jsonl`(>0 就成了;没配 OAuth 时这里常是 0)

成功后,`make app` 跑任何想法都会自动用官方 API,数据量明显变多。

---

## 排错

| 现象 | 原因 / 解法 |
|---|---|
| `OAuth token failed` + 一段 401 | id/secret 填错,或漏了一位。回第四步重新复制 |
| `OAuth token failed` + `unsupported_grant_type` | 只填了 id+secret 时偶发 → 补上 `REDDIT_USERNAME/PASSWORD`(第五步) |
| token 拿到了,但抓取还是 0 | 你的代理出口 IP 连官方 API 也被封 → 换 Clash 住宅节点,或走聊天路径(见 chat-usage.md) |
| 完全连不上 reddit.com | 代理把 reddit 整个屏蔽了 → 换节点 |

---

## 安全 & 隐私

- `.env` 已被 `.gitignore`,你的 id/secret/密码**不会进 git、不会上传**
- 这把 key 是**只读**的:程序只用它读公开帖子,不会用你账号发任何东西
- 担心密码的话,可以只填 id+secret(client_credentials 模式),不填用户名密码

---

## 这把 key 是给谁用的?(重要概念)

- **现在(本地 `make app`)**:这是**你自己的** key,只在你电脑上用,抓你自己的数据
- **未来(公网网站)**:如果做成网站给别人用,要么共用你这把 key(额度/账单算你的),
  要么让访客各填各的。届时再定。

现在配的就是你本地自用的,放心配。
