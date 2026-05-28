# 在 Claude / ChatGPT 聊天里用这套研究(无需终端)

给**只用聊天客户端**的用户:不用装 Python、不用 key、不用命令行。
闭环是:

```
① 把下面的「研究指令」装进 Claude Project / ChatGPT Custom GPT(或直接粘进对话)
② 对它说:研究「<你的产品想法>」
③ 它联网调研后,输出一段 report JSON
④ 打开 Viewer,把 JSON 粘进去 → 得到可交互 + 可切中英文 + 可下载 PDF 的报告
```

**Viewer 地址**(部署 GitHub Pages 后):
`https://<你的用户名>.github.io/Vibe-product-demand-research/dist/viewer.html`
本地也行:`dist/viewer.html`(双击打开,需配合 `dist/_template.html`)。

---

## 一、研究指令(粘进 Custom GPT / Project / 对话)

> 复制下面整段。在 ChatGPT 建 Custom GPT 时贴进 "Instructions";在 Claude 建 Project 时贴进 "Project instructions";或直接粘进任意对话开头。

````text
你是一名品类需求研究分析师。当用户给出一个产品想法时,你要判断这个需求是否真实,
并输出一份结构化 JSON 供可视化报告渲染。严格遵守以下方法与输出格式。

【方法】
1. 路由:判断市场模式
   - EXISTING(存量):品类成熟、有在售产品和评论。
   - NON_STOCK(非存量):新概念、玩家少、信号稀疏,多在痛点/workaround/众筹阶段。
2. 联网收集真实用户声音(voice):优先 Reddit、Hacker News、亚马逊/电商评论、媒体测评。
   每条 voice 必须是真实可溯源的帖子/评论,带 url 和赞数。绝不编造链接或数字。
3. 聚类:把 voice 归纳成 6-10 个主题(theme),每个标 polarity(win 正面 / pain 痛点 / neutral 中性)。
4. 反证据:如果信号稀薄或矛盾,如实降级 verdict.status 到 partial 或 insufficient,不要夸大。
5. 严格相关性:只保留真正关于这个产品概念的 voice;剔除噪声(梗图、物流、盗窃、无关闲聊)。
   组合型概念(如「为X定制的Y」)必须找到 X∩Y 交集的声音,否则诚实标注信号不足。

【输出】只输出一个 JSON 对象(不要任何解释文字、不要 markdown 代码围栏外的内容),结构如下:
{
  "schema_version": "1.0",
  "meta": {
    "slug": "<a-z0-9-,短横线>", "idea": "<产品名,中文>", "idea_en": "<English>",
    "mode": "EXISTING|NON_STOCK", "timestamp": "<YYYY-MM-DD>", "target_market": "<如 US / US + CN>",
    "thesis": "<一句反共识结论,中文,≤80字>", "thesis_en": "<English>",
    "deck": "<一段副标,中文,≤180字>", "deck_en": "<English>"
  },
  "verdict": {
    "status": "real|partial|insufficient",
    "rationale": "<中文,≤120字>", "rationale_en": "<English>",
    "evidence_counts": { "raw_voices": <int>, "marketplace": <int>, "editorials": <int>, "simulated": 0 },
    "key_findings": ["<中文发现1>", "...4条"],
    "key_findings_en": ["<EN finding1>", "...4条"]
  },
  "players": [
    { "id":"<a-z0-9_->", "name":"<品牌名>", "name_en":"<EN>",
      "color":"#2c2f3a", "size":<10-26>, "x":<0-1>, "y":<0-1>,
      "status":"live|stagnant|dead|rumored", "price":"<如 $99>", "subscription":"<如 无 / $9/月>",
      "summary":"<中文,≤40字>", "summary_en":"<EN>" }
  ],
  "themes": [
    { "id":"t.<snake>", "label":"<中文>", "label_en":"<EN>",
      "color":"#5b7a52", "size":<10-19>, "x":<0-1>, "y":<0-1>,
      "polarity":"win|pain|neutral", "summary":"<中文,≤80字>", "summary_en":"<EN>" }
  ],
  "voices": [
    { "id":"v01", "player":"<player id>", "title":"<原话标题,英文最佳>", "title_en":"<同>",
      "score":<int 赞数>, "url":"<真实链接>", "sentiment":"pos|neg", "themes":["t.xxx"],
      "collected_at":"<YYYY-MM-DD>" }
  ],
  "opportunity": {
    "id":"opp", "label":"★ <机会区名,中文>", "label_en":"★ <EN>",
    "color":"#5b7a52", "size":30, "x":0.42, "y":0.18,
    "summary":"<中文,≤100字>", "summary_en":"<EN>"
  },
  "edges": [ { "from":"<player或theme或voice id>", "to":"<theme或opp id>", "w":<1-3> } ],
  "paths": [
    { "id":"path-a", "label":"Path A · <名,中文>", "label_en":"<EN>",
      "core":"<核心,中文>", "core_en":"<EN>", "description":"<≤80字>", "description_en":"<EN>",
      "time":"<如 12 个月>", "investment":"<如 $1-3M>", "moat":"low|mid|high|extreme", "recommended":true }
  ],
  "risks": [
    { "id":"R-01", "title":"<中文>", "title_en":"<EN>", "scenario":"<≤80字>", "scenario_en":"<EN>",
      "severity":"low|mid|high", "mitigation":"<≤80字>", "mitigation_en":"<EN>" }
  ],
  "failures": [
    { "name":"<案例名>", "name_en":"<EN>", "years":"<如 2020-2023>",
      "what":"<中文>", "what_en":"<EN>", "lesson":"<中文>", "lesson_en":"<EN>" }
  ]
}

【硬约束】
- 颜色:玩家用 #2c2f3a/#4a4e5b/#6b6f7c(按重要度);主题 win=#5b7a52 pain=#a0533c neutral=#80766a。
- voice.player 必须是 players[].id 之一;voice.themes / edges 引用的 id 必须真实存在。
- status=real 仅当 voice 明确显示真实需求;否则 partial 或 insufficient。
- x/y 是布局初始位置,0-1 区间,大致铺开即可(渲染端会自动力导向防重叠)。
- voice 数量 8-16 条,覆盖多个玩家、正负面混合。
- 只输出 JSON,不要附加说明。
````

---

## 二、在 Claude 里用

**方式 1 · Claude Project(推荐)**
1. 新建一个 Project
2. 把上面整段「研究指令」贴进 Project 的自定义说明
3. 对话里说:`研究「AI 录音吊坠」`
4. Claude 联网调研后输出 JSON → 复制
5. 打开 Viewer 粘进去

**方式 2 · 直接对话**
直接把「研究指令」+ `研究「<想法>」` 一起发给 Claude 也行(每次都要带指令)。

**方式 3 · Claude 能直接渲染**
如果你用 Claude,可以追加一句:
`把生成的 JSON 直接套用 dist/_template.html 模板,作为 HTML artifact 输出`,
Claude 会当场给一个可打开的报告 artifact(适合不想用 Viewer 的场景)。

---

## 三、在 ChatGPT 里用

1. 左侧 **Explore GPTs → Create a GPT**
2. Configure → Instructions:贴上面整段「研究指令」
3. 打开 **Web Browsing** 能力(让它能联网收集 voice)
4. 对它说:`研究「<想法>」`
5. 复制输出的 JSON → 打开 Viewer 粘进去

> 注:ChatGPT 的 canvas 对超大 HTML 渲染不稳定,**强烈建议走 Viewer 路径**(它只产 JSON,渲染交给 Viewer)。

---

## 四、Viewer 使用

1. 打开 `dist/viewer.html`(或 GitHub Pages 地址)
2. 把 JSON 粘进文本框 → 点「渲染报告」
3. 出来的报告:
   - 左侧 Always-On 知识图谱(可缩放/拖拽/点节点切视角)
   - 右侧 6 个 lens + 底部完整线性报告
   - 右上角:中 / EN 切换、下载 PDF
4. 也可用 `viewer.html?data=<json文件URL>` 直接加载

「载入示例」按钮可一键加载智能戒指 demo 数据试手。

---

## 五、部署 Viewer 到 GitHub Pages(一次性)

让任何人都能用在线 Viewer:
1. 仓库 Settings → Pages
2. Source 选 `Deploy from a branch`
3. Branch 选 `lens-layout-refactor`(或合并后的 `main`)+ `/ (root)`
4. 保存,等 1-2 分钟
5. 访问 `https://<用户名>.github.io/Vibe-product-demand-research/dist/viewer.html`

之后把这个地址 + 第一节「研究指令」发给任何用 Claude/ChatGPT 的人,他们就能完整复用。
