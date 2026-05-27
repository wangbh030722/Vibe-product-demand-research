# Vibe Category Research · Product-Grade Roadmap (P0 + P1)

> 从当前 prototype(`demo-ai-health-ring-lens.html` 单文件,数据手搓)走到"团队可以用、能跑多个品类、可分享 / 打印 / 移动端可看"的产品级形态。

**Source of truth**:本文件。所有 P0+P1 任务对应 `TaskCreate` 任务 ID,完成后在此打勾。

---

## 当前状态(2026-05-27)

- ✅ Lens 范式 spec(`templates/category-research-spec.md` §9)写完
- ✅ Prototype 单文件 demo(`demo-ai-health-ring-lens.html`)73 KB,self-contained
- ✅ 完整 §1-§6 fallback 长报告
- ✅ 滚轮缩放 / 拖拽平移 / hover tooltip / 3 色族配色
- ❌ 数据从 inline JSON 来 —— 不能跨品类复用
- ❌ Marketplace VOC 抓取 / LLM 聚类没接通
- ❌ 没 PDF / 移动端 / deeplink

---

## P0 · "能用起来"(约 1 个月)

没有 P0,所谓"产品"只是 demo。每份新报告都要花一周手搓 JSON。

### P0.1 · JSON schema + 验证 + 友好错误

**任务 #10**

- 在 `schemas/report-data.schema.json` 定义 JSON Schema Draft-07
  - `meta` { idea, mode: EXISTING|NON_STOCK, timestamp, target_market }
  - `players[]` { id, name, color, size, x, y, summary, status, price }
  - `themes[]` { id, label, color, size, x, y, polarity: pos|pain|neutral, summary }
  - `voices[]` { id, player, title, score, url, sentiment, themes[], lang? }
  - `opportunity` { id, label, size, x, y, summary }
  - `edges[]` { from, to, w (1-3) }
  - `marketplace[]` (新增)、`risks[]`(新增)、`paths[]`(新增)、`failures[]`(新增)
- 在 `scripts/validate_data.py` 写 Python validator(`jsonschema` 库)
- 修改 lens HTML:JSON.parse 或 schema 失败时显示**友好错误页**,标出哪个字段、哪一行
- 加入 evidence-rules.md 硬约束:
  - `voices_raw > 0` 才能 `status: real` / `partially_supported`
  - voice.themes 引用必须 ∈ themes[].id
  - edge.from / edge.to 必须 ∈ 所有节点 id

**Done when**:
- 现有 ring 数据通过 validator,0 错误
- 故意改坏一个字段,validator 报具体行号 + 字段路径
- HTML 端打开坏数据,看到友好错误页(不白屏)

### P0.2 · HTML 模板化 · 数据外置

**任务 #11**

当前数据 hardcode 在 HTML 里。要变模板:

- 拆出 `data/health-ring.json` —— 唯一真相源,符合 schema
- HTML 改成 `templates/lens-report-template.html`,startup 时:
  1. 从 `?data=` URL 参数读路径,或默认 `./data/{slug}.json`
  2. fetch + validate
  3. 用数据动态渲染:overview key findings、player cards、voice rows、§1-§6 fallback 表格
- 删掉 lens 内的所有 hardcoded 文本 —— 全部由数据驱动
- 模板用 vanilla JS 占位符渲染(`{{...}}`),无构建依赖

**Done when**:
- `data/health-ring.json` 独立存在,与 HTML 解耦
- 改 JSON 立即反映到 HTML,无需改模板
- 用同一份 HTML + 不同 JSON,能开出不同品类报告

### P0.3 · Marketplace VOC 抓取脚手架

**任务 #12**

`templates/crawler/` 已有 Reddit + HN。要补的最重要一块 = Marketplace。但真 Amazon 抓取涉及反爬虫 + 法律:

- 写 `templates/crawler/collect_marketplace.py` 带 adapter 接口:
  ```
  class MarketplaceAdapter(Protocol):
    def search(self, query: str, limit: int) -> list[Listing]
    def reviews(self, listing_id: str, limit: int) -> list[Review]
  ```
- 实现 3 个 adapter:
  - `AmazonAdapter`(需 proxy + legal sign-off — 先标记 `IMPL_PENDING`)
  - `TrustpilotAdapter`(公开 API,可直接做)
  - `RedditMarketplaceAdapter`(把 r/{brand} 当 marketplace 用 — 兜底)
- 提供 `--fixture` 模式,从 `fixtures/marketplace/*.json` 读测试数据,不打真 API
- 输出格式严格符合 P0.1 schema 的 `marketplace[]` 段

**Done when**:
- 至少 Trustpilot + Reddit 兜底两个 adapter 可工作
- 跑出来的 JSON 通过 schema 验证
- Amazon adapter 留接口 + TODO,文档清楚说明阻塞原因

### P0.4 · LLM 主题聚类管道脚手架

**任务 #13**

当前从 voice 到 theme + edges 全人工。要自动化:

- `templates/pipeline/cluster_themes.py`:
  - 输入:`{voices: [...], collection_meta: {...}}`
  - 输出:`{themes: [...], edges: [...], voices_with_themes: [...]}`
- 使用 OpenAI 兼容接口(`OPENAI_BASE_URL` + `OPENAI_API_KEY` 环境变量)
- Prompt 内容固定为 repo 内 `templates/pipeline/prompts/cluster.txt`,可被替换
- 温度 0.2,token 预算每千 voice 约 8k input + 3k output
- 加 `--cached` 模式,把 LLM 响应缓存到 `fixtures/clusters/{hash}.json`,重跑不再付费
- 加 `--dry-run` 模式,跳过 LLM,从 fixture 出

**Done when**:
- 喂 14 条 ring voice,产出 8 主题 + 30 边 与人工版结构相同
- `--cached` 模式可重复跑 0 费用
- Prompt 输出 JSON 通过 schema 验证(否则 retry 3 次)

### P0.5 · 渲染编排 + 3 个真实品类

**任务 #14**

- `scripts/render_report.py`:
  - 输入 slug(例如 `health-ring`)
  - 流程:`data/{slug}.json` → validate → 注入模板 → 写 `dist/{slug}.html`
  - 同时输出 PDF(用 playwright 或 weasyprint)
- 跑出 3 份完整品类报告:
  - `dist/health-ring.html`(EXISTING,已有数据)
  - `dist/ai-glasses.html`(EXISTING,新建)
  - `dist/ai-recording-pendant.html`(NON-STOCK,新建)
- 每份附 PDF
- 写 `dist/index.html` 列出所有报告,作为入口

**Done when**:
- 一条命令 `python scripts/render_report.py health-ring` 出报告
- 3 个品类都能开,UI 范式一致
- 验证 NON-STOCK 范式与 EXISTING 范式数据形态兼容

---

## P1 · "能分发"(约 1 个月)

### P1.1 · URL deeplink + 浏览器历史

**任务 #15**

- `body[data-lens]` / `[data-selected-id]` / `[data-view]` 全部同步到 URL hash
  - 例:`#lens=players&id=oura&view=split`
- `hashchange` 事件 → 反向更新 body
- `pushState` 在每次状态变化时调用,`popstate` 恢复
- 默认链接(无 hash)= overview / split / no-selection
- 分享场景:把链接发给同事,**打开就是当时看的那个状态**
- 失败优雅:hash 写无效 lens id,fallback 到 overview

**Done when**:
- 复制 URL `...#lens=voices&id=t.medical`,新窗口打开 = 同样状态
- 浏览器 back / forward 按钮在 lens / selection 之间正确切换
- DevTools 改 hash,UI 立刻响应

### P1.2 · PDF 导出 + 打印样式

**任务 #16**

- `@media print` 全面打磨:
  - 隐藏 header view-switcher / lens tabs / graph 控件
  - 自动展开 fallback 长报告
  - 章节 `h2` 前 `page-break-before: always`
  - Footer 显示报告标题 + 页码 + 数据采集日期
  - 表格不被切断(`break-inside: avoid`)
  - voice 引用块加分页友好设计
- 加 "Save as PDF" 按钮(调 `window.print()`)
- 用 playwright 在 CI 跑 PDF 导出测试,产物归档

**Done when**:
- Chrome → 打印 → 保存 PDF,30 页内,排版整齐无切断
- 任何 lens 状态下都能正确导出整份长报告

### P1.3 · 移动端最低可用(<1000px)

**任务 #17**

- 媒体查询 `@media (max-width: 999px)`:
  - 顶层不再左右 split,改 vertical tab 切换:`[图谱] [概览] [玩家] [声音] [机会] [策略] [风险]`
  - Graph 占满 viewport 宽,viewBox 调整为竖屏比例
  - 触屏:
    - **tap node** = 选中(替代 click)
    - **long-press node** = tooltip(替代 hover)
    - **pinch** = zoom(替代 wheel)
    - **two-finger drag** = pan(单指 drag 留给页面滚)
- 字号 + padding 适配
- 用 playwright 切换 iPhone 14 / Pixel 7 viewport 验证

**Done when**:
- iPhone Safari 模拟器打开,所有 lens 可达
- Graph 可缩放 + 平移
- 内容不溢出,无横向滚动条

---

## 不在 P0 / P1 范围(明确推后)

- P2:节点聚合 / level-of-detail(>100 节点)
- P2:a11y 完整审计(axe-core CI、键盘导航)
- P2:链接归档(web.archive.org 集成)
- P2:Counter-evidence + confidence-per-claim 渲染
- P3:多主题(editorial / data-dense)
- P3:协作注释 / 版本 diff
- P3:嵌入模式 / Slide 导出

---

## 进度看板

| ID  | 任务                                           | 状态     |
|-----|------------------------------------------------|----------|
| #9  | 写 P0+P1 roadmap(本文件)                     | 进行中   |
| #10 | P0.1 JSON schema + 验证                        | 待开     |
| #11 | P0.2 HTML 模板化                               | 待开     |
| #12 | P0.3 Marketplace adapter 脚手架                | 待开     |
| #13 | P0.4 LLM 聚类管道                              | 待开     |
| #14 | P0.5 编排 + 3 品类                             | 待开     |
| #15 | P1.1 URL deeplink                              | 待开     |
| #16 | P1.2 PDF + 打印                                | 待开     |
| #17 | P1.3 移动端 ≤1000px                            | 待开     |

---

## 执行节奏与依赖

```
P0.1 (schema)  ──┐
                 ├──▶ P0.2 (template) ──▶ P0.5 (orchestrator + 3 categories)
P0.3 (crawler) ──┤                                    ▲
P0.4 (LLM)     ──┘                                    │
                                                      │
P1.1 (deeplink)  ─────────────────────────────────────┤
P1.2 (PDF)       ─────────────────────────────────────┤
P1.3 (mobile)    ─────────────────────────────────────┘
```

- P0.1 是 P0.2 / P0.5 的硬依赖
- P0.3 / P0.4 可并行
- P1 三项不依赖 P0(基于现有 prototype 也能做)

---

## 外部依赖与阻塞点

| 依赖                  | 用途              | 状态                       |
|-----------------------|-------------------|----------------------------|
| OpenAI API key        | P0.4 LLM 聚类     | 等用户配置                 |
| Amazon scraping proxy | P0.3 真实 marketplace | 留接口,等法律审计         |
| Trustpilot API token  | P0.3 适配器       | 公开 API,自动获取         |
| 移动设备真机测试       | P1.3              | 用 playwright emulation 兜底 |
