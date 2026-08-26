# debug/ — 调试与修改记录

本目录记录 ResearchClawEval 公开仓库在真实评测中排障、修复的完整过程,面向团队协作与后续整合。

## 目录结构约定

**按记录归属人组织**：每位协作者在自己名下的子目录（如 `dawei/`）维护其调试与修改记录,便于确认问题出自谁的环境与工作线,后续整合时由团队统一合并去重。

## dawei/ 当前记录

| 文件 | 内容 |
|---|---|
| [2026-08-25-environment-setup.md](dawei/2026-08-25-environment-setup.md) | 评测机环境搭建排障：容器挂载路径解析、镜像缺依赖、模型名默认值、whest 打分器、网络加速、运行纪律 |
| [2026-08-26-01-arc-bug-analysis.md](dawei/2026-08-26-01-arc-bug-analysis.md) | 框架 01 × ARC "跑不出分数" 的完整 bug 链分析与可复现证据 |
| [2026-08-26-01-arc-fix-log.md](dawei/2026-08-26-01-arc-fix-log.md) | 对应修复的分步实施日志（分支 `fix/01-arc-delivery`,每步一 commit + 独立测试） |
| [2026-08-26-02-arc-blockers.md](dawei/2026-08-26-02-arc-blockers.md) | 框架 02 × ARC 阻塞项：发布遗漏的适配文件（已重建待校对）、S2 key 硬依赖 |
| [collaborator-checklist.md](dawei/collaborator-checklist.md) | 需要与其他协作者对齐/索取的事项清单（持续更新） |

## 记录约定

- 每条记录写清：现象 → 证据（日志/路径/复现命令） → 根因 → 处置（含 commit 号） → 影响面。
- 修改一律标注作用域（哪些文件、影响哪些 framework×topic 组合）。
- 建议在文中标注问题性质,便于整合：**换一台机器/换一个人还会复现 → 仓库级;仅本环境 → 环境级**。
- 失败 run 的目录按 AGENTS.md 规定全部保留,文中引用 run id 即可回溯。
