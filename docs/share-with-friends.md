# 发给好友测试(全流程,用你的 key,好友免费)

目标:好友在**自己机器**跑(用他的 IP 抓 Reddit),**用你封装的 key**(免费,看不到你的真 key),**不依赖你的终端**。

## 一次性准备(你做)

1. **部署 LLM 代理**(藏你的 key):照 `proxy/README.md`,~10 分钟,得到代理地址 +
   一个分享口令(ACCESS_TOKEN)。
2. **准备好友用的 `.env`**(只含代理地址 + 口令,**没有你的真 key**):
   ```
   OPENAI_BASE_URL=https://vibe-llm-proxy.你的子域.workers.dev/v1
   OPENAI_API_KEY=你设的分享口令
   OPENAI_MODEL=deepseek-chat
   ```

## 打包发给好友

把整个项目文件夹(**带上这份准备好的 `.env`**)打包发给好友:
```bash
cd ~
zip -r vibe-research.zip Vibe-product-demand-research \
    -x "*/.git/*" "*/collected/*" "*/dist/*.json"
# 确保 .env 在包里(它默认被 .gitignore,但 zip 会带上本地文件)
```
> 注意:这份 `.env` 里**只有分享口令,没有你的真 DeepSeek key** —— 安全。
> 真 key 只在你的 Cloudflare 代理上。口令泄漏了,你改一下代理的 ACCESS_TOKEN 即可作废。

## 好友怎么用

1. 解压 `vibe-research.zip`
2. **macOS**:双击文件夹里的 `start.command`
   **Windows/Linux 或终端**:`bash start.sh`
3. 自动装依赖 → 浏览器打开 `http://localhost:8200`
4. 输入产品想法 → 等 40-60 秒 → 出报告(全流程)
5. 报告右上角可切中英文 / 下载 PDF;想用自己的 key 也能在「高级」里填

好友需要装 **Python 3**(脚本会提示)。除此之外零配置。

## 为什么好友能抓到 Reddit 而你不行

好友在**自己的住宅 IP** 上跑,Reddit 不封住宅 IP;你之前是机房代理出口 IP 被封。
所以同一套代码,好友那边 Reddit 数据正常,你那边偏少。

## 出问题排查

| 好友遇到 | 原因 / 解法 |
|---|---|
| 没找到 Python | 装 Python 3:python.org/downloads,装完重双击 |
| 连不上后端 / Failed to fetch | `start` 那个窗口关了 → 重开 |
| LLM 报 401 | 代理口令对不上 → 确认 `.env` 的 OPENAI_API_KEY = 你设的 ACCESS_TOKEN |
| Reddit 数据还是少 | 好友也在用代理/VPN?让他直连或换住宅节点 |
