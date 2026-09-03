# 路径教义:框架产物观 × 评测坐标的根治方案

2026-09-03 · 承接 8/26 坐标系地图(否决"提示词带绝对路径")与 8/31 原生产物观调查
("评测索要的产物不在任何框架的原生词汇表里"; ml_agent.py:36 "ALL code must
reside within the project directory")。

## 问题(三层病因)

1. **词汇表缺失**: 契约用评测坐标("workspace 根")表述交付位置,框架世界观只认自己的
   坐标(project/ 等)。
2. **坐标矛盾 → 落位散乱**: agent 同时收到框架指令(进 project/)与注入规格(到根),
   不同模型各自站队 → "有时在 project 有时不在"不是随机,是矛盾的必然。
   (luna 服从规格出过分; DS 服从框架写 project/。)
3. **临时层蒸发**: 可写宇宙中存在未挂载区域(mcar /project),完成的工作物理消失。

## 方案(四件,评分标准零改动)

1. **规格翻译**: 交付规格追加坐标注解——"root-level 即你的 workplace 顶层;写进
   project 目录同样会被收集"。矛盾消除于源头。已落: ARC/babylm 生成器 EVALUATION;
   mcar 由 /project 挂接物理对齐,不改契约级文档。
2. **交付地图**: `real_eval/scripts/resolve_native_artifacts.py` —— 每 topic 一张
   声明式有序候选表,宿主收尾阶段按序原地查找,**符号链接**到验证器/冻结打分器期望
   处(纯别名,零内容拷贝,lstat 纪律不跟随外部链接,sidecar 随行,全程审计到
   delivery_map_resolution.json)。已接: ARC(替换部分搬运块)、babylm(评分接线前)。
   验收层(exit_delivery_check)在其后照常查缺补漏。
3. **持久化不变量**: agent 可写宇宙 ⊆ 挂载。核查结论: ARC ✓(/workplace 即挂载);
   babylm 曾有缺口(tcp_server 默认 cwd=/workplace ≠ 挂载点 /workplace_<runid>)
   → 已双挂载同一宿主目录到两个路径; mcar /project → 已挂接(f943c72)。
   兜底纪律: 销毁工作容器前先 `harvest_before_rm.sh`(逐字节 docker cp,不变换)。
4. **明确不做**(用户裁定): 评分/合规解耦(完整性单独打分)不实施;官方打分器、
   门检 REQUIRED 清单、契约原文一律不动。

## 公平性论证

- 对称性: 输入侧"按各框架原生格式投喂"已被接受;输出侧同理——考研究能力,
  不考"会不会写到评测方指定的绝对路径"(该坐标不在任何框架词汇表中)。
- 地图纯机械(路径别名,零内容),对同一框架下所有模型一致,留档可审计。
- 契约"root-level"的重释(注解+地图)属裁量点,记协作者清单待批;批准前照旧。

## 诚实的残余

1. 地图外落位仍可能(模型自由度)→ 持久化+收割留证、地图按证据迭代、
   缺失如实记 unresolved(不 глад)。
2. 冻结打分器硬编码布局(mcar evaluate.py)→ 别名(symlink)是桥的最后残迹,
   内容零拷贝,但"零宿主动作"不成立;如实声明。
3. runs/ 已 193GB 且按 AGENTS.md 只增不删 → 磁盘红线前需团队定归档策略。

## 验证记录

- 解析器在留存空心 DS run 上彩排: estimator.py 从 project/ 解析+sidecar 随行,
  **经符号链接实跑 predict → (32,256) 全有限** ✅;缺失四件如实 unresolved ✅。
- babylm 双挂载/解析器接线均 bash -n 通过;正跑中的 run 用快照,不受影响,下轮生效。
