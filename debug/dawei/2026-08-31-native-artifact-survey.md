# 七框架"原生产物观"代码级调查

2026-08-31 · 方法: 01/02/04 读本地源码,03/05/07 进运行时镜像或钉定上游 commit,06 仅存 manifest/patch 线索。
问题: 各框架被设计时,自己想交付什么?其约定与评测契约冲突几何?

## 总表

| 框架 | 原生终点产物 | 世界观强度 | 强制层 | 关键证据 |
|---|---|---|---|---|
| 01 AI-Researcher | 七章节 LaTeX 论文 | 强 | 代码+提示词 | ml_agent.py:36 "ALL code must reside within the project directory"; paper_agent/*/writing_templates/{abstract..conclusion} 模板树 |
| 02 AI-Scientist-v2 | ICML/ICBINB 会议 PDF + 自我评审 | 强 | 代码结构 | blank_icml_latex/template.tex, perform_icbinb_writeup.py, perform_llm_review.py; 节点树+字段路由 |
| 03 ARIS | 评审过的 paper/main.pdf + MANIFEST.md 留痕链 | 强 | **纯提示词**(技能 md) | 80 技能;output-versioning.md 规定 idea-stage/refine-logs/review-stage/paper/ 四阶段目录;评测文件名在源码零命中 |
| 04 AutoResearchClaw | paper_final.md/paper.tex + deliverables/ 包 | **最强** | **代码强制** | contracts.py 23阶段类型化产物契约,executor.py:680 缺产物判 FAILED;12套会议模板含.sty,编译测试;评测名只能走 prompts.extra_prompts 外挂 |
| 05 DeepScientist | paper/paper.pdf + 类型化 artifacts/ JSON 库 | **最强** | **代码+工具+schema** | layout.py QUEST_DIRECTORIES 冻结30目录;RESULT.json 由框架代码而非 agent 写;SKILL.md 禁止在 artifact.record_main_experiment() 之外宣称成功 |
| 06 Dr. Claw | (未验证;chat 工具循环形态) | 弱? | — | 仅 manifest: node server/cli.js chat;补丁只动中继/生命周期 |
| 07 EvoScientist | final_report.md(六章节模板)+artifacts/ | 中·双层 | 基础设施硬/研究产物软 | paths.py 硬编码 runs/、sessions.db;研究产物在 prompts.py 全标 "recommended";名字上无进化算法 |

## 三个普适发现

1. **7/7 都有自己的产物观**;除 06/07 外,原生终点产物全是**学术论文**(五个框架内置 LaTeX/会议模板)。
   而本评测拒收论文(客观打分原则) → **评测索要的成果物(estimator/predictions/checkpoints)不在任何框架的原生词汇表里**
   (03/04 已 grep 验证源码零命中;01/02 靠注入;05 靠 --message)。
2. **预测冲突的不是世界观强弱,而是三轴**: ①强制层(代码硬 vs 提示词软) ②契约进场通道(主指令 vs 被路由附件) ③空间墙。
   - 03 丝滑: 强而软 + 契约即主指令 + 无墙 → 一段指令覆盖全部软约定
   - 05 丝滑(推定): 极硬,但 wrapper 做了配置级手术: --home 迁入 /workspace + baseline_gate 豁免 + --message 主指令
   - 07 丝滑: 软 + 原生 final_report.md 与契约撞名(顺水推舟)
   - 01/02 痛: 需源码级补丁(墙/路由器长在代码里,配置够不着)
   - 04 最痛: 代码强制的23阶段契约,评测只有 extra_prompts 一个外挂孔,框架无论如何都产自己的 paper_final.md 宇宙
3. **适配成本的真正分水岭 = 框架暴露的配置面**: 05 有 --home/quest.yaml/runners.yaml 可动手术,55行 wrapper 驯服最硬世界观;
   01/02 无此类配置面,只能 rsync 后打源码补丁(443/91行起步)。给未来评测选型的启示:看配置面,不看名气。

## 附: 各探员调查为镜像/上游取证,细节存 scratchpad 任务输出;03 源自钉定 commit 590ce825 (本地检出已被清空)。
