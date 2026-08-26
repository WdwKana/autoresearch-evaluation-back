# debug/ — 调试与修改记录

本目录记录 ResearchClawEval 公开仓库在真实评测环境中排障、修复的完整过程,面向团队协作与后续整合。按时间与主题分文件：

| 文件 | 内容 |
|---|---|
| [2026-08-25-environment-setup.md](2026-08-25-environment-setup.md) | 环境搭建期排掉的全部问题：容器挂载路径、镜像缺依赖、模型名默认值、官方打分器安装、网络加速 |
| [2026-08-26-01-arc-bug-analysis.md](2026-08-26-01-arc-bug-analysis.md) | 框架 01 × ARC "跑不出分数" 的完整 bug 链分析与证据 |
| [2026-08-26-01-arc-fix-log.md](2026-08-26-01-arc-fix-log.md) | 对应修复的分步实施日志（分支 `fix/01-arc-delivery`,每步一个 commit + 独立测试） |
| [2026-08-26-02-arc-blockers.md](2026-08-26-02-arc-blockers.md) | 框架 02 × ARC 当前阻塞项与已做的临时处置 |
| [collaborator-checklist.md](collaborator-checklist.md) | 需要与其他协作者对齐/索取的事项清单（持续更新） |

## 约定

- 每条记录写清：现象 → 证据（日志/路径/复现命令） → 根因 → 处置（含 commit 号） → 对其他框架的影响面。
- 修改一律标注作用域（哪些文件、影响哪些 framework×topic 组合）。
- 失败 run 的目录按 AGENTS.md 规定全部保留,文中引用 run id 即可回溯。
