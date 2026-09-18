# 02 (AI-Scientist-v2) × 契约：结构性冲突分析

日期：2026-09-18。前提：假设 AI-Scientist-v2 原框架设计良好；问题出在我们的契约要求、host 架构与框架架构/内部 prompt 之间的逻辑冲突，而非单个 topic 的表现。所有引用均来自仓库内 `AI-Scientist-v2/` 源码与今日运行日志。

## 0. 今日证据（TDC run 073215、babylm run 051954）

| 运行 | journal 节点 | 跑完 | 崩溃 | judge 非 buggy | 进入 improve 分支 | 节点代码行数 |
|---|---|---|---|---|---|---|
| TDC 02×luna | 15 | 8 | 7 | 0 | 0 次（"Checking good nodes" 后回到 draft 10 次） | 392–592 |
| babylm 02×luna | 7（另 2 发被 worker 超时丢弃） | 5 | 2 | 0 | 0 次 | 268–332 |

跑完的 13 个节点被判 buggy 的理由全部是方法学/报告一致性（选择逻辑与声明不符、行序错位、比较条件不受控、cache 状态管理），不是契约合规。崩溃的 9 个里 2 个是解析器 bug（无散文的纯代码回复），其余是普通 API 误用。

## 1. 框架原生架构（源码事实）

1. 流水线：topic.md → `perform_ideation_temp_free.py`（"grant proposal" 式创意、S2 查新、5 轮反思）→ idea JSON {Title, Abstract, Short Hypothesis, Experiments, Risk Factors} → `launch_scientist_bfts.py` 四阶段 BFTS → 绘图 + VLM 反馈 → writeup（独立 LLM 从 journal/npy/图/引文写 LaTeX 论文）→ review。
2. **节点 = 一个小实验**。`_draft` prompt："implement a solid baseline… Focus on getting a simple but working implementation first… We will explore more advanced variations in later stages"；设计草图要求 6–10 句。
3. **stage 1 的目标是"基本能跑"**（`main_stage_goals[1]`："basic working implementation / simple dataset / basic functional correctness"），**一旦出现一个 good node 立即结束**（`_check_stage_completion`）。stage 2：调参 + "引入两个新 HuggingFace 数据集"；stage 3：探索 idea 的 Experiments 计划（**Experiments 字段只在 stage 3 注入 task_desc**，`_curate_task_desc`）+ "共用三个 HF 数据集" + 若跑得太快要求"用满 60 分钟"；stage 4：消融。
4. **judge**（`parse_exec_result` + `review_func_spec`）："is_bug: true if the output log shows that the execution failed **or has some bug**"。judge 只看 task_desc + 代码 + 输出。`is_buggy = is_bug or exc_type or 指标解析失败`。
5. **debug prompt 不含 judge 的 analysis**（只有代码 + term_out + VLM/时间反馈）。设计假设：bug 在输出里可见。
6. **搜索**：`_select_parallel_nodes`：未满 num_drafts 就起草；以 debug_prob 随机挑 buggy 叶子 debug；否则若 good_nodes 为空**回到起草**；只有存在 good node 才走 improve（best-first 的核心）。
7. **指标**：`_define_global_metrics` 由 LLM 从 Title/Abstract/Hypothesis 自拟一个指标（今日 babylm 拟出 "Cache Reuse Gain on Cache-Hit Tokens"；ARC 历次是"置换一致性"），coder 必须实现并打印，解析步骤找不到就判 buggy。
8. **环境假设**：`_prompt_environment`："Feel free to use any other packages too (all packages are already installed!)"；draft 指南："Make sure to create synthetic data if needed"；stage 2/3 目标依赖 HF 下载。
9. **交付物**：experiment_data.npy、图、journal、writeup 生成的论文。框架里没有 predictions.csv、experiment_trace.json、claim 标记、reproduce.py 这些概念；论文由 writeup 模块**在实验之后**从 journal 综合，不由实验代码书写。

## 2. 我们的契约/架构（以 TDC 为代表，psydef/babylm 同型）

一个程序在运行中完成：research_idea.json（实验前锁定）→ 2–4 个配置各自的 config/预测/指标/日志 → 调官方 validation scorer → 选择 → predictions.csv（测试集）→ experiment_trace.json（精确 schema + claims）→ paper.md（每个数值单元格带 claim 标记）→ environment.json → reproduce.py。固定数据集、离线、不许装包、预算 3600 s。host 只审最后落盘的根目录文件；禁止 host 回填。wrapper 在 stage 1 后停止（psydef/babylm/TDC）。

## 3. 逻辑冲突

### C1 工作单元错位（根本冲突）
框架的"研究"由**树 × 阶段 × writeup**组装：单节点只做一个小实验，多实验比较由树和后续阶段完成，论文由 writeup 写。契约要求**单个程序**就是一整项研究（多配置 + 选择 + 论文 + 追溯）。于是我们把整项研究塞进 stage 1 的一个节点：
- 节点代码 400–600 行（TDC）/ 270–330 行（babylm），与 draft prompt 的"simple baseline、6–10 句草图"直接矛盾；
- stage 1 之后被 wrapper 截断，框架真正的研究机制（stage 2–4 的树搜索、journal memory、绘图/VLM、writeup）从未运行；我们评的是"luna 写一个大脚本 + 一个 judge 循环"，不是 AI-Scientist-v2；
- idea 的 Experiments 字段（框架自己规划的实验）在 stage 1 根本不给 coder 看，只在 stage 3 注入；stage-1-only 的用法让框架的实验规划完全落空。

### C2 "experiment" 的双重定义
框架：experiment = journal 节点（被判定、被记忆、被选择）。契约：experiment = 一个程序 trace 里的一个配置。今日 TDC 实际运行 15 节点 × 3 配置 = 45 次配置训练，trace 只记录最后 3 个；契约"不得开始第五个配置"在运行层面名存实亡，预算核算只对最后一个节点成立。host 看到的"2–4 个实验"与框架真正做过的事不对应。

### C3 judge 语义 vs 契约完整性（为什么"全 buggy"是必然）
`is_bug` 的定义是宽泛的"有 bug"，在原生场景审的是一个小 baseline，"bug"≈崩溃/输出荒谬。我们让它审一整篇带选择逻辑、claims、论文的研究程序，"bug 表面积"随程序体积增长；luna 作为 judge 把方法学缺陷也算 bug（复判实验证明这是稳定判定，非噪声）。后果链：
1. 完整跑完的节点因方法学被判 buggy；
2. debug prompt 不含 judge 分析，而这类节点的 term_out 看起来一切正常 → **coder 得不到任何关于"错在哪"的信息**，方法学缺陷在设计上不可 debug（debug 路径是为崩溃设计的）；
3. good_nodes 永远为空 → 搜索永远在 draft/debug 间打转，best-first 的 improve 分支一次都没执行（TDC 0/15、babylm 0/7）；
4. 每次重新起草都是一个新的 500 行程序，带来新的普通 bug。
这不是"luna 差"，也不是"judge 太严"能单独解释的，而是**judge 的粒度（一个 baseline）与我们交给它的对象（一整项研究）不匹配**。

### C4 阶段目标 vs 契约约束
stage 2/3 硬编码"引入两个/三个 HuggingFace 数据集"、stage 3 要求"用满 60 分钟"，与固定数据集、离线、预算的契约矛盾。所以我们要么在 stage 1 后截断（回到 C1），要么让它跑全程去撞离线门（ARC 的经历）。在不改阶段目标（红线）的前提下，不存在同时满足两者的配置。

### C5 论文/追溯的作者归属
契约："框架作者的" paper/trace，host 不得回填。框架："论文由 writeup 模块在实验后从 journal 写；实验代码不写论文"。我们把论文写进实验脚本，意味着"论文"是代码里的模板，在结果产生前就写定 → 正是 judge 反复指出的"报告不完整/选择逻辑与声明不符"。ARC 的 plan-b（在 writeup 槽位交付）才是符合框架结构的位置，但契约又要求 trace 记录"2–4 个实验"，而树里有 15 个节点：journal→trace 是一次 host 侧格式桥接，需要契约层面明确它是否属于"回填"。

### C6 自拟指标 vs 官方指标
`_define_global_metrics` 只看 Title/Abstract/Hypothesis，自拟一个指标并强制 coder 实现。官方指标（macro AUROC / 词级 ppl / psydef score / ARC MSE）只有出现在 task_desc 时才可能被选中。我们为了不让 judge 看到契约而把事实移出 task_desc，副作用是指标定义器也看不到官方指标（babylm 今日拟出一个自造的 cache 指标，ARC 历次拟出置换一致性并成为陷阱）。这是同一个 task_desc 被三个角色（coder、judge、指标定义器）共享导致的两难。

### C7 ideation 的取向
ideation 系统 prompt 要求"novel、creative、out of the box、区别于文献"，并做 S2 查新；契约要的是固定数据集上 1 小时内可完成的 2–4 配置研究。越有野心的 idea → task_desc 越复杂 → stage 1 程序越大 → C3 越严重。

### C8 环境假设
"all packages are already installed"、"create synthetic data if needed"、"CRITICAL GPU REQUIREMENTS" 与离线/不装包/无 GPU/不许合成数据的契约相反；coder 在两套指令之间取舍（TDC 有节点尝试 RDKit 不存在的路径）。

### C9 执行模型与预算
单文件 exec、按输出判定、每节点 3600 s；契约把 60 分钟预算交给 stage 1 节点，而框架设计 stage 1 节点应当很快、stage 3 才放大。父进程等待与子进程时限相等的 bug 让"用满预算"的节点必然被丢弃（babylm 两发各损失 1 小时）。

## 4. 结论

"大量 buggy"不是运气也不是单点 bug，而是 C1 → C3 的必然：**我们把框架的一个"小实验"节点当成了整项研究的容器，而框架的 judge、debug、搜索、阶段、writeup 全部是按"节点 = 小实验、研究 = 树 + 阶段 + writeup"设计的**。逐症状打补丁（S2 超时、worker 数、reproduce.py、claim 单元格）解决的是基础设施层，不触及这一层。

## 5. 可选方向（需团队/契约层决定，本人不单方面实施）

- **A. 框架原生模式**：让框架按自己的方式跑完（idea → 四阶段 → writeup），host 用**确定性格式桥接**把原生产物（journal、best node 的代码与保存的预测、writeup 论文）映射到契约 schema；契约需明确"experiment = journal 节点"、"2–4 个实验 = 各阶段最佳节点"，并区分"格式桥接"与"内容回填"。stage 2/3 的 HF 数据集目标要被认定为"环境假设"（基础设施）还是"框架认知"（红线），需要决定。
- **B. 契约原生模式（现状）**：承认我们评的是"coder 循环 + judge 门"，stage 1 only；在计分板上如实标注；接受 judge 门大概率不通过、以最后落盘交付计分。此时 num_drafts/iters 的意义只是"多写几遍脚本"。
- **C. 折中**：stage 1 = 单配置 baseline（原生），stage 2–3 = 契约的 2–4 个配置（树），writeup 槽位 = 交付；前提同样是 stage 目标里的 HF 数据集条款如何处置。

无论选哪条，建议先在契约层面回答两个问题：(1) "experiment"以谁的定义为准；(2) "框架作者的论文/追溯"是否包含框架 writeup 模块从其 journal 生成的内容。
