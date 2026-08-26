# 2026-08-26 框架 02 (AI-Scientist-v2) × arc_wbe_2026 预防性诊断

方法与 01 相同（拓扑 → 规格投递 → 交接门 → 打分 → 终态）,全部静态取证,零 LLM 成本。目的：在 S2 key 到位前把后续会连环撞上的问题提前定位。

## 运行时拓扑（与 01 的关键差异）

```
宿主 wrapper (02_..._fullrun.sh → exec arc_framework_fullrun.sh)
 └── 单一容器 ai-scientist-v2:runtime-ready,workdir /workspace
      AI-Scientist-v2 源码 rsync 进 /workspace;实验代码在同一容器内解释执行
      流程: 重建适配器 → inline 补丁(llm.py/token_tracker) → 契约注入 ideation 系统提示
            → perform_ideation (30min 上限, S2 检索工具)
            → idea JSON 校验 (AI_SCIENTIST_V2_ARC_IDEA_OK)
            → bfts_config 改写 (steps=2, workers=1) → launch_scientist_bfts (60min 上限) → 结束
```

## 对照 01 的 bug 类别逐项核验

| 01 的 bug | 02 是否存在 | 证据 |
|---|---|---|
| B1 拓扑断裂（agent 写不到被检查的位置） | **不存在** | 02 无内层容器,实验代码与 /workspace 同容器,可直接写根目录 |
| B3 失败不写终态 | **不存在** | `arc_framework_fullrun.sh:494` 对任意非零 run_rc 统一 `write_state failed`（062148 的 exit 124 已实证） |
| B2 规格投递缺口 | **部分存在,形态不同（见下）** | — |

## 02 特有的两个风险点

### R1（结构性）：`research_idea.json` 无人机械落盘,BFTS 阶段看不到交付契约
- 注入的契约原文写"the native idea **will be locked** as /workspace/research_idea.json"——**被动语态,但 RUNTIME_COMMAND 里没有任何 lock 写入代码**（全文 grep 证实：ideation 后只做 idea JSON 校验,BFTS 后直接结束,无任何根产物生成/搬运逻辑）。
- `launch_scientist_bfts.py` 只加载 idea JSON;交付契约（5 个根产物路径 + 9 个 trace 字段）**仅存在于 ideation 的系统提示**,能否传到 BFTS 编码 agent,完全取决于 ideation 模型是否恰好把它抄进 idea 字段——概率性投递。
- **预测**：S2 key 到位、ideation 跑通之后,02 大概率死在与 01 相同的 42 号门（缺根产物,尤其 research_idea.json）,机制不同但症状相同。
- 候选修复（02 作用域,待讨论后实施）：
  a) ideation 校验通过后,由 wrapper 在容器内把框架自产的 idea JSON 机械转写/锁定为 `/workspace/research_idea.json`（内容全部来自框架产出,留 provenance;设计裁量点同 01 的搬运桥）；
  b) 让 BFTS 阶段也能看到同一份契约文本（沿用 02 wrapper 已有的 inline 补丁风格,把契约并入 BFTS 任务描述;属"host 定义输出 schema",AGENTS.md 允许）。

### R2（阻塞性,已知）：S2 无界退避挂死
- `semantic_scholar.py` 的 `backoff.expo` 无 max_tries/max_time;无 key 时一次 429 风暴即挂死 ideation（949 秒/次退避实测,run 062148）。
- 检索是 LLM 自主决定的 ACTION（SearchSemanticScholar / FinalizeIdea 二选一）,研究型 ideation 几乎必然选择检索,不能指望模型不搜。
- 候选修复：02 wrapper 的 inline 补丁给该工具加**有界重试**（如 max_tries=3,失败返回 "No papers found"）——把无限挂死降级为无文献继续。**附带效果：不等 S2 key 也能立即解除 02 的阻塞**（文献质量降级,拿到 key 后自动恢复完整功能）。防御性质,与 key 不冲突。

## 可复用的既有资产
- 42 号门重放脚本（gate42.py,Step 0 产物）对 02 同样适用（通用 wrapper 的门与 01 检查同一组文件与字段）。
- 修复若实施,作用域仅 `02_ai_scientist_v2_arc_wbe_2026_fullrun.sh`（RUNTIME_COMMAND 内,inline 补丁风格与现有代码一致）,不触碰共享的 `arc_framework_fullrun.sh`。

## 结论
02 比 01 健康：拓扑通、终态处理健全。剩两件事：R2 一个有界退避补丁即可解阻塞（可立即做）;R1 是"S2 修好后的下一个雷",建议趁现在按 a+b 修掉,再用一次 fullrun 集成验证。
