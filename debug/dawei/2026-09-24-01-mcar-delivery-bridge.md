# 01 × MountainCar：交付桥混装（2026-09-24）

## 现象
`fullrun_mcar_01_luna_20260903_153128`（及 09-03 其余 luna 发）exit 42：根目录 checkpoints + src 送冻结评分器时
`ScopeParamNotFoundError: critic_fc_1`。此前记为"接口交付不全 / luna 自造代码结构"。

## 根因（离线回放证实，不耗 API）
agent 留下两套自洽产物：
- `workplace/checkpoints` + `workplace/src`（16:54）
- `workplace/project/checkpoints` + `workplace/project/src`（17:32，研究变体，networks.py 不同）

01 包装脚本的搬运块把两处 `config-42-*.pkl` 全部 glob 到根目录（10 个，后 5 覆盖前 5），
但从不搬对应的 `src/`，根目录仍是 host 铺的模板起始代码 → 权重与网络结构不配。

| 配对 | 冻结评分器 |
|---|---|
| 实际交付（project 权重 + 模板 src） | 崩 |
| workplace 套 | Reward Mean −8.52 |
| project 套（project/src 覆盖 workplace/src） | Reward Mean −3.71 |

## 修复（仅 01 包装脚本 `real_eval/scripts/01_ai_researcher_mountaincar_continuous_fullrun.sh`）
搬运块改为：按目录分组 checkpoint 集 → 选最新的完整集（5 个）→ 只搬这一集 →
沿 workplace 根到该集所在目录的路径，把每级 `src/` 原样覆盖到 `/workspace/src`（外层先、内层赢）。
`handoff_relocation.json` 记录 `checkpoint_set` 与 `src_overlay`。`MCAR_HANDOFF_WORKSPACE` 仅供离线回放。
共享脚本 `mountaincar_framework_fullrun.sh` 第 248 行的找回逻辑只在数量≠5 时触发，未动。

## 回放测试（沙盒 `real_eval/runs/control_mcar01_replay_20260924/`，运行时镜像内跑冻结评分器）
| 用例 | 旧逻辑 | 新逻辑 |
|---|---|---|
| 两套完整集 | 混装，崩 | 选 project 套，−3.71 |
| 仅 workplace 一套 | — | −8.52 |
| 最新集缺一个文件 | — | 回退到完整的 workplace 套，−8.52 |
| 根目录已有 5 个 | 不动 | 不动 |

## 待做
一发 luna 集成测试；通过后补 DS / kimi（01 MountainCar 从未跑过这两个模型）。

## 集成测试第 1 发（`fullrun_mcar_01_luna_20260924_115332`，保留）：两处与交付桥无关的拦路
1. **中转站变更**：gpt-5.6-luna 现在拒绝一切带 function tools 的 /chat/completions 请求，除非显式 `reasoning_effort='none'`
   （直接探测 5/5 拒、加 none 后 5/5 通；09-03 的 141 次请求全通，即 09-03 之后变的）。AI-Researcher 从不发 reasoning_effort，
   Paper Survey Agent 在 ideation 第 9 次请求死掉。修复：`real_eval/adapters/ai_researcher/patch_reasoning_effort_fallback.py`
   （只在收到该 400 时同请求重试一次，接入 01 MountainCar 包装脚本；其余 01 包装脚本尚未接入，luna 都会撞）。与 02 的 4457b1d 同思路。
2. **共享脚本无声退出**：`mountaincar_framework_fullrun.sh` 第 237 行 `ckpt_count=$(ls .../*.pkl | wc -l)` 在没有任何 checkpoint 时，
   `set -euo pipefail` 让脚本以 2 退出、无输出、state.json 停在 running（回放整段 if 块：旧版 exit 2，新版走到底）。
   这是 08-19 同步进来的代码，影响所有框架的 MountainCar 运行。修复 a8eaa3c：两处 `|| true`。
第 2 发 `fullrun_mcar_01_luna_20260924_121831` 带两处修复重发，fallback 在 ideation 第一次被拒时即触发并继续。

## 集成测试第 2 发(`fullrun_mcar_01_luna_20260924_121831`):交付桥工作,门槛因"只有 1 个实验"以 42 拒绝
- ideation 通过(fallback 触发 1 次),Machine Learning Agent 67 轮,框架自己写出 5 个 checkpoint + src + 三份根文件(Quantile-Distributional PPO)。
- 搬运:`relocated 5 checkpoint(s)`、`overlaid 6 src file(s)`;host 离线用冻结评分器复算 **Reward Mean −9.44**——交付桥修复达到目的。
- 门槛(`mountaincar_framework_fullrun.sh` 的 handoff gate)拒绝:`experiment_trace.json must record 2-4 experiments`,trace 里只有 1 个实验(`qdppo-n16-2updates`)。这是契约要求,不是桥的问题:research_completed=false,不入榜;−9.44 仅作参考。
- 门槛的拒绝原因只走 stderr 未进 e2e.log(09-03 那发同样),排障要靠离线回放 `gate_mcar.py`;是否让 runner 把原因写进 state.summary,待议。
