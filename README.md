# 真需求/伪需求研判 App

一个本地单页 Web 应用,判断一个产品想法是真需求还是伪需求。

输入一个产品想法 + 目标市场,工具自动:
1. 决定走存量市场路径(VOC)还是非存量市场路径(三视图并排),或两者混合;
2. 从 Reddit + Hacker News 抓真实用户原话(绕开 WebFetch 反爬封锁);
3. 把原始 voice 归类成 痛点 / 正面 / workaround / 反向证据 / 付费信号;
4. (可选)调用 Claude 把原始 voice 总结成可读报告——每条 verdict 必须能引到 permalink 上的原文;
5. 最终 verdict 绑死在证据规则上:`voices_raw == 0` 强制 `insufficient`,marketplace VOC 缺失时 hybrid 不能给"真需求"。

## 快速开始

```bash
# 基础模式:只跑 crawler,出原始 voice
./run.sh

# 完整模式:启用 Claude 综合判断
pip install anthropic
ANTHROPIC_API_KEY=sk-ant-... ./run.sh
```

浏览器打开 http://127.0.0.1:8123/。

依赖:Python 3.9+。基础模式不需要任何 pip 包(stdlib only)。

## 它在做什么

```
Input(产品想法 + 目标市场)
       │
       ▼
1. detect_mode  ← Claude(可选)推荐合理的 subreddit / HN query
       │
       ▼
2. Collect       crawler:Reddit /r/<sub>/.json · HN Algolia API
       │
       ▼
3. Clean         dedupe + 关键词分桶
       │
       ▼
4. Analyze
   ├─ existing 模式:VOC 总结 → 痛点/正面/反向 三列原话
   └─ non_stock 模式:三视图并排
        ├─ 客观:5 维度结构化评分(JTBD / 痛点 / analog / workaround / 失败条件)
        ├─ 客观:历史失败案例 + 是否复用同样前提
        └─ 主观:AI 定性评论(明确标注,不作为独立证据)
       │
       ▼
5. Verdict       evidence-rules.md 硬 gating → 真需求 / 伪需求 / 证据不足
```

## 评判尺度

`references/evidence-rules.md` 是单一来源,关键规则:

- **Editorial 不计入 voices**:journalist / analyst / blogger / 二手报道写的内容算 `editorial_signals`,不算 `voices_raw`。
- **`voices_raw == 0` 强制 `insufficient`**:不允许"基于媒体报道"得出需求结论。
- **存量/混合路由需要 marketplace VOC**:没拿到 Amazon/京东评论时,verdict 不能超过 `partially_supported`。
- **Counter-evidence 必填**:不允许只列支持需求的证据,反向证据必须显式找过并交代结果。

## 文件结构

```
app.py                  HTTP server(stdlib http.server)
core/
  pipeline.py           编排:detect → collect → clean → analyze → verdict
  detect_mode.py        模式判定(LLM 推荐查询 + 信号扫描)
  collect/              crawler:reddit.py · hn.py · clean.py
  voc_summarize.py      存量模式 VOC 总结
  non_stock.py          非存量模式三列分析
  verdict.py            合成最终 verdict,应用 gating
  llm.py                Anthropic 封装 + 磁盘缓存
web/
  index.html            单页 UI
  style.css             视觉系统(CSS tokens)
  app.js                SSE 进度流 + 结果渲染
references/
  evidence-rules.md     证据规则唯一来源
legacy/                 旧 skill spec 形态,留作参考
run.sh                  一键启动
```

## 限制

- **Marketplace VOC 还没实现**:Amazon / Best Buy / 京东 评论页有反爬,这一层暂缺。结果:hybrid 路由目前只能到 `partially_supported`,不能给"真需求"——这是设计上的诚实降级。下一步会加 CSV 手动导入 + headless 抓取。
- **Reddit 部分 sub 403**:某些 subreddit 对匿名 .json 端点关闭。Collector 跳过并在 UI 上标 failed。
- **CN 平台尚未接**:小红书 / B站 / 知乎国内反爬难度大,V2 处理。
- **单机单用户**:job 在内存里,重启服务即清空,无历史持久化(本轮)。

## 输入提示

最好用**主流产品类别名 + 形态描述**,不要太具体的品牌名(crawler 抓不到品牌私域),例如:

- ✅ "AI smart glasses with always-on multimodal assistant"
- ✅ "personal AI music coach for adult learners"
- ❌ "MyCoolProduct™ V2 features list" — crawler 找不到

中文输入工具也支持,但 LLM 未启用时 fallback 抓不到 Reddit(默认 sub 是英文社区)。强烈建议在 CN 市场调研时配 `ANTHROPIC_API_KEY`,LLM 会推荐对应的中英文混合社区。
