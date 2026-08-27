# 协作者对齐清单（持续更新,最后更新 2026-08-26）

## 需要向协作者索取

1. **`real_eval/adapters/ai_scientist_v2/patch_ai_scientist_v2_common.py` 原件**——公开发布遗漏;我方已按 wrapper 上下文重建最小版（见 02 阻塞记录）,需 diff 校对。
2. **Semantic Scholar API key**——02 的 ideation 硬依赖;无 key 必然 429 超时。
3. **`real_eval/codex_relay/relay.py` 正本**——公开仓引用但未发布;我方已从常驻 relay 容器回收一份（1046 行,已加 provenance 头）,需 diff 校对。
4. **Codex CLI 版本号**——TDC/PsyDef 的 smoke 依赖宿主 codex;新版 0.150.1 已移除 relay 依赖的 `wire_api="chat"`,需知道你们钉的版本。
5. （可选）`api/_semantic_scholar_api_usage.md`、其他 `api/` 私有配置的清单,确认还有哪些脱敏遗漏。

## 需要同步给协作者的发现

1. **01×ARC 从未出分的根因是线束 bug,不是模型/框架能力**：42 号门拓扑上不可满足 + 交付规格从未送达 agent（详见 `2026-08-26-01-arc-bug-analysis.md`）。修复在分支 `fix/01-arc-delivery`,全部 01 作用域,请 review——尤其"搬运桥是否符合 host-must-not-promote 条款"这一设计裁量点。
2. **01 wrapper 失败不写终态的 bug**：校验失败时 state.json 停 "running",外部看是"神秘消失"。若你们也见过此现象,即是同源。
3. **`REAL_EVAL_MODEL` 默认值**：不设则 01 调 gpt-5.4、02 调 kimi-k2.6;key 无权限即 403 循环至超时。
4. **whest 版本对齐**：仓库未钉版本;我方 whestbench 0.16.0,commit `35164f3535c2103742772dd11a68ce840464db0b`。
5. **镜像依赖**：早期构建的 `ai-researcher:runtime-ready` 缺 libGL/chromium 及其系统依赖（自检命令见环境记录）。
6. **运行纪律**：长 run 须脱离终端会话（tmux/setsid）;失败 run 目录按 AGENTS.md 一律保留,重试用新 run id。
7. **容器内发起评测的路径陷阱**：docker socket 直通宿主时,`-v` 路径按宿主解析;须使用宿主可见路径形式（本机为 `/data/daweiwang/...`）。
