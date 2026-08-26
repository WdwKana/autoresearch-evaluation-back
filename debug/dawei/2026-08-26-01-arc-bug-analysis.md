# 2026-08-26 框架 01 (AI-Researcher) × arc_wbe_2026 "跑不出分数" bug 链分析

## 结论先行

01 在 ARC 上**能完成研究但永远无法合规交付**,失败 100% 确定性、与运行环境无关。根因不在上游框架,而在评测线束的 01 适配层：**交接门在拓扑上不可满足** + **交付规格从未送达 agent 视野**。两次独立干净 run 精确复现（run `fullrun_arc_01_20260825_102702`、`fullrun_arc_01_20260826_044013`,均保留）。

## 运行时拓扑

```
宿主 wrapper (01_ai_researcher_arc_wbe_2026_fullrun.sh)
 └── 外层容器 ai-researcher:runtime-ready
      挂载: $RUN/workspace → /workspace           ← 42号门/打分器/校验器在这里找产物
      运行: run_infer_idea.py（agent 循环）
       └── 内层容器（agent 的代码执行沙箱）
            挂载: workspace/AI-Researcher/research_agent/workplace_paper/
                  task_*/workplace/workplace → /workplace   ← agent 唯一可写世界
            挂载: 数据集 → /data/arc_wbe_2026:ro、契约 → /input/contract.md:ro
```

## Bug 链（按因果顺序）

### B1（致命）交接门物理上不可满足
- wrapper 42 号门检查 `$WORKSPACE` 根的 5 个产物文件;agent 可写世界映射到深层 workplace 目录,与 `$WORKSPACE` 根无交集。
- 三处均无桥接代码：wrapper 无 copy;`run_infer_idea.py`（609 行）无 copy;适配补丁（114 行）无 copy。
- **任何 agent 行为都过不了这道门** → 解释确定性失败与环境无关性。

### B2 交付规格投递链断裂（01 独有的输入配给缺口）
- 生成器 `generate_arc_wbe_2026_native_inputs.py` 为 03/05/07 写 `ARC_WBE_2026_BRIEF.md`（逐字含 9 个 trace 字段 + `predict(mlp)→(32,256)` 接口）;02 由其 wrapper 注入 ideation system prompt;**01 两者皆无**。
- 01 的 metaprompt 走"短句 + REF 指向完整契约"的设计,但 REF 插值的是宿主绝对路径,内层容器不存在（内层也没有 automation/、docs/ 目录）→ **该链路自原作者时代起即断**,与 leaderboard 至今为空自洽。
- 后果实测：trace 用框架私有 schema（契约字段 0/9）、estimator 接口不符（官方 adapter fail-closed 拒分）。

### B3（工程）失败不写终态
- 42 号门与打分后校验为 `set -e` 下的裸 python heredoc,失败即杀 wrapper,`state.json` 永远停 "running" → 外部视角"神秘消失、无分数",极大干扰排障。

### 已撤回的候选
- "metaprompt 应写绝对路径"：经讨论撤回——通用框架不应被要求靠 prompt 里的绝对路径工作;且在 B1 存在时该项无论真假都不影响结局。

## 关键证据（可复现命令）

Step 0 门检重放（零成本,门检代码从 wrapper 原样抽出）：

| 测试 | 输入 | 结果 |
|---|---|---|
| A | 留存 run 的 workspace 根 | ❌ 与 run 日志逐字相同的 missing 报错 |
| A2 | 同 run 中 agent 实际交付的 `project/` 深层目录 | 文件存在性**全过**,死于 trace 字段校验 → 位置问题与规格问题干净分离 |
| B | 合规最小假产物置于沙盒根 | ✅ `rc=0` → 门本身逻辑健全 |

## 设计背景（为什么会这样）

生成器遵循"按各框架原生输入格式投喂"原则（03/05/07 读文件 → BRIEF;02 吃 prompt 注入;01 吃 HKUDS benchmark 短句格式 + REF 链接）。01 的适配**做了一半**：短句有了,链接没接通,规格全文无通道送达。属于遗留未完成项,非有意差别对待。
