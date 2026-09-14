# ARC 任务定义缺口:调查记录(2026-09-14,已撤销试验,留档待议)

状态:**发现成立,试验补丁已按用户决定撤销**(revert 9944f70)。用户判断:非决定性因素,后续团队再议。本文是完整证据链与复原配方。

## 一、发现

框架可见的任何文档都没有定义 ARC-WBE 的估计目标语义:

- "mean activation" 在什么**输入分布**上取平均 —— 未写
- 权重矩阵的**乘法方向**(x@W vs W@x)—— 未写
- 官方主指标是**末层** MSE、**lower is better** —— 未写(我们 scoreboard 还把方向标成了 ↑,待修)

而官方 AIcrowd starterkit(本地拷贝 `/root/whest-starterkit`)在 README 第一段就公开了全部定义;丢失发生在我们的 materialization(metadata.json 政策把 "sampling metadata" 连同任务定义一起留在了 host 侧)。

## 二、证据(全部独立核验过)

1. **真值语义实证**:x~N(0,1) + `x = max(x@W, 0)` 前向模拟 vs 真值 `all_layer_means`:10/10 条记录 cos=1.0000(错误方向 cos=0.39)。官方参考实现 `local_engine.py:77-80` 与此逐行一致。
2. **官方分数复现**:whest 官方日志显示 luna 0.0909 = 末层MSE 0.909×0.1、DS 0.0886 = 0.886×0.1;公式 `adjusted = final_layer_mse × max(0.1, C/B)`,v1-phase1 预算 B=2.72e11(DS run utilization 0.00096 反推吻合)。
3. **01-DS 被隐藏约定所伤(定量)**:其 estimator 明确尝试了"真实 ReLU 前向传播"路线,但乘法方向猜反;原样 cos=0.348,**转置权重后 cos=0.956**。01-luna 则是方法本身弱(翻转无效,cos≈0.12),不能归因于此。
4. **可见字节穷举**:01/02 run 工作区、契约、summary、预算文档、全部注入 prompt、容器挂载——定义零命中(仅评分器脚本含指标名 `adjusted_final_layer_score` 半条线索)。

## 三、试验(已撤销)

`patch_task_definition_restore.py`(见 git 历史 9944f70→revert):env 门控(默认0)、只改 run 工作区蓝本副本、canonical 零接触。试验发 fullrun_arc_02_luna_20260914_102631:

- **定义生效**:stage1 死因中 circular/tautology/permutation 归零(此前 16/20);节点开始用 standard_normal 造合法监督;idea 首次命中真研究前沿("Low-Rank Uncertainty Propagation for Cheap White-Box ReLU Mean Estimation",直指矩传播 vs MC)
- **但 stage1 仍 18/18 全灭**:judge 改咬真实实现 bug(恒为 1.0 的 clamp 指标、声称确定性却用 MC 探针、跨 rank 平均的无意义 loss)
- → **结论:定义缺口真实存在且改变失败性质,但不是 luna×02 通关的决定性因素**(用户判断,数据支持)

## 四、连带待办

- scoreboard ARC 行方向标注(↑ 应为 ↓,lower is better;加粗随之)
- luna×02×ARC 七发 stage1 档案:034336 5/13 通过(孤例),此后 ~104 节点 0 通过;死因分层见各 run journal
- 若团队批准恢复定义:正式做法是写进 `generate_arc_wbe_2026_native_inputs.py` 的 summary 生成 + 契约,对全框架一致生效;措辞照抄 starterkit README(纯任务定义,不提方法);注意 01 旧分与新分不同口径

## 五、复原配方(如需重试)

`git revert <revert-commit>` 或按 9944f70 的三件套重做:补丁文件 + wrapper staging/调用两行 + runner env 透传一行;launcher `export ARC_WBE_2026_RESTORE_DEFINITION=1`。
