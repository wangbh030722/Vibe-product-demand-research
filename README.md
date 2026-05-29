# Vibe 品类需求研究 · Category Demand Research

输入一个产品想法 → 自动联网调研真实用户声音 → 产出一份**可交互、中英双语、可下载**的品类研究报告:
判断这个需求是不是真的,谁在玩,痛点在哪,机会缝隙在哪。

报告形态(MiroFish 启发的 lens 布局):**左侧常驻知识图谱 + 右侧 6 个视角 + 底部完整线性报告**,
图谱可缩放/拖拽/点节点切视角,右上角一键中英切换 + 导出 PDF。

> 在线示例(只读,看效果):
> https://wangbh030722.github.io/Vibe-product-demand-research/dist/index.html

---

## 快速开始(clone 即用)

```bash
git clone https://github.com/wangbh030722/Vibe-product-demand-research.git
cd Vibe-product-demand-research

# 1. 依赖(只需要 jsonschema,其余 stdlib)
python3 -m pip install -r requirements.txt

# 2. 配置 LLM key(DeepSeek / 任意 OpenAI 兼容 API)
cp .env.example .env
#   编辑 .env,至少填 OPENAI_API_KEY

# 3. 启动网页版(输入框 → 报告)
make app
#   自动打开 http://localhost:8200,输入想法,约 40-60 秒出报告
```

`.env` 最小配置:
```bash
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_API_KEY=sk-你的key
OPENAI_MODEL=deepseek-chat
```
> 任何 OpenAI 兼容 API 都行(DeepSeek / 通义 / Kimi / GLM / 本地 Ollama / OpenAI)。
> `.env` 已被 gitignore,不会泄漏。

---

## 三种用法

### 1. 网页版(推荐) · `make app`
浏览器输入框填想法 → 出报告,零复制粘贴。这是日常用法。

### 2. 命令行 · `make research`
```bash
make research IDEA="智能宠物喂食器" SLUG=pet-feeder
make research IDEA="AI 录音吊坠" SLUG=pendant MODE=NON_STOCK   # 强制非存量模式
```
跑完输出 `dist/<slug>.html`,并刷新 `dist/index.html` 索引。

### 3. 纯聊天 + Viewer(无终端) · 给只用 Claude/ChatGPT 的人
见 `docs/chat-usage.md`:把研究指令贴进 ChatGPT Custom GPT / Claude Project,
让它联网产出 JSON → 粘进 `dist/viewer.html` 渲染。适合不装工具的用户。

---

## 数据从哪来(重要)

采集**真实用户声音**,优先级:Reddit > Hacker News >(可选)电商/媒体。

- **Reddit 是消费类产品的主力数据源**。Reddit 封机房/VPN 的出口 IP:
  - 你在**住宅宽带**直连(美/欧常见)→ 直接通,无需任何配置
  - 你在**国内 + 机房代理节点** → 可能 403,这是你网络环境的问题,不影响别人
  - 想在被封环境下也能爬 → 配 **Reddit 官方 API(免费)**,见 `docs/reddit-oauth.md`
- **Hacker News** 通过公开 Algolia API,稳定但偏技术话题。
- 采集器走 curl,自动适配代理/TLS;LLM 调用优先直连(国内 API 不需代理)。

> 诚实说明:纯本地免 key 抓取对反爬天生脆弱。信号稀薄时报告会如实降级 verdict
> (`insufficient` / `partial`),不编造数据。

---

## 评判尺度(evidence-rules)

`references/evidence-rules.md` 是单一事实源:

- **真实原话才算证据**:媒体/分析师/博主写的算 editorial,不计入 raw voices。
- **`raw_voices == 0` 强制 `insufficient`** —— 不允许"基于媒体报道"下需求结论。
- **反证据必填** —— 不允许只列支持证据。
- 自动校验:`scripts/validate_data.py` 跑 schema + 交叉引用 + 证据 gating。

---

## 命令一览

```bash
make app           # 本地网页版:输入框 → 报告
make research IDEA="..." SLUG=foo [MODE=NON_STOCK] [MARKET="US + CN"]
make all           # 校验 + 渲染所有 data/*.json + 刷新 index
make validate      # 只校验数据
make serve         # 本地静态预览 dist/
make clean         # 清 dist/
```

---

## 项目结构

```
scripts/
  app.py              本地网页版(输入框 → 报告)
  research.py         全自动流水线:scope→collect→curate→cluster→synth→assemble
  llm_client.py       OpenAI 兼容 LLM 客户端(curl fallback + 代理自适应)
  validate_data.py    schema + 交叉引用 + 证据 gating 校验
  render_report.py    data JSON → dist/<slug>.html(注入模板)
  render_index.py     生成 dist/index.html + 拷贝 viewer 资源
  translate_data.py   回填英文(_en 字段,支持中英切换)
core/collect/
  reddit.py           Reddit 采集(支持官方 OAuth API)
  hn.py               Hacker News 采集
  ddg.py              DuckDuckGo 搜索(备用)
templates/
  lens-report-template.html   报告模板(数据驱动,中英双语)
  category-research-spec.md    报告输出规范(§1-§9)
  pipeline/ crawler/           聚类 prompt + 采集脚手架
schemas/report-data.schema.json   报告数据契约
data/*.json             各品类报告数据(含示例)
dist/                   渲染产物 + viewer.html(可直接打开/部署)
docs/
  chat-usage.md         聊天客户端用法(Custom GPT / Project + Viewer)
  reddit-oauth.md       Reddit 官方 API 配置(5 分钟)
  ROADMAP.md            产品级路线图(P0/P1/P2)
```

---

## 已知限制

- **电商 VOC(Amazon/京东)未接**:有反爬,目前靠 Reddit + HN。`templates/crawler/collect_marketplace.py` 留了 adapter 接口。
- **Reddit 在机房 IP 上会 403**:住宅 IP 或官方 OAuth 解决(见上)。
- **托管成网站**:服务器共用机房 IP,Reddit 对全员失效 → 需 OAuth 或住宅代理。当前以**本地工具**形态分发最稳。

---

## License

MIT
