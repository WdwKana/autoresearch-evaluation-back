# 02 (AI-Scientist-v2) stage1 失败机制分析与对照实验报告(2026-09-17)

面向团队讨论。结论先行:**02 的 stage1 失败不是随机事件**;judge 稳定,失败是草稿的确定性质,而每个 topic 的失败驱动不同:psydef 是 wrapper 缺陷(已修通、已出分),ARC 是任务定义缺失(试验显示失败性质随之改变,但未在中止前出现通过节点)。

## 一、判定链的代码事实(AI-Scientist-v2/ai_scientist/treesearch)

| 机制 | 位置 | 含义 |
|---|---|---|
| 节点判 buggy 三条路 | parallel_agent.py:713, 1634-1659 | judge `is_bug` ∨ 执行异常 ∨ 指标解析失败 |
| judge 的输入 | parallel_agent.py:690-699 | 只看 task_desc(Title/Abstract/Hypothesis+阶段目标)+代码+执行输出;**看不到 impl_guideline** |
| 自动指标定义 | parallel_agent.py:1194-1222 | 每阶段由 LLM 从 task_desc 提一个指标,coder 被强制实现 |
| 抽取器要求"先有自然语言再有代码块" | parallel_agent.py:672-681 | luna 纯代码回复→3 次重试→原文当代码→SyntaxError;137 个 stage1 节点中 11 个(8%)死于此,plan 全空 |
| debug 看不到 judge 判词 | parallel_agent.py:494-507 | 只给执行输出;被判"方法学有误"的节点无法对症修 |
| stage1 完成条件 | agent_manager.py:434-442 + journal.py:390-407 | 需 `is_buggy is False` **且** `is_buggy_plots is False`(需 npy→画图→VLM 链) |
| workers 上限 | parallel_agent.py:1179 | `min(num_workers, num_gpus)`;GPU 箍死 1 卡后恒为 1 |
| interpreter 执行语义 | interpreter.py:135-144 | `exec(code, {})`,`__name__ != "__main__"` |

**judge 一致性(复判实验,同模型同温度 0.5,每节点 6 次)**:两个通过节点复判 11/12 通过;五个被判节点复判 29/30 仍被判。通过/失败是草稿性质,不是骰子。

## 二、ARC:失败驱动 = 任务定义缺失 → 指标陷阱

- 9 发 ARC run 的自动指标**全部**是"置换/对称一致性"(日志 Defined eval metrics),对置换不变特征恒真(套套逻辑);coder 因无可计算目标而从特征反造标签(循环论证)。judge 判词 90% 咬这两条。
- 两次通过发(034336: 5/13, replay: 5/10)的"5"实为 1 个真节点 + 3 个种子副本 + 1 个聚合节点;通过草稿是常规 train/val 设计。此前归因的 iters/workers/内核配方均为幻影(workers 恒 1)。
- 官方定义(starterkit README 首段 + local_engine.py):目标 = x~N(0,1) 输入下逐层 post-ReLU 激活均值,约定 x@W;评测预算 2.72e11 FLOP(v1-phase1),lower is better。我们的搬运在任何框架可见文档中都丢了这句(全框架缺失;01-DS 因乘法方向猜反从可能的 cos 0.96 掉到 0.35)。

**试验发 125627(定义放进 BFTS task_desc,ideation 不可见;提交 2e99831,标注不入记分)**,与对照 095951 单变量对照,用户中止于 stage1 第 8-9 节点:

| | 对照 095951 | 试验 125627(中止时) |
|---|---|---|
| judge 放行 | 0/12 | 0/8 |
| 循环目标构造 | 普遍 | **0/8** |
| 走解析矩传播路线 | 无 | 4/8 |
| 主要死因 | 套套指标/循环目标(概念性,不可 debug) | `np.math.erf`(NumPy 2.x 已移除)×4、shape/语法错(工程性,可 debug) |
| 自动指标 | 置换一致性 | 置换鲁棒性,但**定义为末层 MSE 之差** |
| judge 新判据 | — | "evaluation target is not the official ARC-WBE target"(开始按官方定义评价) |
| debug 次数 | 6/18 | **0/9**(原因未查) |

结论:定义改变了失败的**性质**(概念陷阱→普通 bug),但未在中止前产出通过节点;`np.math` 版本冲突与"零 debug"是下一步要看的点。

## 三、psydef:失败驱动 = wrapper 缺陷,已端到端跑通并出分

| run | 改动 | 结果 |
|---|---|---|
| 0828 ×3, 0914 ×2 | (旧) | stage1 全灭,"无输出" |
| 112949 | 恢复原生"禁 `if __name__=='__main__'`"规则 + 要求存 npy(c8b3917;之前 8/8 节点用了该门,exec 语义下一行不跑,容器内复现) | 16/16 节点真执行、官方分 0.197,**host 验证失败**:trace.experiments 为 dict |
| 115325 | 写明 trace list-schema + 结尾验证块(415190f) | `finished 0`,官方分 **0.1317**——02 首个正式出分格;judge 0/8 放行(合规猎捕,含发明的要求) |
| 122907 | 从 judge 可见的 task_desc 移除 MANDATORY 契约,仅留 coder-only guideline(e3b250a) | **首个草稿即放行,原生 Completed,`finished 0`,官方分 0.1371,4 分钟** |

psydef wrapper 设计上只跑 stage1(两实验模式:跳过多种子、`_create_next_main_stage` 返回 None、`--skip_writeup`),故"端到端"= ideation→stage1→原生 handoff→host 验证→出分,已完整走通。psydef 02 luna 真实水平 0.13-0.20,与 01 三模型同量级。

## 四、对"topic 特定"假设的判定

- **ARC 特有**:"stage1 造不出合法原型"(套套指标/循环目标),源于任务定义缺失;psydef 的自动指标是 macro-F1,不存在此病。
- **跨 topic 常数**:judge 一旦视野里有清单/标准就"必判";psydef 的触发器是 host 契约进 task_desc(已实证并移除),ARC 的触发器是原生指标定义(只能靠补定义间接改变)。

## 五、本日提交(本地,未 push)

a6bdfab HF 离线(ARC runner)| b0271b0/108ec58 数据文档加入又撤出蓝本 | 0c85257 设备级 GPU 箍束 | 324732c 收尾阶段方案 b(五文件交付已两发验证)| 1b1d629 iters 12 | c8b3917 / 415190f / e3b250a psydef 三连修 | 04b49db psydef runner GPU 箍束 | 1a2bf11 psydef scorer CLI | 2e99831 ARC 定义试验(试验用)| 4e31e1c/… debug 记录

## 六、待团队裁定

1. ARC 真值定义的 canonical 落点(全框架一致的 summary/契约;记分前必须统一,现有 ARC 分为旧口径)
2. exit_delivery_check(事后模型回填)在 psydef 的处置(本轮已停用)
3. 上游不对称:scorer CLI、trace schema 等"考试须知"各框架厚薄不一,是否拉平
4. 框架级放大器是否修:抽取器接受纯代码回复(8% 草稿)、debug 提示词回传 judge 判词、psydef 之外的 `__main__` 检查
5. scoreboard:02 行 psydef×luna 0.1371(122907)是否入表;ARC 列方向标注(官方分 lower is better)修正
