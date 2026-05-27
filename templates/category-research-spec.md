# Category Research Report — Output Spec

为产品团队 / 创始人 / 既有玩家产品总监做品类调研的标准模板。两种模式:

- **EXISTING 模式** — 存量市场,有零售评论 / 多家在售玩家 / 真实用户社区
- **NON-STOCK 模式** — 非存量市场,品类刚出现,玩家少 / 数据稀疏 / 多在 crowdfunding / waitlist 阶段

输出形态:**自包含 HTML 报告**(无后端依赖),A4 / 笔记本 / 平板尺寸均可读。

---

## 1 · 共用结构(两种模式都有)

### 1.1 Masthead
```
{机构名} · CATEGORY DEEP DIVE · {子赛道}    Brief №{ID}   {YYYY/MM/DD}
```

### 1.2 Cover
- 单句**反共识 thesis**(serif 大字)
- 一段 deck(serif italic 副标)
- 读者标签(`<strong>新进入者产品团队 / 创始人 / 既有玩家产品总监</strong>`)

### 1.3 TL;DR 速读盒
- **4 格 verdict**:品类是否真实 / 是否值得切入 / 推荐切入点 / 窗口期
- **4 条编号 key findings**(每条 ≤ 80 字,带 *em-strong* 关键短句)

### 1.4 章节编号制
```
§1 品类拆解         · 1.1 / 1.2 / 1.3
§2 用户洞察         · 2.1 / 2.2 / 2.3 / 2.4
§3 竞品全景         · 3.1 / 3.2 / 3.3
§4 机会缝隙         · 4.1 / 4.2 / 4.3
§5 入场能力栈       · 4 卡(must / critical / standard / optional)
§6 风险与挑战       · R-01 to R-05
附录                · A 数据采集方法 / B 一手 voice 完整清单 / C marketplace VOC 来源
```

每章前导:`§N · {一句话副标 italic}` + `<div class="h2-rule">` 黑线

---

## 2 · EXISTING 模式专属规范

### 2.1 §1.2 市场规模
必有项:
- **TAM 表格**(年份 / 规模 USD Mn / YoY / 主导份额变动 / 关键事件)
- 数据来源标注 IDC / Mordor / Grand View 等,估算误差区间标明 ±N%

### 2.2 §2.2 真实需求结构 · 横向条形图
- **N 条 voice 顶帖按主题分布**(红/黑/灰三色:危机/正面/产品体验)
- 每条带原始 upvote 数 + 主题 + 一句场景说明
- chart-caption 必含"对产品团队的启示"一句话

### 2.3 §2.3 JTBD 层级表
4 层固定结构:`L1 医疗/核心场景 / L2 日常状态 / L3 长期趋势 / L4 AI/insight`,每层带:
- voice 强度信号(具体数字)
- 主流玩家兑现度(good / amber / warn / missing)

### 2.4 §2.4 用户原话 · 跨玩家双语 voice 表
- **必须跨玩家覆盖**(不能只有头部玩家),且在表头声明样本分布
- 表头列:`玩家 / 用户原话主题 / 场景 · 来源 / 赞数 / +`
- 圆点 `● 玩家名`(绿色 = 正面,红色 = 负面/危机)
- 折叠行,展开后 4 块:English / 中文 / 关键启示 / 来源 permalink
- 至少 8 行,覆盖 ≥ 3 玩家
- 顶部"样本透明度"灰底注释,声明各 sub 的数据密度

### 2.5 §3.2 Marketplace VOC 表(必有)
- 单一表格,带 `评价 / 主题 / 玩家 / 关键数据 / 来源平台 / +` 6 列表头
- ● 好评(绿圆点)+ ● 差评(红圆点)圆点列
- 至少 5 正面 + 5 负面,跨 3+ 玩家
- 来源:Amazon / Best Buy / Trustpilot / 厂商社区 / 主流测评站(Android Central / Wareable / Tom's Guide 等)
- 数据透明度灰底注释必备

### 2.6 §4.1 定位散点图(SVG)
- 真坐标轴(不是文字象限列表)
- X = 硬件成本(具体美元刻度)
- Y = 医疗化 / 服务深度 / 等价物(分 4-5 档)
- 玩家用圆点 + 标签 + 价格 + 一句定位描述
- **3 类圆**:
  - 实心 = 在售
  - 虚线圆 = 未发布 / 假设
  - 灰色 = 品类外参照(如 Apple Watch 之于戒指)
- **空白机会区**用绿框 + 虚线 + ★ 标注
- **战略箭头**:从主导玩家"当前"位置 → "应该"位置(虚线 + 箭头)
- legend + chart-caption 两段必备

### 2.7 §4.2 切入策略表 + §4.3 MVP 范围
- 3 条 Path 表(路径 / 定位 / 核心动作 / 差异化卖点 / 适合谁)
- 推荐 Path 用 `<strong>` 加粗
- MVP 范围 ≥ 6 条,每条针对一个具体决策(硬件 / 临床 / App / 定价 / 退换 / 不做什么)

---

## 3 · NON-STOCK 模式专属规范

### 3.1 §1.2 → 起源叙事 + 早期信号(替换市场规模)
存量市场用 TAM 表,非存量市场用:
- **品类起源时间线**(谁先做、何时、为什么)
- **早期信号表**(crowdfunding 总额 / waitlist 人数 / 已发货量 / 媒体 demo 量)
- 不要伪造"市场规模 USD X Mn"——非存量没有真数字,有的话也是分析师估算

### 3.2 §2.1 personas → 假设性 personas
- 标记 `<span class="ptag warn">推测 · 待验证</span>`
- 来源:创始人采访 / Demo 评测 / 早期 access 用户 / 跨品类 analog
- 数量 2-3 个(不要 3 个全编)

### 3.3 §2.4 voice 表 → 早期采纳者 voice
- 来源以 r/Limitless / r/HumaneAIPin / r/wearables / HN / Twitter / Product Hunt 评论为主
- 数据密度低,可能每个产品只 1-2 条
- 加更多媒体测评作为补充("review-type" 圆点区别于 user-type)

### 3.4 §3.2 Marketplace VOC → 早期评测聚合
- Amazon 几乎没有评论,改用:
  - 创始人采访 / Demo 视频 transcript
  - 主流科技媒体测评(The Verge / Engadget / Wired / 中文 36kr / 爱范儿)
  - Twitter / Mastodon 上的早期用户晒图 + 反馈
  - YouTube 测评频道 / Marques Brownlee 类
- 表头改为:`评价 / 主题 / 产品 / 关键数据 / 来源类型 / +`
- 来源类型新增 tag:`实测` / `评测` / `创始人话术` / `早期用户`

### 3.5 §3.3 加 失败案例对比(必备)
- 对照表:已停产 / 已失败的同形态产品
- Humane AI Pin / Google Glass / Vine / Quibi 等
- 每条:失败时间 / 原因 / 与本品类的共享前提

### 3.6 §4.1 散点图 → "待验证假设图"
- 实心圆少(只有真在售产品)
- 虚线圆多(crowdfunding / 未发货 / 假设玩家)
- 加一类:`?` 标记 — 用户角色未确认的潜在赢家形态

### 3.7 §4.2 切入策略 → "三种可能的形态"
- 不是"切哪一格",是"三种可能的产品形态,各自的 win condition"
- 每条带:`若成立,该形态成为品类标准的必要条件 + 反面证伪`

### 3.8 §6 风险 → 更多 category-level
- R-01 通常是"品类本身不成立"
- R-02 通常是"早期玩家失败把品类污名化"(Humane 效应)
- R-03 通常是"巨头降维"(Apple / Google / Samsung 入场后,先驱被吃掉)

---

## 4 · 数据采集 · 共用流程

### 4.1 信号扫描(决定走 EXISTING 还是 NON-STOCK)
```
1. r/{品类核心 sub} 顶帖近 1 年的 upvote 中位数
   ≥ 1000 → EXISTING(社区已活跃,有真实使用者)
   100–1000 → 看玩家数,跨 ≥ 3 家有专属 sub 则 EXISTING
   < 100 → NON-STOCK
2. 主流商城前 2 页结果数
   ≥ 5 个产品 + 评论合计 ≥ 200 → EXISTING marketplace 一定要做
   < 5 → NON-STOCK
3. crowdfunding / waitlist / preorder 信号
   有强信号 → NON-STOCK 但加分(说明早期需求真实)
```

### 4.2 Reddit Crawler 调用(`core.collect.reddit`)
```bash
python3 -m core.collect.reddit \
    --subs {sub1} {sub2} {sub3} \
    --limit 25 --sort top --time year \
    --with-comments --comments-per-post 4 \
    --out evidence/{idea-slug}/reddit.jsonl
```
注意:** crawler 部分 sub 会 403**,这是已知限制,需在样本透明度声明。

### 4.3 HN Crawler(`core.collect.hn`)
两轮:stories + comments,query 数 ≥ 5。

### 4.4 Cleaner(`core.collect.clean`)
```bash
python3 -m core.collect.clean \
    --in evidence/{idea}/reddit.jsonl evidence/{idea}/hn_stories.jsonl evidence/{idea}/hn_comments.jsonl \
    --out-dir evidence/{idea}/pack \
    --min-score 3
```

### 4.5 Marketplace VOC 补充(EXISTING 必做,NON-STOCK 可选)
通过 WebSearch 收集:
- Best Buy theme tags(已知:Oura "Sleep Tracking 717")
- Trustpilot 高频主题
- Samsung Community Forum
- 主流测评站对比文章
- 直接抓 Amazon 评论:不可行(反爬),通过聚合源补

### 4.6 跨玩家 voice 补正(关键!)
单一 sub 的数据会偏向头部玩家。**必须在数据收集第二轮做跨玩家补全**:
```bash
# 第二轮:针对挑战者的 sub
python3 -m core.collect.reddit --subs {Player2Sub} {Player3Sub} ...
```
否则报告会沦为"头部玩家用户分析"。

---

## 5 · HTML 设计规范

### 5.1 视觉系统 CSS variables
```css
--bg: #fafaf7;             /* 整页背景,暖白纸感 */
--ink: #14171c;            /* 主文字 */
--muted: #5a606a;          /* 次要文字 */
--paper: #ffffff;          /* 卡片 / 表格背景 */
--bg-warm: #f5f1ea;        /* 数据透明度/方法论灰底 */
--accent: #c2410c;         /* 警示 / 战略箭头(橙) */
--good: #14532d / --good-soft: #ecf3ef;
--amber: #92400e / --amber-soft: #fdf5e9;
--line: #e1e3e7;
--serif: "Source Han Serif SC", "Noto Serif SC", Georgia, serif;
--sans: "PingFang SC", "Hiragino Sans GB", Inter, system-ui;
--mono: "SFMono-Regular", "Roboto Mono", Consolas;
```
颜色总数原则:**正面 / 负面 / 中性 + 一个 accent,不要更多**。

### 5.2 表格规范
- 表头黑底白字 mono 字体 letter-spacing 0.16em
- 列对齐严格(不混用 left/center 在数字之间)
- 圆点(`.sent-dot`)替代背景色 badge
- 折叠行用 `<details>` + `.drow`,展开图标 `+` 旋转 45° 成 `×`

### 5.3 散点图规范
- viewBox 760×520(或等比)
- 网格用 `<pattern>` + 浅灰 0.5px stroke
- 玩家圆点半径 6-11px(头部玩家略大)
- 标签字体 11px PingFang SC,锚点根据位置左 / 右 / center
- 战略箭头 marker-end + dasharray 5 3
- 空白机会区:绿色虚线 + ★

### 5.4 双语 voice 卡片规范
- 折叠状态:1 行,玩家圆点 / 标题(中文为主 + 英文副标)/ 元信息 / upvote / +
- 展开状态:4 块
  - English(serif italic + 红色左边栏)
  - 中文(sans + 绿色左边栏)
  - 关键启示(灰底 + 黑字结论)
  - 来源(mono + permalink)

### 5.5 默认 mobile responsive
- 散点图保持比例
- 表格切回单列
- 折叠卡片网格变 1 列

---

## 6 · 输出检查清单(报告完成前必过)

- [ ] 反共识 thesis 一句话(不是"市场分析",是"为什么主流叙事错了")
- [ ] TL;DR 4 格 + 4 编号 finding
- [ ] §2.2 数据图至少一张(条形 / 散点 / 时间线之一)
- [ ] §2.4 voice 表 ≥ 8 行,跨 ≥ 3 玩家(EXISTING) / 跨 ≥ 4 信号源(NON-STOCK)
- [ ] 每条 voice 都有 permalink,中文翻译逐字不剪裁
- [ ] §3.2 Marketplace VOC(EXISTING)或 早期评测聚合(NON-STOCK)≥ 10 主题
- [ ] §3.3 错配诊断 / 失败案例诊断 ≥ 2 卡
- [ ] §4.1 真坐标散点图,玩家位置可视化,空白机会区标出
- [ ] §4.2 切入策略 3 路径 + 明确推荐
- [ ] §4.3 MVP 范围 ≥ 6 条具体建议
- [ ] §5 能力栈 4 卡(must / critical / standard / optional)
- [ ] §6 风险 ≥ 5 条,每条标严重程度
- [ ] 样本透明度声明出现至少 2 次(顶部 + §3.2 数据来源)
- [ ] Method note 收尾

---

## 7 · 文件结构(每次研究产出)

```
evidence/{idea-slug}/
  reddit.jsonl            # 第一轮 reddit
  reddit_other.jsonl      # 跨玩家补充
  hn_stories.jsonl
  hn_comments.jsonl
  pack/
    cleaned.jsonl
    summary.json
demo-{idea-slug}-report.html    # 最终报告
```

报告 HTML 文件名规范:`demo-{idea-slug}-report.html`,放仓库根目录,可独立分享。

---

## 8 · 交互层规范(MiroFish-启发,2026-05 新增)

报告除了静态内容,**必须叠加 4 个交互组件**,提升信息密度与可探索性。所有交互在单一 HTML 文件内 inline 实现,无 CDN 依赖,保留 self-contained 可分享性。

### 8.1 数据 inline JSON(必备)

报告主体 HTML 末尾(在 `<div class="method">` 之前)嵌入数据块:

```html
<script type="application/json" id="report-data">
{
  "meta": { "idea": "...", "mode": "EXISTING|NON_STOCK", "timestamp": "..." },
  "players": [
    { "id": "oura", "name": "Oura Ring 4", "color": "#c2410c", "size": 18,
      "x": 0.62, "y": 0.30, "summary": "...", "status": "live" }
  ],
  "themes": [
    { "id": "t.medical", "label": "医疗级预警", "color": "#14532d", "size": 14,
      "x": 0.5, "y": 0.5, "polarity": "win|pain|neutral", "summary": "..." }
  ],
  "voices": [
    { "id": "v01", "player": "oura", "title": "...", "score": 2903,
      "url": "...", "sentiment": "pos|neg", "themes": ["t.medical"],
      "x": 0.5, "y": 0.4 }
  ],
  "opportunity": {
    "id": "opp", "label": "★ 空白机会区", "size": 22, "x": 0.42, "y": 0.20, "summary": "..."
  },
  "edges": [
    { "from": "oura", "to": "t.medical", "w": 3 }
  ]
}
</script>
```

约束:
- 所有节点的 `x` / `y` 在 [0, 1] 区间,作为力导向初始位置
- voice 节点的 `themes` 数组必须引用已存在的 theme id
- edge 的 `from` / `to` 都必须是已存在的节点 id
- `w`(weight)1-3 影响 spring rest length(weight 越大越靠近)

### 8.2 顶部 Sticky Process Bar(组件 A)

`<body>` 后第一个元素,5 步骤横向:

```html
<nav class="process-bar">
  <div class="pb-inner">
    <a class="pb-step active" data-target="#sec-meta">
      <span class="pb-num">1</span><span class="pb-lbl">信号扫描 · SETUP</span>
    </a>
    ... 共 5 步
  </div>
</nav>
```

对应章节添加 anchor ID:
- `#sec-meta` → cover + tldr 块
- `#sec-collect` → §1 品类拆解
- `#sec-clean` → §3 竞品分析
- `#sec-analyze` → §4 机会缝隙
- `#sec-verdict` → §6 风险

JS 监听 scroll,根据 `offsetTop` 自动切换 active 状态。每步可点击跳转。

### 8.3 知识图谱面板(组件 B)

在 §1 与 §2 之间插入独立 section:

```html
<section class="chapter kg-section">
  <h2 class="h2"><span class="secnum">★</span>品类关系网络(交互式知识图谱)</h2>
  <div class="kg-wrap">
    <div class="kg-graph">
      <svg class="kg-svg" id="kgSvg" viewBox="0 0 760 520"></svg>
    </div>
    <aside class="kg-side" id="kgSide">...</aside>
  </div>
  <div class="kg-legend">...</div>
</section>
```

视觉规范:
- **玩家节点**:r=11-18,色按品牌(蓝/橙/灰);灰色 = 死/退场玩家(NON-STOCK 特征)
- **主题节点**:r=10-14,绿(正面)/ 橙(负面)/ 灰(中性)
- **voice 节点**:r=6-14,按 `log10(score)` 计算;红(正面)/ 橙(负面)
- **机会区**:虚线绿圆,r=22,无填充
- **边**:灰色,stroke-width 按 weight 0.6-1.8

交互:
- hover 节点 → 高亮该节点 + 邻接节点 + 边;其余 0.18 opacity
- click 节点 → 右侧 `.kg-side` 面板显示详情(玩家/主题/voice/机会的对应模板)
- 详情面板内 `data-jump-node` 链接可跳到关联节点

力导向算法约 90 次迭代:
- 节点间斥力 REPEL=1200/d²
- 边弹簧 SPRING=0.035,rest length = 90/weight
- 中心拉力 CENTER=0.008
- 阻尼 DAMP=0.78

### 8.4 表格 Filter Bar(组件 C)

每张 `.voice-table` 和 `.mkt-table` 前必须有一个 filter-bar:

```html
<div class="filter-bar" data-filter-target=".voice-table">
  <span class="fb-lbl">玩家</span>
  <button class="filter-chip active" data-filter-group="player" data-filter-value="all">全部</button>
  <button class="filter-chip" data-filter-group="player" data-filter-value="Oura">Oura</button>
  ...
  <span class="fb-lbl">情绪</span>
  <button class="filter-chip pos" data-filter-group="sent" data-filter-value="pos">● 正面</button>
  <button class="filter-chip neg" data-filter-group="sent" data-filter-value="neg">● 负面</button>
  <input type="search" class="filter-search" data-filter-search placeholder="搜索...">
  <span class="filter-count" data-filter-count>9 / 9</span>
</div>
```

JS 行为:
- chip 单选(同 group 互斥),所有 group 取交集
- search box 全文匹配(包括展开后的内容)
- 不匹配的 `<details.drow>` 加 `.fb-hidden`(`display:none`)
- 搜索命中的 summary 加高亮背景
- 计数器实时更新

### 8.5 What-If SIMULATED 面板(组件 D)

§4.2 切入策略表后,每条 path 各加一个 `whatif-panel`:

```html
<div class="whatif-panel">
  <div class="whatif-banner">
    <span class="wi-warn">SIMULATED · PATH A 模拟推演</span>
    <span class="wi-note">本块为 LLM 模拟 · 非真用户证据</span>
    <button class="whatif-toggle">收起 ▲</button>
  </div>
  <div class="whatif-body">
    <div class="whatif-grid">
      <div class="whatif-card">
        <div class="wc-scenario">...</div>
        <div class="wc-row"><span class="wc-k">触发</span><span class="wc-v">...</span></div>
        <div class="wc-row"><span class="wc-k">后果</span><span class="wc-v">...</span></div>
        <span class="wc-conf hi">置信 · 中高</span>
      </div>
    </div>
  </div>
</div>
```

视觉硬约束(防止与真证据混淆):
- 红色边框 `1.5px solid var(--accent)`
- 网格底纹 `repeating-linear-gradient(45deg, ...)`
- 横条 banner 显眼 `⚠ SIMULATED` 标签
- 卡片内字体 `var(--mono)` 而非 serif
- 虚线 dashed border

每个 path 3 张卡(成功/中性/失败 scenario),每张含:scenario + 触发 + 后果 + 置信(`lo` / `mid` / `hi`)。

数据来源:LLM 在报告生成时一次性产出,固化进 JSON。运行时不调 LLM。

### 8.6 evidence-rules.md 新约束

新增 §SIMULATED 隔离规则:

- 真 voice / marketplace 数据**绝不**与 simulated 内容混入同一张表
- SIMULATED 卡片必须出现在 `.whatif-panel` 内,带红色横条
- verdict 不可基于 SIMULATED 内容(只能基于 raw_voice 真实计数)
- 报告底部 method note 必须声明"本报告含 X 个 SIMULATED 推演面板,标识为 SIMULATED 字样,不构成决策证据"

### 8.7 文件大小目标

加上 4 个交互组件后的 HTML:
- EXISTING demo:< 200 KB(当前 health-ring 144 KB)
- NON-STOCK demo:< 200 KB(当前 pendant 127 KB)
- 上限 500 KB · 超过则需要外链 JS / 折叠数据

### 8.8 验证清单

报告完成前必过:
- [ ] inline JSON 块存在且通过 `JSON.parse()`
- [ ] 顶部 process bar 5 步骤可点击 + 滚动激活正确步
- [ ] 知识图谱 ≥ 20 节点,hover/click 正确高亮 + 详情面板
- [ ] 每张数据表前有 filter bar,chip + search + 计数正常
- [ ] §4 三条 path 各有 SIMULATED What-If 面板,banner 显眼
- [ ] 复制 HTML 到 `/tmp`,新 tab 打开仍全功能(self-contained)

---

## 9 · Lens-Layout 范式升级(MiroFish 启发,2026-05 重构)

> **本章是范式级升级,不是叠加层**。§8 的 4 个组件全部保留,但它们的容器由"线性长报告"变成 "Always-On 视觉中心 + 可切换 Lens"。旧的线性章节作为 fallback 长页,折叠在 lens 底部。

### 9.1 问题诊断

§8 之前的报告范式是 **"线性长文档 + 4 个增强补丁"**:
- Knowledge Graph 是 §1 与 §2 之间的 section,**滚下去就消失**
- Process Bar 只是 sticky 阅读进度,**不是探索状态**
- Voice 表 / Marketplace 表各自带 Filter,**互相不联动**
- 用户消费方式仍是 cover → §1 → §2 → … → §6 的**线性消费**

参考 MiroFish (`github.com/666ghj/MiroFish`) 的 `MainView.vue`:
- `<main>` 这一级就是 horizontal split,左侧 GraphPanel 永远占据物理空间
- 3-mode view switcher(`graph` | `split` | `workbench`)给用户控制信息密度
- 进度 = `currentStep.value` 状态,右侧 swap step 组件,**graph 不动**
- "视觉中心是布局原语,不是内容元素"

本章把这套范式移植到品类研究报告,但严格保留 self-contained static HTML + vanilla JS 形态。

### 9.2 顶层 DOM 结构(强制)

```html
<body data-mode="EXISTING|NON_STOCK" data-view="split" data-lens="overview">
  <header class="app-header">
    <div class="brand">VIBE · CATEGORY DEEP DIVE · {子赛道}</div>
    <nav class="view-switcher">
      <button data-view="graph">◧ 全景</button>
      <button data-view="split" class="active">◫ 50/50</button>
      <button data-view="lens">◨ 详情</button>
    </nav>
    <div class="verdict-pill" data-status="real|partial|insufficient">{verdict}</div>
  </header>

  <main class="workbench">
    <!-- 左侧:Always-On 视觉中心 -->
    <aside class="center-panel">
      <div class="graph-mount" id="kgSvg"></div>
      <div class="center-overlays">
        <div class="evidence-counter">raw voices: 172  ·  marketplace: 38  ·  editorials: 12</div>
        <div class="legend">...</div>
      </div>
    </aside>

    <!-- 右侧:Lens 容器,根据 data-lens 切换内容 -->
    <section class="lens-panel" data-lens="overview">
      <nav class="lens-tabs">
        <button data-lens="overview" class="active">概览</button>
        <button data-lens="voices">用户声音</button>
        <button data-lens="players">竞品玩家</button>
        <button data-lens="opportunity">机会缝隙</button>
        <button data-lens="strategy">切入策略</button>
        <button data-lens="risks">风险</button>
      </nav>
      <div class="lens-body">
        <!-- 各 lens 内容在这里 swap,详见 9.4 -->
      </div>
    </section>
  </main>

  <!-- 底部:fallback 长报告(默认折叠) -->
  <footer class="report-fallback" hidden>
    <button class="fb-toggle">展开完整报告 ↓</button>
    <article class="fb-body"><!-- 旧的 §1-§6 线性内容 --></article>
  </footer>
</body>
```

### 9.3 View Switcher(组件 E,新增)

3 个模式,通过 `body[data-view]` CSS 控制左右 panel 宽度,**graph 永不 unmount**:

```css
body[data-view="graph"]  .center-panel { width: 100%; }
body[data-view="graph"]  .lens-panel   { width: 0;    opacity: 0; pointer-events: none; }
body[data-view="split"]  .center-panel { width: 50%; }
body[data-view="split"]  .lens-panel   { width: 50%; }
body[data-view="lens"]   .center-panel { width: 0;    opacity: 0; pointer-events: none; }
body[data-view="lens"]   .lens-panel   { width: 100%; }
.center-panel, .lens-panel { transition: width 0.32s ease, opacity 0.2s ease; }
```

切换通过 `document.body.dataset.view = mode`。Graph 内部 selection、缩放、力导向位置全部保留(因为 DOM 不重建)。

### 9.4 Lens 路由(组件 F,新增)

6 个 lens,核心机制:**点击 Graph 节点自动切换到对应 lens**,同时上方 tab 高亮。

| Lens id | 触发方式 | 内容来源(从既有章节迁移) |
|---|---|---|
| `overview` | 默认 / 点击空白 / verdict-pill | TL;DR 速读盒 + 章节标题列表 + 证据计数 |
| `voices` | 点击主题节点 / theme node | §2.2 横向条形 + §2.4 跨玩家 voice 表(filter bar 跟着进来) |
| `players` | 点击玩家节点 / player node | §3.1 玩家卡 + §3.2 Marketplace VOC 表 + §3.3 失败案例 |
| `opportunity` | 点击机会区节点 / opp node | §4.1 定位散点图 + §4.2 空白带描述 |
| `strategy` | 点击 path edge / strategy 节点 | §4.3 切入策略三 path + §8.5 What-If SIMULATED 面板 |
| `risks` | 点击风险标签 / 手动 tab | §6 风险 R-01..R-05 |

JS 行为:

```js
// 点 Graph 节点
function onNodeClick(node) {
  const lensMap = { player: 'players', theme: 'voices', voice: 'voices',
                    opportunity: 'opportunity', strategy: 'strategy' };
  const lens = lensMap[node.kind];
  if (lens) {
    document.body.dataset.lens = lens;
    document.body.dataset.selectedId = node.id;   // lens 内部据此聚焦
    if (document.body.dataset.view === 'graph') {
      document.body.dataset.view = 'split';        // 自动展开
    }
  }
}

// 点 tab
document.querySelectorAll('.lens-tabs button').forEach(b => {
  b.onclick = () => {
    document.body.dataset.lens = b.dataset.lens;
    delete document.body.dataset.selectedId;       // 手动切换 = 不聚焦
  };
});
```

**Lens 容器内部约束**:
- 每个 lens 是一个 `<div class="lens-view" data-lens-id="...">`,默认 `display:none`,通过 `body[data-lens="X"] .lens-view[data-lens-id="X"] { display: block }` 控制
- Lens 内若有 `data-focus-target` 元素,渲染时根据 `body[data-selected-id]` 滚动并高亮对应行
- Lens 切换不刷新 graph,graph 内 selection 与 lens 双向联动

### 9.5 Always-On 视觉中心(组件 G,扩展自 §8.3)

`<aside class="center-panel">` 内除了既有 `kg-svg`,新增 3 个 overlay:

1. **Evidence Counter Strip**(顶部细条)
   - 实时显示 `raw_voices / marketplace / editorials / simulations` 4 个计数
   - 数字带 `data-status` 颜色:绿(达标)/ 橙(临界)/ 红(不足)
   - 鼠标 hover 数字 → graph 上对应类型节点高亮

2. **Verdict Pill**(右上角悬浮)
   - 跟着 `body[data-status]` 变色:`real`(绿)/ `partial`(橙)/ `insufficient`(红)
   - 点击 → 跳 `overview` lens 并滚动到 verdict 块

3. **Legend Mini-Map**(右下角)
   - 节点类型图例 + 一个 minimap 矩形显示当前 viewport
   - 与 §8.3 既有 legend 合并

### 9.6 Liveness 装饰(组件 H,新增,可选)

Evidence-based 报告本身没有"运行中"概念,但可以借用 MiroFish 的 liveness 设计语言传达"数据真实有时序":

- **入场动画**:首次加载时,graph 节点按 collection_plan 顺序 staggered fade-in(模拟"数据正在汇入"),5 秒内完成
- **时间戳浮标**:每个 voice 节点 hover 显示 "collected 2026-05-19 14:32"
- **新鲜度环**:节点边缘有渐变环,亮度随 voice 发布时间衰减(近 30 天最亮,>1 年灰)
- **collection log strip**(底部细条,可选):一行滚动文本显示数据采集时间线(`14:21 r/RayBanMeta · +47 voices  ·  14:33 HN search · +28 voices  ·  ...`)

实现优先级:入场动画 > 新鲜度环 > collection log。前两个加起来约 40 LOC。

### 9.7 Fallback 长报告

页面底部固定一个折叠区:

```html
<footer class="report-fallback">
  <button class="fb-toggle" aria-expanded="false">展开完整报告 ↓</button>
  <article class="fb-body"><!-- §1-§6 线性结构 --></article>
</footer>
```

- 默认折叠,点击展开
- 展开后是当前 spec §1-§7 的完整线性内容(给打印 / 分享 / 全文搜索 / Ctrl+F 用)
- **Lens 范式服务"探索",fallback 服务"阅读"**,两者不互斥
- 打印样式 `@media print` 强制 `.fb-body` 展开,隐藏 `.workbench`

### 9.8 状态模型(单一事实源)

页面状态完全编码在 `<body>` 的 data 属性,无外部 store:

| 属性 | 值 | 含义 |
|---|---|---|
| `data-mode` | `EXISTING` / `NON_STOCK` | 数据模式(§2/§3 走哪套规范) |
| `data-view` | `graph` / `split` / `lens` | 左右 panel 宽度 |
| `data-lens` | `overview` / `voices` / `players` / `opportunity` / `strategy` / `risks` | 当前 lens |
| `data-selected-id` | node id / undefined | graph 当前选中节点 |
| `data-status` | `real` / `partial` / `insufficient` | verdict |
| `data-style` | `minimal` / `editorial` / `data-dense` | 视觉 token preset(沿用 §P2) |

所有交互最终落点都是修改 `body.dataset.X`,CSS + lens-router JS 据此重渲。可读性、可调试性、可 deeplink 都强。

### 9.9 与 §8 关系

| §8 组件 | 在新范式下的命运 |
|---|---|
| §8.2 Process Bar | **降级**:不再是 sticky nav,迁移为 fallback 长报告内部的章节锚点 |
| §8.3 知识图谱 | **升级为 substrate**:从 section 提到 `<aside class="center-panel">`,Always-On |
| §8.4 Filter Bar | **保留**:嵌入到 `voices` / `players` lens 内部,与 graph selection 双向联动 |
| §8.5 What-If SIMULATED | **保留**:迁移到 `strategy` lens 内,SIMULATED 视觉硬约束不变 |
| §8.6 evidence-rules.md 约束 | **不变** |
| §8.7 文件大小 | **放宽**:上限 600 KB(新增 view-switcher + lens-router + liveness ≈ 80 KB) |

### 9.10 实现优先级(增量)

1. **P0 · 布局壳**(~ 60 min)
   - 顶层 DOM 改造(header + workbench + footer)
   - View Switcher CSS 3 模式
   - body data 属性状态机骨架

2. **P0 · 2 个 lens 切片**(~ 90 min)
   - `players` lens(基于现有 §3 内容)
   - `voices` lens(基于现有 §2.4)
   - 验证 graph 节点点击路由

3. **P1 · 剩余 4 个 lens**(~ 60 min)
   - overview / opportunity / strategy / risks

4. **P1 · Always-On overlays**(~ 40 min)
   - evidence counter strip / verdict pill / mini legend

5. **P2 · Liveness 装饰**(~ 30 min)
   - 入场动画 + 新鲜度环

6. **P2 · Fallback 长报告**(~ 30 min)
   - 折叠容器 + 章节复用 + print 样式

7. **验证**(~ 20 min)
   - 6 个 lens 切换正常
   - graph selection ↔ lens 内 row 联动
   - 复制到 `/tmp` 仍 self-contained
   - 文件大小 < 600 KB

总计 ~ 5.5 小时。

### 9.11 验证清单(在 §8.8 基础上追加)

- [ ] 三种 view mode 切换流畅,graph 状态(selection / 缩放)保留
- [ ] 点 graph 玩家节点 → `players` lens + 该玩家高亮聚焦
- [ ] 点 graph 主题节点 → `voices` lens + voice 表自动滚到该主题相关行
- [ ] Verdict Pill 颜色与底部完整报告 verdict 一致
- [ ] Evidence Counter 数字与 inline JSON 计数一致
- [ ] Fallback 长报告默认折叠,展开后包含完整 §1-§6
- [ ] `@media print` 下 fallback 自动展开,workbench 隐藏
- [ ] 复制 HTML 到 `/tmp`,新 tab 打开,6 个 lens 全功能 + graph 全交互
- [ ] body data 属性手动改(DevTools)能正确反映在 UI 上(deeplink-ready)
