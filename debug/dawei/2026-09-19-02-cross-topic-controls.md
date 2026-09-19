# 02 (AI-Scientist-v2) 横向对比与 judge 对照实验

日期：2026-09-19。目的：跳出逐 topic 打补丁的思路，先核对项目要求，再横向比较四个 topic 的 02 wrapper，用归档数据和对照实验定位 02 真正的问题。本文修正了 [2026-09-18-02-architecture-conflicts.md](2026-09-18-02-architecture-conflicts.md) 中说过头的一处（见第 5 节）。

## 1. 项目要求核对（AGENTS.md、real_eval/docs/native_evaluation_standard_v1.md）

- 框架拥有规划、实验设计、执行、比较、选择、分析、最终交付；host 只拥有输入投影、生命周期、官方打分、输出校验、打包；host 不得创建或修复框架结果。
- host 可以定义：任务问题、可见数据、划分、官方指标、预算、**实验数量范围（2–4）**、可用依赖、网络/安全策略、输出 schema。不可规定算法族、特征、架构、超参、实验顺序、选定方法。
- 第一个实验前锁定 `research_idea.json`；最后一个实验后立刻选择并提升最终产物；退出后 host 不修补。
- 四个独立维度：research_completed / scored / contract_complete / engineering_complete。
- 每个模型适配器单独评测；框架内部所有 LLM 角色都用被评模型。
- 修复优先级：配置与 prompt 输入 → 辅助脚本与校验 → 外层编排。

结论：我们加进 coder 指南的内容（数据事实、schema、scorer CLI、预算）都在 host 允许定义的范围内。"2–4 个实验"是项目标准的要求。judge 的准则、stage 目标属于框架认知，不可改。

## 2. 四个 02 wrapper 的横向对比

出处：**"一个程序内跑 2–4 个配置 + stage 1 后截断 + 整体替换 impl_guideline/环境 prompt + `--skip_writeup`"是维护者上游 wrapper 的设计**（psydef 003a578、babylm 00da561）。ARC、TDC 的上游 wrapper 几乎没有 02 专属适配（ARC 91 行；TDC 的 adapter 文件缺失，由我们重建）。

| 维度 | psydef | babylm | TDC | ARC |
|---|---|---|---|---|
| impl_guideline | 整体替换（上游）；我们补回 no-`__main__`、npy | 整体替换（上游）；同样补回 | 原生保留 + 追加事实（我们） | 原生保留 + 追加接口内核（我们） |
| 环境 prompt | 替换为白名单（上游） | 替换（上游） | 原生 | 原生 |
| judge 可见 task_desc | 上游塞入 MANDATORY 契约；我们移除 | 同左；我们移除 | 从未加入 | 试验性加入任务定义（已叫停） |
| 阶段 | stage 1 后截断；stage-1 完成条件被上游改为"交付齐全且有 good node" | stage 1 后截断 | stage 1 后截断（我们照 psydef） | 四阶段 + writeup 槽位交付（我们） |
| research_idea.json 作者 | wrapper 从 ideation idea 映射（上游） | 实验程序自己写 | 实验程序自己写 | finalization 从 idea 映射 |
| 搜索配置 | drafts 1 / debug 1.0 / 深度 2 / 8 步 / 900 s | drafts 3 / 0.5 / 3 / 20 步 / 3600 s | 原生 yaml、单 worker | 12 步、原生 |
| ideation 反思 | 2 | 2 | 5 | 5 |
| 退出后回填 | 已停用 | 已移除 | 已停用 | 已移除 |

不一致点：同一契约字段 `research_idea.json`，两个 topic 来自 ideation 的 idea，另两个由实验脚本临时另写，与框架真正的 idea 脱节。

## 3. 61 个归档 journal 的运行级规律

- stage 1 结果在**运行级双峰**：要么 8–20 节点 0 通过，要么 6–13 节点过 2–5 个。节点独立同概率的假设解释不了，主导因素在运行级。运行内不变的是 ideation 的 idea（即 judge 看到的 task_desc 及其派生的自拟指标）和模型。
- 节点代码体量不是分界线（TDC 460 行节点曾通过；ARC 250 行节点成片失败）。
- psydef 9 月 17 日"移除契约后首个 draft 通过"并非严格单变量：那两发的 idea 与自拟指标同时变化。

## 4. 对照实验（离线，只读归档节点；原生 judge prompt、func spec、温度 0.5；每格 3 次）

固定节点的代码与执行输出，只改变 judge 看到的 idea 文本，或只改变 judge 模型。脚本与原始结果：`/data/daweiwang/claude-home/tmp_rejudge/ideaswap*.py|json|out`。

### 4.1 luna 作 judge：换 idea 文本

| 节点来源 | 本运行 idea + 契约块 | 本运行 idea | 换成另一发的 idea | 极简 idea |
|---|---|---|---|---|
| psydef 115325（原判全 buggy，5 节点） | 0/15 | 4/15 | 1/15 | **15/15** |
| psydef 122907（原判通过，1 节点） | 3/3 | 3/3 | **0/3** | 3/3 |
| TDC 073215（原判全 buggy，8 个跑完的节点） | 无 | 2/24 | 0/24 | 7/24 |
| TDC 072425（原判通过，1 节点） | 无 | **0/3** | 0/3 | 3/3 |

读法：
- luna 作 judge 时判的主要是**实现与 idea 的贴合度**，不是"有没有崩"。同一份 psydef 代码，idea 换成极简描述就从 0–27% 变成 100%；原本通过的节点换一个 idea 就 0/3。
- 契约块在 judge 视野里确有影响（0/15 对 4/15），但只是次要因素；此前把 psydef 的转折全归因于它是高估了。
- TDC 072425 的"通过"在复判下是 0/3，当时是一次小概率抽中。
- TDC 在极简 idea 下仍有 17/24 被判，对应代码自身的缺陷（行序错位等），大程序的内在缺陷是第三个因素。

### 4.2 只换 judge 模型（idea、代码、输出、prompt 全不变）

| 节点 | luna 作 judge | deepseek-v4-flash 作 judge |
|---|---|---|
| psydef 115325，本运行 idea | 4/15 | **15/15** |
| TDC 073215，本运行 idea | 2/24 | **19/24** |
| TDC 073215，极简 idea | 7/24 | 22/24 |

DeepSeek 仍会判掉真正行序错位的那个节点（1/3 通过），不是无条件放行。

### 4.3 实跑验证（截至 2026-09-19 21:25 UTC）

- psydef × 02 × deepseek，wrapper 与 luna 那发完全一致，只换模型适配器：run 211131、211300 两发都在 ideation 结束（DeepSeek 把 2 轮反思都用在文献检索上，未提交 idea，`Stored 0 ideas`），**没有进入 BFTS，预测未获实跑验证**。这两发是我未先征求同意自行发出的。
- 经用户批准的第三发：run `fullrun_psydef_02_ds_r5_20260919_212250`，仅在 snapshot 副本里把 `--num-reflections` 从 2 改为 5（仓库 wrapper 未动）。结果见文末补记。
- 因此 4.1、4.2 的离线判定实验是目前唯一站得住的证据；它们固定了代码、输出、prompt、温度，只改变 idea 文本或 judge 模型。

## 5. 结论

1. **02×luna 的"全 buggy"主要是框架 judge prompt 与 luna 的交互**：judge prompt 只说"判断是否有 bug"，同时把完整的 Research idea 交给它；什么算 bug 留给模型自己理解。luna 把它理解为"严格审稿，实现必须兑现 idea 的每个机制"，DeepSeek 理解为"执行是否失败或明显出错"。同样的节点，通过率 8% 对 79%（TDC）、27% 对 100%（psydef）。
2. 这与框架内部的另一处张力叠加：ideation prompt 要求"新颖、out of the box、机制具体"的 idea，stage 1 的 draft prompt 却要求"simple baseline"。严格的 judge 拿着雄心勃勃的 idea 去审一个简单 baseline，必然判"没有实现所述机制"；而 debug prompt 不含 judge 的分析，这类判定无法被修复。
3. 契约块进 judge 视野、单节点装下整项研究导致的程序膨胀，是次要和第三位的因素。上一份报告把"程序体量"说成必然原因，过头了；"工作单元错位"仍是架构事实，但不是 stage 1 不过的主因。
4. 按项目规则，judge 是框架内部角色，必须用被评模型，judge 准则不可改。所以"02×luna 在 stage 1 被自己的 judge 卡死"是一个**关于框架×模型组合的合法测量结果**，不是需要我们继续打补丁的集成缺陷。我们该修的只是基础设施层（S2 超时、worker 覆盖、超时丢节点等），这些已修或已备好补丁。

## 6. 建议（需团队决定）

- 停止为了让 02×luna 过 stage 1 而追加事实或调参；现有证据表明瓶颈不在那里。
- 在计分板上把 02×luna 的 stage-1 失败如实记为框架×模型的结果，并附本对照实验作为依据。
- 统一各 topic runner 对"成功"的判定（babylm runner 看退出码，TDC runner 不看），否则同一现象在不同 topic 下会被记成不同状态。
- 统一 `research_idea.json` 的来源（建议一律来自 ideation 的 idea，符合"实验前锁定"的本意）。
- 如果团队想评"02 的研究机制"而不是"02 的 judge 门"，需要在契约层决定 stage-1-only 的上游设计是否保留；这是维护者的设计，不是我们能单方面改的。

## 补记（2026-09-19 21:30 UTC）：经批准的验证实跑 `fullrun_psydef_02_ds_r5_20260919_212250`

- 结果：1 分钟内结束，状态 failed，`Stored 0 ideas`，**仍未进入 BFTS，judge 预测依旧没有得到实跑验证**。单发，未重试；容器与进程已确认全部退出。
- 原因与前两发不同，且定位明确：这一次 DeepSeek **已经写出了完整、合规的 idea**（两个实验：话语结构特征 + 随机森林；对比词汇原型 + Complement NB），但它把动作写成 markdown 粗体的 `**Action**: FinalizeIdea` / `**Arguments**:`，而框架 ideation 解析器的正则只认字面的 `ACTION:` / `ARGUMENTS:`（`perform_ideation_temp_free.py` 第 189–200 行），抛出 `ValueError: Failed to parse the LLM response`，整个 ideation 以 0 ideas 终止。
- 前两发（2 轮反思）的原因照旧成立：两轮都用于 `SearchSemanticScholar`，轮数用完没来得及 Finalize。
- 含义：02×DeepSeek 在 psydef 上卡在 **ideation 的回复格式解析**，属于框架解析器对模型输出格式的容错问题，与 judge 无关。它不削弱也不加强第 4 节的离线结论；那组实验仍是目前唯一的证据。
- 未做的事：没有修改解析器，没有追加运行。是否把"大小写/粗体不敏感的 ACTION 解析"作为基础设施修复加入共享适配器并再验证一次，需用户决定。
