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
