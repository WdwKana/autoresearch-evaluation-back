# PsyDefDetect 契约措辞修订草案（针对树搜索类框架，如 AI-Scientist-v2）

草案，供团队讨论；未生效。目的：让契约与校验器的措辞与框架自己的编排流一致，不改变 host 与框架的责任边界。

## 1. "实验"的定义

现行："Run exactly 2 to 4 materially different experiments … Never start a fifth experiment."

修订："For tree-search frameworks, an *experiment* is the solution the framework itself promotes at the end of each of its stages (AI-Scientist-v2: `best_solution_<node>.py`, 1 per stage, so 2–4 per run). The framework's exploration nodes are not counted as experiments. `experiment_trace.json` lists these 2–4 promoted solutions."

理由：树搜索天然探索几十个节点；契约关心的是被框架选出并比较的方案，而每阶段的 best_solution 正是框架自己的选择。

## 2. "选择"的定义

现行：framework-level final selection.

修订："The selected experiment is the framework's promoted solution of its final stage."（框架最后一个阶段的 best_solution。）

## 3. "提升产物"的责任

现行："Before exit, the framework must promote the selected final artifacts to /workspace/…"

修订："The framework's promoted solutions are the handoff. The host may (a) replay a promoted solution in a clean offline environment to regenerate its predictions and official score, (b) relocate those files to the workspace root, (c) re-run the official scorer, and (d) write `experiment_trace.json` from recorded facts only. The host must not modify, repair, select among, or generate framework-authored content."

理由：这是标准中 host 拥有的"打包、官方打分、输出校验"，不是"创建或修复框架结果"；选择仍由框架做。

## 4. 官方评估的产物位置（输出 schema）

新增："Official evaluation of a configuration is done through the provided reference function, which writes `working/<name>.predictions.jsonl` and `working/<name>.official_score.json` and prints `official psydefdetect_score (<name>): <value>`."

## 5. 预算

现行：7200 s 墙钟。

修订："Budget is a run-level wall clock per topic; stage iteration limits are part of the framework adapter and recorded in the run."（psydef 建议 4 小时，或按阶段上限 12/4/4/2 压回 2 小时；由团队定。）

## 6. `final_report.md`

修订："`final_report.md` may be rendered by the host from the framework's recorded plans, verdicts, scores and the framework's own stage summaries; the host adds no scientific content."
