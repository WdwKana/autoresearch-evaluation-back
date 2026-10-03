# 原生输入对照实验：judge 的严格是否来自我们的输入

日期：2026-09-19。用户批准后执行。先写预测，再跑实验。

## 分歧

- 用户的看法：judge 严格的根源是我们的输入（meta prompt 经 ideation 进入 judge 可见的 idea 文本）；原生输入下 luna 作 judge 不会这么严。
- 我此前的保留：idea 细节只是一半原因，luna 对模糊 judge 指令的"审稿式读法"是另一半，换成原生输入可能仍偏严。

## 实验二（离线归因，先做）

固定归档节点的代码与执行输出，luna 作 judge（原生 prompt、func spec、温度 0.5，每格 3 次），只改 judge 可见的 idea 文本：
1. own：本运行原始 idea；
2. stripped：同一 idea，**机械地**删除带流程承诺的句子，科学机制描述保留；
3. minimal：极简 idea。

删除规则在看到结果之前固定：把 Short Hypothesis 和 Abstract 按句切分，凡匹配下列正则的句子整句删除，其余原样保留（Title 不动）。规则与逐句的保留/删除清单见 `/data/daweiwang/claude-home/tmp_rejudge/stripped_ideas.json` 与本次会话记录。

已知不完美之处（不事后调整）：TDC 两个 idea 里各有一句同时含"配置枚举"和流程承诺（"Within a fixed computational budget, we compare three configurations: …"、"Three configurations are compared using identical train/validation data …"），被整句删除，少量机制信息随之丢失；机制主体仍在保留句中。

节点：psydef 115325 的 5 个跑完节点 + 122907 的通过节点；TDC 073215 的 8 个跑完节点 + 072425 的 1 个节点。

### 预先写下的预测

- 若用户看法成立：stripped 接近 minimal，远高于 own。
- 若我的保留成立：stripped 接近 own，仍明显低于 minimal（机制贴合度仍被判）。
- 我个人的事前估计：psydef 的 stripped 会很高（≥10/15），因为此前 11 条 buggy 理由里 9 条都是"在评估集上选择，与 idea 的承诺矛盾"；TDC 的 stripped 介于 own（2/24）与 minimal（7/24）之间，因为 TDC 还有与 idea 无关的真实代码缺陷。

## 实验一（原生基线，随后做）

02 框架只保留模型接入类补丁（provider 路由、responses 兼容、token 统计空值、S2 重试上限与超时），不加任何契约、指南、环境 prompt、ideation 系统 prompt 或 stage 完成条件的改动；上游默认搜索配置，仅 worker 数设为 1（GPU 限定物理 5 号）。stage 1 一结束由外部看护停容器，每臂 2 小时硬上限。
- 臂 A：上游自带的现成 idea（`i_cant_believe_its_not_better.json` 第一个）。不使用 `--load_code` / `--add_dataset_ref`：上游自带的同名 `.py` 是针对第三个 idea（病虫害图像识别）的图像训练代码并要求 HF_TOKEN，与第一个 idea 无关；README 明示不想用代码片段初始化时不要设该参数。
- 臂 B：上游自带主题文件 + luna 自己 ideation（视臂 A 结果再定）。
- 主指标：未抛异常节点中 judge 判非 buggy 的比例；崩溃节点、VLM 审图分别单列；跑完的节点再离线复判 5 次得到有分母的通过率。
- 事前估计：臂 A 的 luna 通过率过半，stage 1 在少数节点内结束。若如此，"02×luna 的 stage-1 失败是框架×模型的合法测量结果"这一说法应整体收回。
- 已知局限：原生臂同时换了输入、任务、数据与程序复杂度，单凭它分不清"idea 文本干净"与"玩具程序 bug 少"，归因靠实验二。

## 结果

### 实验二（离线归因，2026-09-19 22:4x UTC 完成；135 次判定，1 次调用出错）

| 节点 | own | stripped（删流程承诺句） | minimal |
|---|---|---|---|
| psydef 115325（原判 buggy，5 节点） | 2/15 | **7/15** | 15/15 |
| psydef 122907（原判通过） | 3/3 | 3/3 | 3/3 |
| TDC 073215（原判 buggy，8 节点） | 3/24 | 4/24 | 4/23 |
| TDC 072425（原判通过） | 0/3 | 1/3 | 3/3 |

对照预测：
- psydef：删掉流程承诺后通过率从 13% 升到 47%，方向支持用户的看法，但没有达到我事前估计的 ≥10/15，也远未到 minimal 的 100%。stripped 下剩余的 buggy 理由变成了"特征实现与 idea 描述的机制不符"（覆盖了特征列、speaker 特征取错轮次、上下文包含当前话语），另有 2 票仍自发提出"在评估集上选择"。也就是说：流程承诺约解释差距的三分之一，其余来自 idea 里**机制描述的具体程度**；换成不含机制细节的 minimal idea，同样的代码 15/15 通过，说明这些"bug"只相对于 idea 的具体描述才成立。
- TDC：own、stripped、minimal 三者几乎没有差别（3/24、4/24、4/23），判定由与 idea 无关的代码缺陷主导。用户的看法在 TDC 上没有得到支持。
- 噪声水平：TDC minimal 上一批是 7/24，这一批 4/23；单格 3 次的波动不小，小差异不应解读。

小结：judge 的严格**部分**来自我们输入带进 idea 的细节（psydef 明显，含流程承诺与机制细节两部分），**部分**来自程序自身的缺陷（TDC 主导）。"机制细节"是否也是我们的输入诱导出来的（数据 schema 与依赖限制让 ideation 把 idea 写到特征级），由实验一检验。

### 实验一臂 A（原生基线，run `control_native02_luna_armA_20260919_224152`，2026-09-19 22:47 UTC 结束）

- 框架只打模型接入补丁（容器日志："model adapter applied (no guideline / stage / contract patches)"），上游自带 idea #0（组合泛化正则化），luna 任全部角色，上游默认搜索配置，worker 数 1。
- stage 1 在 **4 分钟、3 个 draft** 内原生结束（"found working implementation"），看护随即停容器。3 个节点全部无异常跑完，每个约 3 秒、204–266 行，用的是合成数据的玩具实验。自拟指标为 "Held-Out Compositional Generalization Exact-Match Accuracy"。
- 实跑中的 judge：2 个判 buggy，1 个判通过。两个 buggy 的理由都是"实现没有有效检验假设"（`embedding(a)+embedding(b)` 可交换，无法表示有序对；正则项只是 MSE(z, raw)），不是崩溃。
- 离线复判（同一 native idea，luna，5 次/节点，共 15 次）：**0/15 通过**，包括实跑中被判通过的那个节点（0/5；理由："正则项没有绑定到明确的期望组合"）。实跑里的那次通过是一次小概率抽中。合并实跑与复判：18 次判定里 1 次通过。

对照事前预测：
- "stage 1 在少数节点内结束"：对，但原因不是 luna 变宽松，而是原生节点便宜（3 秒一个、两百多行），多试几次就能抽中一次通过。
- "臂 A 的 luna 通过率过半"：**错**。luna 在原生 idea、原生玩具程序上照样按"实验是否有效检验了假设"来判，通过率很低。
- 因此"严格的根源是我们的输入"这一看法没有得到臂 A 的支持；luna 对 judge 指令的审稿式读法在原生条件下同样存在。我们的输入的作用是叠加：psydef 上引入与契约自相矛盾的流程承诺（实验二：删除后 13% → 47%），并把每次尝试变得又大又慢又容易崩，使"多抽几次"这条原生出路走不通。

局限：只有 1 个 idea、3 个节点；judge 模型只测了 luna。

### 实验一臂 B（luna 原生 ideation，run `control_native02_luna_armB_idea0_20260919_225150`，23:00 UTC 结束）

- 上游自带主题文件 → 原生 ideation（ideation 系统 prompt 未改，`--max-num-generations 2 --num-reflections 5`）→ luna 生成 2 个 idea；本发跑第 0 个："I Can't Believe It's Still Confident: Shadow Counterfactuals for Detecting Silent Deployment Failures"。第 1 个 idea 尚未运行。
- luna 自己写的原生 idea 与我们契约下的 idea 一样长、一样具体：Short Hypothesis 556 字符、Abstract 1762 字符（上游示例为 224–242 / 744–1387）。"idea 写得细"并不是我们的输入诱导的，luna 在原生输入下同样如此；我们输入带来的特有成分只有流程承诺。
- stage 1 在 **7 分钟（含 ideation）、3 个 draft** 内原生结束。3 个节点全部无异常跑完，每个 4–5 秒、249–259 行、合成数据。自拟指标 "Silent-failure detection AUROC"。
- 实跑 judge：2 buggy（"干预实现与声称的方法不符：把特征置 0 而非条件重采样"；"silent_failure_auroc 与 sca_auroc 重复"）、1 通过。
- 离线复判（luna，5 次/节点）：1/5、0/5、3/5（实跑通过的那个），合计 **4/15**。

事前预测对照：复判通过率"低于三成" → 27%，勉强成立；"节点便宜则几个 draft 内结束" → 成立。

### 汇总：luna 作 judge，对"无异常跑完的节点"的通过率

| 条件 | 复判通过率 | 实跑 |
|---|---|---|
| 原生臂 A（上游 idea） | 0/15 | 1/3 |
| 原生臂 B（luna 自己的原生 idea） | 4/15 | 1/3 |
| psydef 契约条件，本运行 idea（两批） | 4/15、2/15 | 0/8（当时 task_desc 含契约块） |
| TDC 契约条件，本运行 idea（两批） | 2/24、3/24 | 0/8 |

luna 的单节点通过率在原生条件（约 13%）与我们的契约条件（约 8–27%）之间**没有明显差别**。差别在于尝试的成本与成活率：原生 6/6 节点无异常跑完、每个几秒；契约条件下约半数节点崩溃、每个几分钟到一小时。原生设计靠便宜的重试消化 judge 的严格，我们的契约把重试变贵、变脆。

结论（截至目前证据）：
1. "judge 严格的根源是我们的输入"没有得到支持：luna 在完全原生的输入、idea、玩具程序上同样按"实验是否有效检验了假设"严判。
2. 我们的输入确有两点特有的负面作用：psydef 上与契约自相矛盾的流程承诺（删除后 13% → 47%）；以及把节点变大、变慢、变脆。
3. 我此前"luna 自带严格"的判断得到支持，但我对臂 A"通过率过半"的预测是错的，对 psydef stripped 的估计也偏高。

局限：原生臂共 2 个 idea、6 个节点；judge 只测了 luna；每格 3–5 次，噪声不小。

## 更正（2026-09-19 23:2x UTC，经用户质疑后）

上面"汇总"一节的结论说过头了，予以更正：

1. **离线复判回答的是另一个问题**（固定节点上判定的稳定性），我却用它推出"luna 的单节点通过率在原生与契约条件下没有明显差别，差别只在尝试成本与成活率"。样本很小（每格 15–24 票），更重要的是实跑过程不是独立同分布的抽样，这个推论不成立。
2. **原生回路是自适应收敛的，不是"小概率抽中"。** 读两个原生臂的 draft 计划可见：
   - 臂 A：draft 1 被判"`embedding(a)+embedding(b)` 可交换"；draft 2 的计划写明"order-sensitive concatenation-based encoder, avoiding the earlier commutativity failure"，又被判"正则项只是 MSE(z, raw)"；draft 3 的计划改为"alignment penalty between the full-pair representation …" → 通过。
   - 臂 B：draft 1 被判"把特征置 0，不是合理的反事实"；draft 3 的计划改为"sign-flipping selected symmetric features, which is plausible under the synthetic data-generating process" → 通过。
   两发都是 败、败、过。judge 的意见经 Memory 摘要进入下一个 draft 并被采纳。
3. **我自己的旧数据也与"通过率相同"矛盾**：ARC 有 8 发 luna 运行、每发 12–20 个节点、零通过；若单节点通过率真有 13–27%，这几乎不可能。实跑差距很大：原生 2/2 发在 3 个 draft 内收敛，契约条件下是成片的零。
4. **契约条件下同一回路没有收敛的迹象**：TDC 073215 的 13 个 draft 计划里，几乎没有一个提到此前的失败（唯一一处是 debug 节点修崩溃）；Memory 在两种条件下都按同一代码路径每步生成。也就是说反馈送到了，但没有被采纳或无法被采纳。可能的原因（假设，未证实）：每个契约 draft 是 400–600 行的整项研究，计划的 7–10 句被交付物占满；意见又多又杂（崩溃 + 方法学），再经一次有损摘要；部分意见在构造上无法满足（psydef：契约要求在评估集上选择，idea 却承诺不这样做）；psydef 的上游搜索配置（1 个 draft、debug 概率 1.0）让绝大多数节点走 debug 路径，而 debug prompt 既收不到 Memory 也收不到 judge 的分析，反馈回路被配置切断。
5. 因此更准确的表述是：luna 单次判定确实严（原生 3 个 draft 也被它以方法学理由否掉 2 个），但在原生流水线里这种严格是**有产出的**，它在 3 步内把 draft 引到通过；我们改造后的流水线与框架的**反馈回路**发生了冲突。用户"是我们改造的 pipeline 造成了冲突、差距比表面大"的判断，比我此前"只是成本与成活率"的说法更符合证据。

局限：原生只有 2 发；"计划是否提及此前失败"是粗糙的文本启发式；Memory 摘要与 draft prompt 的原文没有被日志记录，我没有看到。

## 臂 B 重复两次（用户 2026-09-19 要求；只看实跑，不做离线复判）

做法与第一发完全相同：上游主题文件 → luna 原生 ideation（`--max-num-generations 2 --num-reflections 5`，每发重新做 ideation）→ 取第 0 个 idea 跑 stage 1 → stage 1 结束或满 2 小时由外部看护停容器。两发顺序执行。

事前预测（跑之前写下）：两发都会在 6 个 draft 以内原生通过 stage 1。需要区分的两种情形：
- "轻松通过"：第 1 个 draft 就过，或通过与此前的 judge 意见无关；
- "反馈收敛"：先被判 buggy，后续 draft 的计划明确回应 judge 的意见，随后通过（第一发和臂 A 都是这种）。
若任一发在 20 步内耗尽仍未通过，则"原生条件下稳定通过"的说法不成立。

### 臂 B 三发汇总（2026-09-19 23:47 UTC 完成；只看实跑）

| 发 | idea（luna 原生生成） | stage 1 结果 | 节点 | 用时（含 ideation） |
|---|---|---|---|---|
| 1（225150） | Shadow Counterfactuals… | 通过，第 3 个节点 | 3 跑完 / 0 崩溃 | 7 分钟 |
| 2（231551） | Probe Before Labels… | 通过，第 **10** 个节点 | 8 跑完 / 2 崩溃（KeyError；代码围栏 SyntaxError） | 24 分钟 |
| 3（234021） | Do Synthetic Stress Tests Predict Real-World Failure? | 通过，第 2 个节点 | 2 跑完 / 0 崩溃 | 6 分钟 |

加上臂 A（第 3 个节点通过，4 分钟）：原生条件下 **4/4 发都在 20 步内原生通过 stage 1**，通过位置为第 3、3、10、2 个节点。节点始终便宜：每个 4–10 秒、250–370 行、合成数据、不占 GPU；一步约 2 分钟，几乎全是 LLM 调用时间。

事前预测对照：
- "两发都在 6 个 draft 以内通过"：第 3 发成立（第 2 个节点），**第 2 发不成立**（第 10 个节点，7 个 draft + 3 个 debug）。
- 两种情形的区分：第 2 发是明显的"反馈收敛"——节点 4、8、10 的计划以 "The main correction is… / The main fix is…" 开头，逐条回应 judge 此前关于"未来失败标签"构造的意见，第 10 个才满足；第 1 发与臂 A 同属此类。第 3 发是第 2 个节点就过，节点 2 的计划没有明显回应节点 1 的意见，更接近"轻松通过"。
- 没有任何一发在 20 步内耗尽。

结论（截至目前）：
1. 原生流水线 + luna：stage 1 稳定能过（4/4），但并非总是轻松——luna 在原生条件下同样以方法学理由否掉大多数跑完的节点（4 发共 16 个跑完的节点，12 个被判 buggy），通过靠的是"便宜的节点 + judge 意见经 Memory 回流 + 足够的步数"。难的 idea 需要 10 步。
2. 契约条件下同样的 20 步预算换来的是 0 通过（TDC 0/15、babylm 0/7、ARC 多发 0/12–0/20），差距是真实且很大的，用户的判断成立。
3. 原生 4 发共 18 个节点只有 2 个崩溃（11%）；TDC 073215 是 7/15（47%）、babylm 2/7、外加两个被超时吞掉的 draft。崩溃节点既不产生可用的方法学反馈，也占用步数。

## 消融梯子（用户 2026-09-20 批准：按档顺序跑，失败的档再细分；每档 3 发）

固定：psydef 数据、luna 全角色、只跑 stage 1（外部看护停）、上游默认搜索配置（worker 数 1）、日志补丁全程开启（落盘 Memory 摘要与完整 draft prompt，不改行为）。工具：scratchpad `tier/{launch_tier.sh,tier_build.py,tier_apply.py,watch_tier.sh,summarize_tier.py}`；每发运行目录保存 `tier.json`（本档开关、逐字文本、来源 wrapper 的 sha256）与脚本快照。离线验证（无网络容器）：四档均可应用、可编译；原生指南保留；第 2/3 档追加行到位；第 1 档起 ideation 契约段到位；第 4 档 manager 闸门与搜索配置到位；日志补丁在桩 query 下正确落盘且返回值不变。

| 档 | 累加的改动 |
|---|---|
| 0 | 原生基线（已有臂 B 三发 + 臂 A：4/4 通过，通过节点 3、3、10、2） |
| 1 | 输入通道：psydef 任务说明文件（由正式生成器产出）+ ideation 契约段（逐字取自 psydef wrapper） |
| 2 | + 真实数据/split/scorer 只读挂载 + 指南追加 8 条任务事实与依赖约束（追加，不替换原生指南） |
| 3 | + 指南追加 6 条整项研究与交付物要求 |
| 4 | + 上游 psydef wrapper 的控制流：stage-1 完成闸门、stage 停止、多种子跳过，及其搜索配置（1 draft、debug 1.0、8 步、900 s） |

事前预测（第 1 档，跑之前写下）：3 发中至少 2 发在 20 步内通过；若第 1 档就成片失败，则"输入通道本身"即为不兼容点。
- 偏离记录：开跑前物理 GPU 5 已被其他租户占用（17.6 GB、99% 利用率），梯子改为**不挂 GPU、CPU-only**（psydef 为 sklearn 任务；臂 B 的原生玩具节点在有卡时 GPU 利用率也为 0%）。第 0 档基线是在 GPU 5 可见的情况下跑的，这是两者之间的一个小差异。

### 第 1 档第 1 发（`control_tier1_rep1_psydef02_luna_20260920_140632`）：设计缺陷，作废

19 分钟、9 个节点、0 通过。跑完的 6 个节点被判的理由全部相同："没有使用 PsyDefDetect 数据，找不到兼容数据集，回退到合成数据，因此不是对所述研究的有效评估"。原因是我的分档定义有漏洞：我们的任务说明文件本身就指向固定数据集，而第 1 档按原定义不挂载数据，idea 于是在构造上不可满足，失败与"输入通道"无关。已由操作者停止，运行目录保留。

**修正后的分档**：数据/split/scorer 的只读挂载随输入通道一起从第 1 档开始（任务说明文件指向它们）；第 2 档保持为"指南里追加数据与 scorer 的事实"。这样第 1 档检验的是"要求只从 idea 接口进入、coder 未被告知任何数据事实"，第 2 档检验的是"再把事实告诉 coder"。第 1 档从头重跑 3 发，预测不变。

### 第 1 档结果（修正定义后 3 发，2026-09-20 14:27–16:3x UTC，CPU-only）

| 发 | 结果 | 通过节点 | 节点数 | 崩溃率 | 通过节点用真实数据 + scorer？ | 备注 |
|---|---|---|---|---|---|---|
| 1（142722） | 通过 | 第 4 个（debug 节点） | 4 | 25% | **否**（"No DATA_PATH supplied; using deterministic synthetic data"） | judge 对节点 2 因合成回退判 buggy，对节点 4 同样回退却放行 |
| 2（143552） | 通过 | 第 16 个 | 16 | 43% | **否** | 计划回应了 judge 关于逐 epoch 选 checkpoint 的意见，但收敛在合成数据上 |
| 3（152245） | **20 步耗尽未通过** | — | 20 | 40% | — | 12 个跑完节点几乎全被判"合成数据，不是对 PsyDefDetect 的有效评估"；终端出现 `Data source: synthetic_smoke_test` |

三发共 40 个节点，**没有一个节点读过 PsyDefConv/split，也没有一个调过官方 scorer**。崩溃 18/40（45%，原生 4 发为 11%），其中代码围栏解析 bug 6 次、`SGDClassifier.partial_fit(class_weight='balanced')` 4 次。draft prompt 平均 2.6–2.7 万字符，Memory 摘要随步数增长到 2 万字符。

对照预测："3 发中至少 2 发在 20 步内通过"按字面成立（2/3），但两次通过都是空心的。第 1 档的结论：**只把要求送进 idea 接口，框架不会去做我们要的实验**。coder 只看到"固定的 PsyDefDetect 划分"几个字，没有路径、格式、scorer；原生 draft prompt 又明文要求"必要时自行创建合成数据"，于是全部节点走了合成替身；judge 多数时候识别并判掉，偶尔放行。这不是"过不过"的问题，而是"做的不是我们要的实验"。

下一步（待用户决定）：第 2 档拆为 2a（指南追加数据/scorer 事实，即正式 wrapper 的做法）与 2b（不动指南，改用框架原生的 `--load_code` "Code To Use" 通道挂一段 host 写的数据加载 + scorer 调用参考代码，不含任何方法内容），各 3 发对比。

### 第 2 档：两臂（用户 2026-09-20 批准）

- **2a**（正式 wrapper 的路线）：我们的说明书式主题文件 + ideation 契约段 + 数据挂载 + 原生指南末尾追加 8 条数据/依赖/scorer 事实。
- **2b**（接近原生的路线）：主题体的主题文件 `psydefdetect_native.md`（征稿说明风格：研究问题、语料作为资源、官方指标、一句话的计算设定与"两到四种方法对比"的惯例；无路径、无交付物、无契约段）+ 数据挂载 + 框架原生的 `--load_code` 通道挂 host 写的参考代码 `psydefdetect_native.py`（读语料、按 split 切分、按官方格式写预测、调官方 scorer；不含特征、模型、实验顺序）；指南保持原生，ideation 系统 prompt 不动。
- 事实核对：我们四个 02 wrapper 以及维护者的上游原版都**没有**使用 `--load_code`；"Code To Use" 通道在正式流水线里从未用过。
- 工具与输入文件的快照存于 `debug/dawei/ladder/`。

事前预测（跑之前写下）：
- 2a：3 发中至少 2 发通过；通过节点真正读取 PsyDefConv 并调用 scorer；崩溃率仍高于原生（契约段把 coder 推向同一类实现）。
- 2b：3 发中至少 2 发通过；通过节点真正读取数据并调用 scorer；通过节点序号与崩溃率比 2a 更接近原生四发（第 2、3、3、10 个；11%）。
- 若 2b 明显好于 2a，则"主题进 idea 接口、数据事实走 Code To Use"是与 02 兼容的输入方式；若两臂相近，则输入形式不是主因，问题在更下游（第 3、4 档）。

### 待一起分析的假设（2026-09-20，用户要求先记录）

**"缺少参考代码通道"可能是接入不兼容里最具体的一项。** 框架对 coder 取数据只设想了三条路：HuggingFace 下载、`--load_code` 挂上的 "Code To Use"、自行合成（draft prompt 明文"必要时自行创建合成数据"）。我们的沙箱断网，四个正式 wrapper 与上游原版都不挂 Code To Use，于是只剩"合成"一条路——第 1 档 40/40 节点走合成替身可由此完整解释。正式 wrapper 用散文事实替代（路径、schema、scorer CLI），能走通但有损：预测行键名、对话轮次结构、TDC 交付事实都曾因"没写到"而失败；第 1 档 45% 的崩溃中相当部分是数据管道与 API 误用。stage 1 目标明文"给了 Code To Use 可直接以它为起点"，挂代码让 coder 回到框架自己的工作流（从给定代码起步做原型），条文清单则不是。
它解释不了的：judge 的方法学判定（原生 16 个跑完节点仍 12 个被判，靠便宜节点 + 反馈回流收敛）、交付物（trace/报告，第 3 档）、流程承诺进 idea（主题文件问题；2b 同时改了主题文件与通道，若 2b 优于 2a 需再拆一个只换其一的对照）。潜在副作用：Code To Use 进入 judge 视野，judge 可能核对"是否按给定代码来"。
检验：2a 对 2b 的通过节点序号、崩溃率、通过节点是否真用数据与 scorer。

### 第 2 档结果（2026-09-20 16:48–18:5x UTC，两臂并行，CPU-only）

**2a（说明书式输入 + 指南 8 条事实）**

| 发 | 结果 | 通过节点 | 节点数 | 崩溃率 | 通过节点用真实数据 + scorer？ |
|---|---|---|---|---|---|
| 1（164806） | 20 步耗尽未通过 | — | 20 | 25% | —（4 个节点官方分 NaN：scorer 输出键名 `psydefdetect_score` 不在第 2 档事实中，是分档切法的缺口） |
| 2（174644） | 通过 | 第 7 个 | 7 | 43% | **是**，官方分 0.203；计划明确回应此前"泄漏/评估集选择"的判定 |
| 3（180758） | 通过 | 第 15 个 | 15 | 46% | **是** |

三发 42 个节点全部读真实数据、调 scorer：把事实写进 coder 指南后，替身实验消失。两次通过都是"败、败、过"式反馈收敛，但慢（第 7、15 个，原生为第 2、3、3、10 个），崩溃率 25–46%（原生 11%；代码围栏解析 bug 与 `SGDClassifier` 用法错误反复出现）。跑完节点的判定几乎全为方法学（评估集选择、实现与 idea 设计不符、上下文构造）。

**2b（主题体输入 + `--load_code` 参考代码）**：第 1 发跑 1 小时仅到第 4/20 步，0 通过；节点很重（19 分钟、11 分钟），2 个代码围栏崩溃；第 1 个节点只用了参考代码里的 `official_score`，其余自写。用户决定取消 2b（第 1 发在第 4 步停止，第 2、3 发未跑）。初步判断：2b 未显示优势，主题体的 idea 更有野心、原型更大。

**决定**：第 3、4 档不做。理由：它们测的是在"单节点装整项研究"的设计上再加什么，而现有证据（stage 目标原文、原生四发、8 月 ARC 合成数据时代的通过、第 1 档与第 2 档）指向这个设计本身与框架的阶段划分冲突：框架的 stage 1 按设计是玩具数据上的最小原型，真实数据属于 stage 2、3。下一步改测"分阶段注入"臂。

## 分阶段注入臂（设计与离线验证，2026-09-20；等用户批准后跑）

假设（用户提出，与论文 stage 设计一致）：框架的 stage 1 按设计是玩具数据上的最小原型，真实数据属于 stage 2、3；我们的 wrapper 把整项研究塞进 stage 1 并截断，才是与框架阶段划分的根本冲突。相应的 meta 流程应为：ideation 拿到开放主题；数据与接口在合适的阶段通过框架自己的槽位注入；实验以后续阶段的节点为单位；交付由结束时导出。

本臂的具体做法（psydef，luna 全角色，CPU-only）：
- ideation：主题体主题文件 `psydefdetect_native.md`，原生系统 prompt。
- 数据：host 参考代码 `psydefdetect_native.py` 放在 workspace 根目录作 `hf_dataset_reference.py`，用框架自带的 `--add_dataset_ref` 槽位进入 task_desc 的 "Code To Use"（所有阶段可见；不再同时用 `--load_code`，避免重复）。
- 阶段：放开 stage 1–3，stage 4 仅 2 步；`num_seeds=1`（README：等于 num_workers）；不做 stage 停止、不改指南、不改阶段目标、不改 judge。
- 停止：stage 3 结束或 stage 4 出现，或 4 小时上限。
- 记录：每阶段的节点数、通过、崩溃、读真实数据/调 scorer 的节点数、输出含 synthetic 的节点数、执行总时长；prompt 日志全程开启。

离线验证（无网络容器）：指南未追加、ideation 契约段不存在、manager 闸门不存在、日志补丁在、stage 上限 20/6/6/2、num_seeds 1、num_workers 1、单节点 3600 s、`hf_dataset_reference.py` 与主题文件就位、数据链接就位、全部文件可编译。

事前预测（跑之前写下）：
1. stage 1 会在少数节点内通过；通过节点是否用真实数据不作要求（有 Code To Use 在手，预计部分节点会直接用）。
2. **关键问题**：stage 2、3 的节点是否读真实数据并产出官方分。预测：多数会，因为参考代码就在任务描述里且 stage 2 目标要求"引入新数据集"；但存在 coder 尝试 HuggingFace 下载而崩溃的风险。
3. 若 stage 2、3 多数节点在真实数据上产出官方分，则"分阶段注入"成立，下一步转向结束时的导出与契约层的"实验 = 节点"定义；若后续阶段仍以合成数据为主，则数据参考槽位不足以把后续阶段拉回真实任务。

### 分阶段注入臂 第 1 发结果（`control_staged_rep1_psydef02_luna_20260920_190806`，19:08–20:45 UTC，97 分钟，CPU-only）

| 阶段 | 节点 | 跑完 | 崩溃 | 通过 | 真实数据 + scorer | 合成数据 | 备注 |
|---|---|---|---|---|---|---|---|
| stage 1 | 10 | 7 | 3 | 第 9 个 | 10/10 | 0 | 被判理由：3 次"未实现 idea 所述反事实训练"、泄漏、索引错误；崩溃：`partial_fit`、目标轮次定位 ×2 |
| stage 2 | 7 | 6 | 1 | 1（带入的最佳节点） | 7/7 | 0 | 6 个被判，主因"未引入两个 HuggingFace 数据集"；节点 4 真的下载了 `dair-ai/emotion`（镜像），`empathetic_dialogues` 脚本不受支持；按 6 步上限结束 |
| stage 3 | 6 | 2 | 4 | 1（带入的最佳节点） | 6/6 | 0 | **3 个崩溃是代码围栏解析 bug**，1 个崩溃是 HF `daily_dialog` 旧脚本；唯一跑完的节点因"三个 HF 数据集全部 HfUriError"被判；idea 的 Experiment Plan 已注入但没有一个节点真正执行它 |

带入的最佳节点（stage 1 第 9 个）本身就在一个程序里跑了多个配置并各自调用官方 scorer（输出中有 0.1210 / 0.1280 / 0.1657 / 0.1522 等官方分）。

对照事前预测：
1. "stage 1 在少数节点内通过"：第 9 个，勉强；重要的是 10/10 节点都在真实数据上，零合成。
2. "stage 2、3 节点读真实数据并产出官方分"：**成立**，13/13 节点真实数据 + scorer；数据参考槽位足以让后续阶段留在真实任务上。
3. 但 stage 3 没有执行 idea 的研究议程：两个障碍占满了 6 步——(a) 代码围栏解析 bug（3/6）；(b) stage 2、3 目标硬编码的 HuggingFace 数据集要求（judge 据此判节点，coder 据此去下载并崩溃）。在正式的断网沙箱里 (b) 会更彻底。

结论：分阶段注入解决了"做真实实验"与"数据管道崩溃"，stage 1 的"idea 太重"问题仍在（前 8 个节点），stage 2、3 则暴露出与阶段目标文本的硬冲突和解析器 bug。下一步的候选：修解析器对纯代码回复的回退（基础设施，非认知）；stage 目标里的 HF 条款如何处置（红线，需团队决定）；idea 的野心（主题文件是否该说明 stage 1 只需可行性原型）。

## 端到端（用户 2026-09-20 批准："倾向做的都做，然后运行"）

新增并离线验证的部件（快照在 `debug/dawei/ladder/staged/`）：
- **参考代码 v2**（`psydefdetect_native_v2.py`，作 `hf_dataset_reference.py`）：官方评估只经 `official_score(name, id_to_label)`，固定写 `working/<name>.predictions.jsonl` 与 `working/<name>.official_score.json`，打印 `official psydefdetect_score (<name>): <value>`。贴合原生指南的 `working_dir` 约定，也给 evaluator 固定位置。真实数据上验证通过。
- **确定性组装**（`assemble_psydef.py`，host 侧，无 LLM）：实验 = 各阶段的 `best_solution_<node>.py`（框架自己每阶段的选择，2–4 个）；在干净离线容器复现每个，收集官方分；选择 = 最后阶段的 best_solution；搬运其预测到根目录并由 host 重跑 scorer 写 `score.json`；trace 只填事实；报告由 journal 事实与框架原生阶段摘要（若有）渲染。在上一发原生产物上离线验证：stage 1/3 复现官方分 0.15215 与运行时逐位一致，stage 2 的 best_solution 因用 v1 参考代码把产物写进临时目录而无分（v2 约定即为此而设）；host 重算一致。
- **host 校验器**：从正式 psydef runner 逐行抽出的校验块，对组装产物 **通过**（research_idea.json 由 idea 映射并早于 trace）。
- **契约措辞草案**：`contract_wording_draft.md`（实验/选择/提升/输出位置/预算/报告六处）。
- 决定不做的：不修代码围栏解析回退；不动 stage 目标里的 HF 条款；不把预测另存为 npy；不占用 writeup 槽位。

端到端一发的流程：主题体 ideation → research_idea.json（BFTS 前）→ stage 1–4（20/6/6/2，种子 1，原生 generate_report）→ 容器退出 → host 组装 → host 校验。4 小时上限。事前预测：stage 1 通过；stage 2–4 留在真实数据；组装得到 ≥2 个带官方分的实验；host 校验通过。风险：stage 2/3 的 HF 条款与围栏 bug 消耗步数；stage 4 消融节点可能不产出官方分（则实验数为 2–3）。

### 端到端对照臂 SPEC（用户 2026-09-20 要求并行发）

用户的担心：最初的 meta prompt（说明书式主题文件）可能不必改，需要改的只是"按阶段注入数据与交付"。核查：8 月 26 日–9 月 14 日跑到 stage 2–4 的 9 发 ARC 运行，**所有阶段的通过节点无一读过真实数据**（每发 0–3 个尝试者全被判 buggy/崩溃）；3 发的 `estimator.py` 来自退出后的 exit-delivery-check 回填。9 月 13–14 日的 A' 补丁曾以散文在 stage 2+ 注入真实数据要求（034336 及其重放），后续阶段仍无真实数据的通过节点。结论：早期"能过"是全程替身；散文式按阶段注入不够；主题体是否必要**未被证明**（支持它的只有离线实验二的部分效应，2b 单发无优势）。

对照设计：与主题体端到端（run 213932）完全相同的流程，只把主题文件换回正式的说明书式 `psydefdetect_topic.md` 并加正式的 ideation 契约段（run `control_e2espec_rep1_psydef02_luna_20260920_215346`，并行）。指南保持原生、数据走参考代码 v2 槽位、阶段 20/6/6/2、host 组装与校验相同。

判定规则（跑之前写下）：两发都通过 stage 1、后续阶段留在真实数据、组装与校验都通过 → 保留正式 meta prompt，撤回主题体改动，只采纳数据通道与组装；说明书式一发失败而主题体成功 → 主题体改动有依据；附带比较两发 judge 判定中"与 idea 承诺不符"的比例。

## ARC 端到端（主题体路线；用户 2026-09-20 逐条确认：定义写进主题、参考代码只含数据/验证/打包、GPU 5、whest 官方打分、4 小时、实验 = 各阶段 best_solution）

- 主题文件 `arc_wbe_2026_native.md`（challenge 说明体）：目标量定义（x~N(0,I)，x_{l+1}=max(x_l@W_l,0)，每层每神经元的平均激活，(32,256)）、官方分（末层 MSE × max(0.1, C/B)，B=2.72e11，越低越好，隐藏 MLP 上打分）、资源（约 100 条带真值的记录）、接口（`Estimator.predict(mlp)`，自包含、仅 numpy + 标准库、参数嵌入文件）、一句话计算设定与"两到四种方法对比"惯例。
- 参考代码 `arc_reference_v1.py`（作 `hf_dataset_reference.py`）：`load_records`（100 条，float32 权重约 0.9 GB，加载约 73 s）、`split_records`（末 20 条为验证）、`make_mlp`、`ground_truth`、`local_validation(name, estimator_path)`：在只含该估计器文件的临时目录里用子进程验证（强制自包含），写 `working/<name>.estimator.py` 与 `working/<name>.validation.json`（末层/全层 MSE、耗时），打印固定行。**不含**前向模拟或任何估计方法。真实数据上验证通过（平凡估计器末层 MSE 0.804）。
- 组装 `assemble_arc.py`：实验 = 各阶段 best_solution，复现（GPU 5）后取 `working/*.validation.json` 中末层 MSE 最低的配置，最后阶段的估计器提升为 `estimator.py`，写 `submission.json`（仅来源与本地验证数值）、trace（仅事实）、报告；`score.json` 随后由 host 用 whest 官方 adapter 生成。
- 事实：ARC runner 默认的 whest 路径 `/tmp/whest-starterkit` 已不存在，可用的是 `/data/daweiwang/claude-home/whest-starterkit/.venv`；02 此前从未走到 host 打分；官方打分通道用平凡的权重相关估计器预检通过（score 0.0661，`official_adapter_whest_run`，98 s）。
- 事实：docker 守护进程看不到 `/root/researchclaweval-public` 路径（挂进去是空目录），数据必须用 `/data/daweiwang/claude-home/...` 路径挂载。
- 校验器从 ARC runner 第 437–493 行逐行抽出。契约措辞草案：`ladder/staged/arc/contract_wording_draft_arc.md`。

### 端到端 主题体臂 结果（`control_e2e_rep1_psydef02_luna_20260920_213932`，21:39–22:4x UTC，约 65 分钟）

| 阶段 | 节点 | 崩溃 | 通过 | 真实数据 + scorer |
|---|---|---|---|---|
| 1 | 2 | 0 | 第 1 个（2/2） | 2/2 |
| 2 | 7 | 1 | 带入节点 | 7/7 |
| 3 | 7 | 4 | 带入节点 | 7/7 |
| 4 | 3 | 1 | 带入节点 | 3/3 |

- 组装：4 个阶段的 best_solution 全部复现成功（29 s / 119 s / 151 s / 23 s），每个节点内部都比较了多个配置并各自调官方 scorer（如 stage 1：sgd_no_context 0.1203、sgd_real_context 0.0880、sgd_shuffled_context 0.0937；stage 3：real_model_* 0.087–0.105）。
- 选择 = stage 4 的 best_solution（与 stage 1 同一节点），最佳配置 sgd_no_context，官方分 **0.1203**；host 重算逐位一致。
- **host 校验通过**（从正式 runner 逐行抽出的校验块），状态 finished（assembly 0、validation 0）。
- 原生退出码 143：BFTS 结束后框架自己的孤儿进程清理向匹配关键词的进程发 SIGTERM，把自己也杀了（上游 bug；ARC wrapper 里早有 `_arc_self_pids` 修复，此诊断未打）。不影响组装。
- 更正（2026-09-20 晚）：`best_solution_<node>.py` 由上游 `get_best_node(only_good=False)` 写出，是框架在该阶段**全部节点**（含它自己判为 buggy 的）里选的；带入下一阶段的节点则只在通过节点里选。本次 stage 2（048fa074）和 stage 3（4ea34bb1）的 best_solution 都是 buggy 节点；stage 1 与 stage 4 的 best_solution 是同一个通过节点 8d3cb8ad（3 份不同代码）。通过节点只有 stage 1 的 2 个，stage 2/3/4 的新节点无一通过。
- 口径决定（用户）：契约的"2–4 个实验"按框架各阶段选出的方案计数，不要求非 buggy；组装脚本不改。最终产物（stage 4 best_solution = 8d3cb8ad）在两种原生口径下一致，host 转换、官方打分 0.1203、校验通过，这三步成立。
- 这是 **02 第一次在真实数据上以框架自己的四阶段流程 + 确定性组装通过 host 校验并得到官方分**。分数本身低（0.12），与 psydef 早先 stage-1-only 的 0.13–0.14 同量级。

### 端到端 规格体臂 结果（`control_e2espec_rep1_psydef02_luna_20260920_215346`，21:53–23:2x UTC，约 90 分钟）

输入 = 正式 psydef 规格 topic + ideation 契约（生产口径），其余与主题体臂完全相同（loader v2 走 dataset-reference 槽、阶段 20/6/6/2、host 确定性组装 + 校验）。

| 阶段 | 节点 | 崩溃 | 新通过 | 真实数据 + scorer | best_solution 判定 |
|---|---|---|---|---|---|
| 1 | 11 | 4（2 个围栏） | 1（第 10 个） | 11/11 | buggy（454538f1，目标轮定位/泄漏） |
| 2 | 7 | 0 | 2 | 7/7 | buggy（9f6fd878，额外内部切分） |
| 3 | 7 | 2 | 0 | 7/7 | **崩溃节点**（1aa1518c，ValueError），复现 rc=1 无分数 |
| 4 | 3 | 1 | 0 | 3/3 | 通过节点（ba73ebcf，stage 2 带入） |

- 组装：4 个 best_solution 中 3 个复现出官方分（0.1409 / 0.1445 / — / 0.1445）；选择 = stage 4 的 ba73ebcf，配置 routed_svm，官方分 **0.1445**，host 重算一致；**host 校验通过**（assembly 0、validation 0）；原生退出码 143 同主题臂（上游自杀式清理）。
- 规格体特有现象：规格里"生成的程序自己必须写出 /workspace/predictions.jsonl、score.json、experiment_trace.json、final_report.md"让 stage 3 的 5 个节点都往根目录写这套文件、互相覆盖；最后留下的版本（routed_linear_margin，官方分 0.1537，host 重算一致）来自一个被 luna 判 buggy 的节点，已原样快照到 `native_root_handoff/`。luna 的 buggy 理由多为合规冲突：research_idea.json 后写、HF 数据集只冒烟、stage 3 的"三个 HF 数据集"与规格的"恰好两个实验"直接矛盾。
- 与主题体臂对比（各 1 发）：stage 1 通过所需节点 2 vs 11；两臂 stage 3/4 都没有新通过节点；两臂都完成组装、打分、校验。按预注册规则（两发都过 stage 1、后续阶段留在真实数据、组装与校验都过），**结论是保留正式 meta prompt，主题体不是必需**；主题体的优势只体现在 stage 1 收敛速度，单发不足以定量。规格体额外暴露的"节点自己写根目录契约文件"是与 host 组装重叠的责任，需在契约里二选一。

### 端到端 ARC 主题体臂 结果（`control_e2earc_rep1_arc02_luna_20260920_223702`，22:37–23:21 UTC，GPU 5）

**失败于 stage 1**：20 次迭代用满，0 个通过节点（3 个崩溃、17 个跑通但被判 buggy）。随后上游 `overall_summarize` 因只有 1 个阶段而崩溃（ValueError: expected 4, got 1），原生退出 1；组装因只有 1 个阶段选择退出 3；官方打分与校验因缺产物退出 1。

- 20 个节点里 **19 个自己生成小随机 MLP**（如 8×32、12×…）做合成原型，只有 1 个（n15）用参考加载器读真实记录，但因 `np.erf` 在 NumPy 2.x 不存在而崩溃。psydef 上 loader 从第 1 个节点起就被用；ARC 上"随机初始化 MLP"这一任务定义本身让"自己造数据"成为最自然的 stage 1 原型，参考加载器通道没有被采用。
- luna 判 buggy 的理由高度集中：估计器没有可训练参数，但 02 原生 stage 1 实现指南要求逐 epoch 打印训练/验证损失，节点于是写了空转的 epoch 循环，被反复指为"假 epoch"；其次是"没有实现提供的 ARC 套件"（用合成小网络）、rank 选择用验证集或各 rank 结果相同、decay ratio 定义误导。
- 结论：主题体 + 参考加载器这条路在 ARC 上没有复现 psydef 的结果。ARC 暴露了两个 psydef 不会触发的冲突：(a) 02 原生"训练循环/epoch 指标"硬要求 vs 无训练的估计问题；(b) 任务定义里的"随机 MLP"使合成原型比真实记录更自然，stage 1 不会自发走向参考数据。两者都是框架认知/阶段目标层面的，按当前约束不改。

### TDC 主题体臂（设计与离线链路验证，2026-09-20 23:4x UTC）

与 psydef/ARC 同构:主题体 `tdc_admet_tox_native.md`(三端点毒性、scaffold split、macro AUROC、CPU/无 RDKit)+ 参考模块 `tdc_reference_v1.py`(仅 load_split / validation_score(官方验证 scorer, 写 working/<name>.validation_metrics.json) / test_predictions(写 working/<name>.test_predictions.csv))经 `--add_dataset_ref` 槽注入;阶段 20/6/6/2;CPU 4 核 16 GiB。host 组装 `assemble_tdc.py`:复现各阶段 best_solution(离线容器,无网),实验 = 每阶段 best_solution 中验证 macro AUROC 最高的配置;选择 = 验证 macro AUROC 最高的实验(契约规则,校验器强制);契约包(runs/<run_id>/{config,validation_predictions,metrics,train.log,runfile}、predictions.csv、environment.json、experiment_trace.json 含 claim 账本、paper.md 表格带 claim 标记、final_report.md、logs/)全部由事实渲染;score.json 由 host 隐藏标签 scorer 在 framework 阶段审计通过后写。隐藏标签从不进容器。
离线链路测试(两份玩具 best_solution,字符 n-gram + 逻辑回归):framework 审计 passed(2 实验、8 claims、8 个表格数值核对)、host 隐藏标签打分 main_score 0.7951、final 审计 passed。
已知张力:节点内部会给多个配置打验证分,契约要求 candidate_count=1;trace 每条实验只记该节点的最优配置,其余配置名如实记在 config.json 的 other_configurations_scored_by_this_node。

### TDC 主题体臂 rep 1（`control_e2etdc_rep1_tdc02_luna_20260920_234655`）：用户终止

- ideation 正常(2 个 idea,选 0:"Shared Causes, Private Liabilities: Factorized Multi-Task Toxicity Prediction Under Scaffold Shift");stage 1 第 1 个节点读真实 split、字符 n-gram TF-IDF + torch 共享因子/端点私有头多任务模型、30 epoch、自己调官方验证 scorer,文件命名与参考模块约定一致 —— 与 ARC 不同,这是训练形态,套得进 02。
- 但该节点跑了 26 分钟仍未结束:容器 `--cpus 4` 只限配额,`os.cpu_count()` 仍为 384,没有设线程环境变量,torch 开了 192 线程挤在 4 核配额里(线程超额调度)。正式 TDC runner 同样没设线程变量,9 月 18 日那批正式 TDC 02 运行带着同样的缺陷。
- 00:2x UTC 用户决定结束任务;按 pid 杀 launcher 与 timeout 包装,docker stop 自己的容器;目录保留,state.json 记为 stopped_by_user。未重发。
- 若重发:launcher 加 OMP/MKL/OPENBLAS/TORCH_NUM_THREADS=4(与配额一致),其余不变。

### psydef 规格臂 × deepseek-v4-flash / kimi-k2.6（2026-09-21 00:4x UTC 并行发出，各一发）

决定(用户):后续用规格臂(正式 meta prompt)跑,主题臂留作诊断。理由:两臂效果无差异;meta eval 测的是框架消化规格的能力,各框架同一输入;起作用的是分阶段路线而非臂;规格里"程序自己写根目录契约文件"一段的责任重叠另行决定,这一轮不改规格文本。
launcher `launch_e2e_spec_model.sh <rep> <tag> <provider_env>`:与 luna 规格臂完全相同的输入、阶段(20/6/6/2)、组装、校验,另加正式 psydef wrapper 的 ideation 补丁(标签归一化、MAX_NUM_TOKENS 16384、ideation 最多 3 次;luna 未触发,ds 此前全踩过)和线程上限(OMP/MKL/OPENBLAS/TORCH_NUM_THREADS=8,与 --cpus 8 一致)。provider env 复用最近的 ds / kimi 文件(同一 key 与 base URL,仅 OPENAI_MODEL 不同),发前各做了 1 token 连通检查。

#### 结果:两发都在 ideation 阶段失败,未进入 BFTS

- **deepseek-v4-flash**(`control_e2espec_rep1_psydef02_ds_20260921_163524`):ideation 第 1 次就存了 2 个 idea,但 idea 0 的 FinalizeIdea 参数多套了一层 `{"idea": {"idea": {...}}}`,存下来的是 `{"idea": {...}}`,没有 Name/Title 顶层键;idea 1 是合规的。上游 `launch_scientist_bfts.py` 直接取 `idea['Name']`,idea 0 会崩;我的 launcher 映射 research_idea.json 时先崩在同一处(KeyError 'Title')。是模型输出格式问题,不是我的映射独有。
- **kimi-k2.6**(`control_e2espec_rep1_psydef02_kimi_20260921_163544`):3 次 ideation 全部 "Stored 0 ideas"。kimi 每次回复把多个 ACTION/ARGUMENTS 块批量写在一条里(几次 SearchSemanticScholar 后接 FinalizeIdea),上游正则 `ARGUMENTS:\s*(.*?)(?:$|\nTHOUGHT:|\n$)` 取到第一个 ARGUMENTS 之后的全部文本,json.loads 报 "Extra data",整个反思循环中止。3/3 系统性复现;上游 prompt 只写 "Respond in the following format: ACTION/ARGUMENTS",没有明说每条回复一个动作。
- 两者都是上游 ideation 对回复格式零容错(任一条不可解析即丢弃整轮)与这两个模型格式习惯的冲突,与 9 月 19 日 ds 系列 ideation 失败同类。luna 未触发。未做 host 修复,等待决定。

#### 决定(用户):加兼容解析器 → `real_eval/adapters/ai_scientist_v2/patch_ideation_tolerant_parser.py`

只改解析,不改 prompt、不改判官、不改任何决策:一条回复里的多个 ACTION/ARGUMENTS 块按模型写的顺序依次执行(同一回复的工具结果拼接后回填);JSON 之后的多余文字忽略;FinalizeIdea 多套的一层 `idea` 剥掉;仍然非法的 JSON 与上游一样丢弃整个提案。幂等,锚点找不到即报错;与标签归一化补丁任一顺序兼容。离线仿真 7 例通过(kimi 批量块、ds 嵌套、单动作 + 围栏 JSON + 结果回填、markdown 标签 + 批量、非法 JSON 仍中止、5 轮纯检索仍不存、空 idea 仍拒绝;`debug/dawei/ladder/staged/ideation_tolerant_parser_test.py`,在运行镜像内跑)。已接入 `launch_e2e_spec_model.sh`;正式 psydef wrapper 未接(待团队决定)。

### TDC 规格体臂 rep 2（用户决定:规格体 + CPU 上限 32）

`launch_e2e_tdc_spec.sh`:topic = 正式 `tdc_admet_tox_topic.md`(generate_tdc_admet_tox_native_inputs.py 生成,含"Native handoff"段),参考模块与分阶段路线、组装、审计、隐藏标签打分与主题体 launcher 完全相同;`--cpus 32` + OMP/MKL/OPENBLAS/TORCH_NUM_THREADS=32(主机 384 核、负载约 70);容器退出后先把框架自己写到根目录的契约文件快照到 `native_root_handoff/`(规格里要求程序自己写,和 psydef 规格臂同样会与 host 组装重叠),再组装。正式 wrapper 的 handoff guideline 事实与 stage-1 stop 不用(与 psydef 规格臂只取 ideation 段、不取指南事实一致;TDC 正式 wrapper 没有 ideation 注入段)。

#### rep 2 结果:deepseek-v4-flash 失败在 VLM 图表门,kimi 进入 stage 2

- **deepseek-v4-flash rep 2**(`control_e2espec_rep2_psydef02_ds_20260921_165225`):ideation 第 1 次成功(2 个 idea);stage 1 20 个节点全部真实数据 + 官方 scorer,**文本判官通过 7 个,第 1 个节点就通过**;但上游 `good_nodes` 要求 `is_buggy is False and is_buggy_plots is False`,VLM 图表门(`agent.vlm_feedback.model` 被适配层设为同一模型)对 5 个通过节点全部回复 "No plots were received"(is_buggy_plots=True),另 2 个为 None;stage 1 因此 20 次迭代耗尽、"Failed to find working implementation",随后上游 overall_summarize 崩溃(仅 1 阶段),原生退出 1,组装 3,校验 1。
- 直接验证:向 bianxie 的 deepseek-v4-flash 发一张 8×8 红色 PNG 问颜色,返回空内容;kimi-k2.6 同样请求返回 "Red."。即 **该端点的 deepseek-v4-flash 不处理图像**,而 02 的 stage-1 完成条件硬性要求 VLM 确认收到图表。这是 02 的视觉依赖与模型(或中转)能力的不兼容,与判官标准、输入方式无关;9 月 19 日 ds 系列 stage 1 不通过很可能同因(待核对)。
- **kimi-k2.6 rep 2**(`control_e2espec_rep2_psydef02_kimi_20260921_165245`):解析器起效(两条 5 动作块回复、8 处尾随文字),ideation 第 1 次成功;stage 1 通过 2 个节点(VLM 门 OK),已进入 stage 2。

### ARC 讨论结论与 rep 2 设计（2026-09-21）

苏格拉底式梳理(用户答复):(1) 三条指令冲突 = A 阶段目标"简单数据集/可造合成数据" vs B 实现指南"逐 epoch 训练指标" vs C 判官"忠于任务";(2) 读 stage 1–4 的 prompt 与切换代码:数据/接口的决定只在 stage 1 做一次,stage 2 "不许改架构"、stage 3 在带入代码上 improve(仅此时注入 idea 的 Experiment Plan)、stage 4 "同上一阶段数据集",四阶段内没有"切到真实数据"的动作 → 血统在 stage 1 钉死;用户据此撤回"玩具数据可通过"的判断,选 (a):stage 1 必须在真实数据与接口上通过,只通过输入侧实现;(3) 节点 plan 原话证实其把 stage 1 读成"先合成、正式套件留给后面"(18/20),并明知 epoch 是为满足 B 的空转(15/20);psydef 的加载器被用是因为官方指标只能经它得到,ARC 的真值节点可自造 → 真实记录无必要性;(4) 用户接受两类输入侧杠杆:(i) 参考模块形态,(ii) 主题里对"结果"的定义(不进契约,本轮只改主题)。

rep 2 只改两处:`arc_reference_v2.py`(`load_records()` 默认 20 条训练记录;`validation_records()` 固定 20 条留出;`local_validation(name, estimator)` 接受脚本内的对象/类或文件路径,进程内验证,不起子进程;把类源码连同其引用的顶层函数/赋值/import 打包成自足的 `working/<name>.estimator.py`,在临时目录以子进程、只允许 numpy + 标准库 import 自测,`validation.json` 记 `submittable`;docstring 陈述官方运行时事实:numpy-only、flopscope 数组、np.vectorize/object dtype/scipy 不可用)与 `arc_wbe_2026_native_v2.md`(把"可本地开发验证"改为"结果只定义在提供的记录上,自造网络上的数字不是本任务的结果")。`assemble_arc.py` 只加一行:跳过 `submittable: false` 的配置。阶段、判官、指南、模型、GPU 5、预算与 rep 1 相同。
离线验证:参考模块在运行镜像内测过对象/类/路径/不可打包依赖/scipy 依赖五种情形;完整链路(两份 numpy-only 的矩传播 best_solution → 组装 → whest 官方打分 9.98e-05 → host 校验)通过。发现并记入 docstring 的事实:whest 环境无 scipy;权重以 flopscope 数组传入,np.vectorize 会报 NotImplemented。
预注册判读:节点转向真实记录但仍因假 epoch 判 buggy → B 是剩余根因;转向真实记录且有节点通过 → 主因是 A/C 冲突 + 真实数据无必要性;仍不用真实记录 → (i)+(ii) 不够。
- rep 2(`control_e2earc_rep2_arc02_luna_20260921_182113`)发出 2 分钟后发现 GPU 5 被其他租户占用(16 GB、87% 利用率,host nvidia-smi 因 PID 命名空间看不到进程),按"GPU 忙则 CPU-only"的约定按 pid 停掉(目录保留,state=aborted_gpu_busy),以 **rep 3 CPU-only** 重发(`ARC_GPU=none`:不挂 GPU、CUDA_VISIBLE_DEVICES 置空;组装复现同样 CPU)。与 rep 1 的差别只多了"无 GPU":rep 1 的 20 个节点全是 numpy/秒级,GPU 未被实质使用。

#### deepseek-v4-flash rep 3:VLM 图表反馈步骤改用 gpt-5.6-luna(用户决定)

launcher 新增可选 `VLM_MODEL`:只覆盖 `agent.vlm_feedback.model`(图表门),ideation、代码、判官、汇总仍是 deepseek-v4-flash;tier.json 与 state.json 记录 `vlm_model_override`。这是混合模型条件,测评口径上要单独标注。rep 3 = `control_e2espec_rep3_psydef02_ds_*`。

#### TDC 规格体 rep 2 结果:端到端通过,隐藏标签 main_score 0.7949

- 原生:81 分钟,四阶段全部完成(退出 143 = 上游自杀式清理)。stage 1 17 个节点、7 个崩溃(3 个围栏)、第 16 个通过;stage 2 7 个节点仅带入节点通过;stage 3 7 个节点仅带入节点通过;stage 4 3 个节点 2 个通过。全部真实数据 + 官方验证 scorer;规格里"程序自己写根目录文件"这次没有触发(根目录无框架写的契约文件)。
- 组装第一次崩在我的 paper 渲染(idea 的 Risk Factors 字段是列表,`"\n".join` 报 TypeError);修复后在 host 重跑确定性步骤(组装 → framework 审计 → 隐藏标签打分 → final 审计),不触碰框架产物。
- 4 个实验 = 各阶段 best_solution 的最优配置(验证 macro AUROC:stage1 gated 0.7971、stage2 independent_bs64_lr0_01 0.8395、stage3 independent 0.8039、stage4 gated 0.8052);选择 = 验证最高的 stage 2(契约规则)。framework 审计 passed(4 实验、16 claims、16 个表格数值核对)、**隐藏标签 main_score 0.7949**(AMES 0.7776 / hERG 0.7642 / DILI 0.8430)、final 审计 passed。
- 对比:9 月 18 日正式 TDC 02×luna 的榜单分 0.6311(那批带 26 分钟/节点的线程超额缺陷,且是节点自己写根目录契约文件的路线)。
- 事实补充:四个阶段的 best_solution 都是框架判 buggy 的节点(选择在全部节点里做),各阶段的通过节点是 stage 1 第 16 个节点及其带入;按用户口径(实验不要求非 buggy)计入,trace 的 `framework_verdict_is_buggy` 字段如实记录。

#### ARC rep 3(CPU,v2)中途观察(40 分钟)

- **stage 1 第 3 个节点通过**(4 节点:1 崩溃、2 判 buggy、1 通过),**4/4 节点用参考模块读真实记录**(rep 1 为 1/20);stage 2 7 节点全部真实记录、估计器全部可提交,带入节点通过;stage 3 进行中。按预注册规则落在第二档:节点转向真实记录且有节点通过 → 主因是 A/C 冲突 + 真实数据无必要性,(i)+(ii) 足够。
- B(逐 epoch 训练指标)的表现:通过节点 n3 引入了一个"输入方差校准标量",用 3 轮坐标搜索选取,每轮记录训练/验证损失 —— 即节点用一个真实(虽小)的学习环节满足了 B,luna 接受;stage 2 里把网格搜索包装成 epoch/优化器的节点仍被判"epoch 无效"。B 是持续的压力(把方法推向"可校准"的形态),但不再是阻断。
- 参考模块边角:n1 自己先把估计器写到 `working/<name>.estimator.py` 再把该路径传给 local_validation,copy 到同一路径触发 SameFileError;已在 v2 中改为同路径跳过复制(rep 3 用的仍是发出时的副本)。

#### 结果:kimi rep 2 与 ARC rep 3 均端到端通过

- **kimi-k2.6 rep 2**(`control_e2espec_rep2_psydef02_kimi_20260921_165245`,约 2.5 小时):四阶段完成(stage 1 第 4 个节点通过;stage 2/3/4 各 2/3/3 个通过节点,是四个模型里后续阶段通过最多的);组装 4 个 best_solution 全部复现(stage 3/4 同一节点),选择 stage 4 的 combined_full,官方分 **0.1820**,host 重算一致,校验通过。事故:launcher 的 host 步骤在容器退出后因 bash 语法错误崩溃 —— 原因是我在 kimi 运行期间编辑了它正在执行的 `launch_e2e_spec_model.sh`(加 VLM 覆盖),违反了"运行中的脚本不改"的规则;host 步骤(组装、校验)手动重跑,不触碰框架产物,state 记录了此事。以后每次发射前把 launcher 复制到运行目录并从副本执行。
- **ARC rep 3**(`control_e2earc_rep3_arc02_luna_20260921_182346`,CPU,v2):四阶段完成;组装 4 个 best_solution 全部复现(stage 1/3/4 同一通过节点 diagonal_transport,stage 2 为 buggy 节点),选择 stage 4;**官方 whest 分 0.0988**(official_adapter_whest_run),host 校验通过。科学上很弱:本地留出集 final-layer MSE 1.13,与全零估计器的 1.11 相当,但这是框架自己在真实记录上做出并提交的结果 —— 这正是 (a) 口径下 02 × ARC 的真实测评数据。与 rep 1 对照:输入侧两处改动((i) 参考模块形态、(ii) 结果定义)把 stage 1 从 0/20 变为第 3 个节点通过,20 个节点 1 个用真实记录变为全部使用。

### 扩大规模(2026-09-21 20:1x UTC 起):ARC × ds/kimi、TDC × ds/kimi、BabyLM × luna

- **模型参数化 launcher**(`launch_e2e_arc_model.sh`、`launch_e2e_tdc_model.sh`,由 `gen_model_launchers.py` 从 luna 版机械生成):加正式 wrapper 的 ideation 补丁(标签归一化、兼容解析器、MAX_NUM_TOKENS 16384、重试 ×3)、可选 `VLM_MODEL`(ds 用 gpt-5.6-luna 做图表反馈,同 psydef 的决定)、线程上限。发射改为"复制 launcher 到 launch_copies/ 再执行",避免再犯"编辑运行中的脚本"。
- ARC ds/kimi:CPU-only(GPU 5 仍被占用),v2 参考模块 + v2 主题。TDC ds/kimi:规格体,32 核。四发并行发出。
- **BabyLM(新 topic,规格体做法)**:topic = 正式 `babylm_topic.md`(生成脚本;注意其"6 个域"列表与实际数据文件名不符,原样保留);参考模块 `babylm_reference_v1.py`:`load_corpus()`、`default_split()`(域内固定 10% 留出,种子 0,允许自定义但验证行不得用于拟合)、`word_count()`、`official_validation(name, total_nll_nats, validation_lines)` = exp(NLL / (词数 + 每行一个句尾)),按词归一化使不同分词可比;`save_submission()` 保留模型。组装复现各阶段 best_solution 于同一 GPU,选最低词级困惑度,提升 submission/、trace(含 validation_perplexity 与 best_validation_perplexity,供 run_babylm_score.py 读取)、报告;host 校验块从 babylm runner 逐行抽出。GPU 1(空闲);容器启动即核对只看到该卡的 UUID,否则退出 97。阶段 12/4/4/2(训练节点慢,单节点上限 3600 s),4 小时总预算。离线链路(两份 unigram best_solution)通过:组装、打分(2456 ppl)、校验。
- 发射后发现:机械生成的 ARC/TDC 模型 launcher 里 ideation 成功检查的引号写错(bash -lc 单引号串内又用了单引号),导致每次 ideation 明明存了 idea 也被判 EMPTY、白跑 3 次(多耗 2 次 ideation API);第 3 次后按 `test -s` 继续,4 发都正常进入 BFTS。已修(仅影响后续发射;本轮四发从副本执行,不受影响)。babylm launcher 手写,无此问题。另:kimi 偶有整条回复只有"我先去搜文献"的叙述、没有 ACTION 块,上游丢弃该提案,兼容解析器对此无能为力(不是解析问题,是没有动作)。BabyLM 正式 topic 把数据集路径写成 host 路径,容器内额外把数据与契约只读挂到同一 host 路径,避免纯路径问题导致失败(生产 runner 不这样做)。

#### BabyLM × luna rep 1(`control_e2ebabylm_rep1_babylm02_luna_20260921_202716`,GPU 1):stage 1 失败(12/12)

- 12 个节点:4 个崩溃(CUDA OOM、TypeError、KeyError、代码围栏),8 个跑通判 buggy。判词分两类:**A/C 冲突的 BabyLM 形态**(4 个):只取每域前 600 / 2500 行、自定义 20% 切分、甚至 500 行合成语料 —— "use a simple dataset" 在文本任务上变成子采样,luna 判"不是官方可比的词级困惑度";**实现 bug**(4 个):目标对齐错、NLL 只算活跃目标、稀有词阈值设定与数据不符等。7/12 用了参考模块的 official_validation,只有 2 个用了 default_split。
- 我把阶段迭代设为 12/4/4/2(其他 topic 是 20/6/6/2),stage 1 的搜索空间比别的 topic 小;这是我的设定,不是框架的。
- 对照 ARC 的教训:这里真实数据是文本,子采样零成本,"结果只定义在全量语料 + 参考切分上"这一条在正式 topic 里不存在,参考模块也没有把非官方验证集标出来。

#### BabyLM rep 2 设计(用户同意):验证集从节点手里拿走,训练集留给它;stage 迭代恢复 20/6/6/2

`babylm_reference_v2.py`:`official_validation(name, nll_fn)` —— 节点交出 `nll_fn(lines) -> 总 NLL(nats)`,参考模块自己在固定验证行(每域 10%,种子 0,33,583 行、975,273 词)上调用并按词归一化;`training_lines()` 是其余约 30 万行,用全量或子集都行;docstring 明说"结果只定义在固定验证行上,训练数据是你的选择"。与 psydef `official_score(name, id_to_label)` 同构:预测由节点做,评估集由参考模块钉死。正式 topic 不动。离线链路测试:子集训练(5000 行)与全量训练的 unigram 都在同一验证集上得到可比的困惑度(2619 vs 2455),组装、打分、校验通过。
契约层弱点(记录,不动):BabyLM 的打分只读 trace 里框架自报的困惑度,没有固定评估集与 host 重算,跨框架不可比;我们的组装至少复现 best_solution 并按参考模块定义重算。

#### BabyLM rep 2(`control_e2ebabylm_rep2_babylm02_luna_20260921_213017`):3 个节点后整条运行被 provider 的一次 400 打死

- 判官调用(parse_exec_result → backend_openai)在 worker 进程里收到 bianxie 的 400:"Function tools with reasoning_effort are not supported for gpt-5.6-luna in /v1/chat/completions… or set reasoning_effort to 'none'"(type rix_api_error)。我们的代码没有发 reasoning_effort(上游只对 o1 模型设),是 provider 某条路由对自己默认值的拒绝;直接探测:带 reasoning_effort=high 3/3 被拒,不带则通过,复现运行的请求形状也通过 —— 间歇、按路由。今天其他运行(含在跑的 5 个)0 次出现。
- 上游无 400 重试,且 APIStatusError 在 worker → 主进程的 pickle 中失败(缺 response/body),BrokenProcessPool,整条运行退出。
- 修复(基础设施层,`patch_ai_scientist_v2_common.py`):chat shim 对含 reasoning_effort 的拒绝按 provider 指示改 reasoning_effort='none' 重试;并把 backend_openai 的 `backoff_create(client.chat.completions.create, …)` 也路由过 shim(wrapper 的文本替换只覆盖 `client.chat.completions.create(` 调用点,这里传的是绑定方法,原本绕过了 shim)。假客户端离线测试通过。rep 3 重发。
- 另一个事实:3 个节点里 2 个按正式 topic 的域名列表(bnc_spoken, childes, gutenberg, open_subtitles, simple_wiki, switchboard)去找文件,实际文件是 aochildes/bnc_spoken/cbt/children_stories/gutenberg/open_subtitles/qed/simple_wikipedia/switchboard/wikipedia,找不到就"Real corpus unavailable"回退合成。正式 topic(以及各框架共用的 shared summary)的数据事实是错的,待用户决定是否修生成脚本。

#### 修复(用户决定,仅针对 02):BabyLM 02 topic 的域列表改为从数据目录实际读取

`generate_babylm_native_inputs.py` 的 `render_ai_scientist_topic` 不再硬编码 "6 text domains: bnc_spoken, childes, gutenberg, open_subtitles, simple_wiki, switchboard",改为生成时 glob 数据根目录下的 `*.train.txt`(现为 10 个:aochildes, bnc_spoken, cbt, children_stories, gutenberg, open_subtitles, qed, simple_wikipedia, switchboard, wikipedia);目录不可读时改为提示"列目录"。原因:02 的 BFTS 节点按 topic 文本拼文件路径、不列目录,错名字直接导致回退合成;01 的输入里没有这份列表且其 agent 会自己列目录,所以 01 不受影响。shared summary(其他框架的 brief)与契约里的"6 个文件"未改,待团队定。rep 3 发在修复之前,仍用旧 topic;从 rep 4 起生效。

#### TDC × deepseek-v4-flash rep 1(`control_e2etdcspec_rep1_tdc02_ds_20260921_201847`,VLM 用 luna):四阶段完成,组装失败 —— 节点从未产出测试集预测

- 原生 75 分钟四阶段全部完成(stage 1 第 1 个节点通过;stage 2/3/4 各 5/2/2 个通过),全部真实数据 + 官方验证 scorer,VLM 门正常。
- 组装:4 个 best_solution 全部复现成功、每个节点都给多个配置打了验证分(最高 0.79 左右),但**没有一个配置调用参考模块的 `test_predictions()`**,working 目录里只有 validation_predictions/metrics;规格要求的根目录 predictions.csv 节点自己也没写。契约的交付物(测试集概率)不存在,组装退出 4,framework 审计/打分/final 审计未执行。host 不能替框架生成预测,记为失败:**DS 只做了验证评估,没有做交付**。luna(rep 2)和 kimi 的节点都调用了 test_predictions。

#### TDC 参考模块 v2(用户同意):单一 `official_evaluation(name, predict_fn)`

节点交出 `predict_fn(rows) -> 正类概率`;参考模块自己在验证行上调用并跑官方验证 scorer,再在测试行上调用写出 `working/<name>.test_predictions.csv`。交付物随评估必然产生,DS "只验证不交付" 的失败模式消失。与 BabyLM v2 / psydef `official_score(name, id_to_label)` 同一结构:预测由节点做,评估集与交付由参考模块钉死。离线链路(两份字符 n-gram 逻辑回归)通过:framework 审计 passed、隐藏标签 main_score 0.7886、final 审计 passed。launcher 加 `TDC_REF`(默认 v2)与 `RUN_TIMEOUT`(默认 14400);DS rep 2 以 21600 s 上限发出。同条件可比起见,luna 与 kimi 的 TDC 后续也应用 v2 重跑。

#### BabyLM rep 3(旧 topic + v2 参考模块):用户取消于 16/20,0 通过;rep 4 以修正后的 topic 发出

rep 3 的 16 个节点按判词分类:旧 topic "6 个域" vs 实际 10 个文件 5 个(其中 n11 被判各项功能正确、n15 在固定验证行上得到 156.8 的有效困惑度,仅因"与六域描述不符"判 buggy;n2/n12 因此崩溃);绕过官方评估/自定义切分 4 个(n1/n5/n9/n10);matplotlib `boxplot(labels=)` 废弃导致画图崩溃 2 个(n6 已完成官方验证 178.4 并保存 submission);指标截断 1、验证损失调采样 1、围栏 1、词表 bug 1。结论:不是 ARC 那种单一结构性根因,最大来源是输入里的错误事实(已修),其次是评估绕过的残余(v2 已把它从主因降为次因)。预期 rep 4 能过 stage 1;若仍 0/20 且判词集中,再查"绕过官方评估"为何在 BabyLM 上多于 psydef。

#### 发现:launcher 的 4 小时上限只作用于 docker 客户端,容器不会停

psydef × ds rep 3 于 18:28 启动,`timeout 14400s docker run` 在 22:28 向 docker 客户端发了 SIGTERM,客户端把信号转给容器里的 `bash -lc`,bash 等前台 python 结束才退出 —— 容器与 BFTS 继续跑,launcher 也一直等。之前所有运行都自然结束,所以没暴露。修法:各 launcher 加看门狗子进程,到期 `docker stop -t 30 $NAME`,native 结束后撤销看门狗。对正在跑的 psydef ds rep 3 不追加干预(用户本就要求给 DS 更多时间),让它自然结束。

#### 资源统一(用户决定,2026-09-21 23:0x UTC):CPU 上限统一为 32 核(psydef / ARC / TDC),BabyLM(GPU)16 核;线程上限 = 核数;未设内存上限的 launcher 加 64 GiB

参照 TDC × luna rep 2 的 32 核。主机 384 核、负载约 85,并发 ≤ 5 时 5×32 = 160 核有余量;64 核在 5 并发下会到 320,过近。只影响之后的发射,在跑的容器不变(torch 线程数在进程启动时已定,动态调核数也无益)。
ARC 参考模块打包器修复(`class Estimator(<YourClass>): pass` 代替别名)同此提交快照。

#### BabyLM rep 4(修正域名 + v2 参考模块)stage 1 仍失败(0/20);(ii) 加入 02 专属渲染;rep 5 在 GPU 5 发出(2026-09-24)

- rep 4 判词:15/20 节点未调 `official_validation`,自算困惑度(含 2 个合成语料),luna 判"不是有效官方结果";其余在 idea(PBDS 自适应域采样控制器)的实现上有逻辑错。ideation 只看 topic、看不到参考模块,idea 自己规定了困惑度算法,节点忠实于 idea → 参考模块被绕开。与 ARC rep 1 同类:仅 (i) 不够。
- (ii)(用户同意,仅 02 渲染):`render_ai_scientist_topic` 的 Concrete Goal 第 4 条改为"as reported by the provided reference validation function on its fixed validation lines; a perplexity computed any other way … is not a result of this task",Dataset 下加一行"a reference module is provided at run time …"。其他框架的 brief 未变(已验证)。
- 预注册判读:official_validation 使用率从 5/20 明显上升且 stage 1 通过 → (i)+(ii) 足够;上升但仍 0 通过且判词集中在 idea 算法实现 → 复杂 idea 在 stage 1 写不对,另议;不上升 → 该句未进 idea,查 ideation 输出。
- 昨夜其他结果:psydef × ds rep 5 0.1746(32 核);TDC × ds rep 2 0.8046(参考 v2);TDC × kimi 原生四阶段完成、组装成功,但总墙钟 47017 s、复现运行时 5517 s 两项超契约预算,审计不通过(诊断副本上其余检查全部通过);ARC × kimi host 重跑组装通过、whest 仍拒(未深挖);ARC × ds rep 2 合成路线组装失败。

#### TDC × kimi rep 2 重发(用户决定):上限 24 h,不向 agent 提供时间

`RUN_TIMEOUT=86400`,参考模块 v2,32 核,setsid 独立会话。02 侧没有 01 那种 budget_clock / 时间可见性补丁(仅 psydef 正式 wrapper 里有一处提及,规格臂不用);agent 能看到的时间信息只有正式 TDC topic 里契约原文的预算行("3,600 cumulative experiment seconds, 7,200 total wall seconds")和上游 stage 3 的"每个实验最多 60 分钟"反馈,两者都不动。审计仍会按契约核对两项预算字段;若再超,按契约口径记为超预算。

#### ARC × kimi rep 1 的最终定位 + rep 2 重发;所有 launcher 上限统一 24 h(用户决定,2026-09-24)

- rep 1:stage 4 的 best_solution 没有 import 参考模块,而是把当时的参考模块源码(含旧的"别名"打包器)整段粘进了自己的脚本;复现时跑的是节点内嵌的旧打包器,产出 `Estimator = DiagonalEstimator` 别名,官方 adapter 只认类定义 → 无候选。stage 2/3 的节点正常 import,文件正确。按"选最后阶段"的规则不改选;以修好的参考模块(追加 `class Estimator(<YourClass>): pass`)重发 rep 2(CPU,32 核,24 h)。
- 所有 launcher 的默认 `RUN_TIMEOUT` 改为 86400(看门狗到期 docker stop);不向 agent 增加任何时间信息。
- ARC × ds rep 2:24 个节点 1 个用提供的记录,四个 best_solution 复现各跑满 3600 s 超时(合成元预测器训练),无官方验证记录;按 (a) 口径记为失败,是模型行为结果,不修。

#### TDC × kimi rep 2(`control_e2etdcspec_rep2_tdc02_kimi_20260924_051931`,v2 参考模块、32 核、24 h 上限):端到端通过,main_score 0.7963

原生 99 分钟(5939 s)四阶段完成;组装 4 个 best_solution 复现 25/133/145/120 s,选 stage 2 的 smiles_aware_best_hidden_dim(验证 macro AUROC 0.9394);总墙钟 6361 s、复现运行时 423 s,两项预算都在契约内;framework 审计、隐藏标签打分(AMES 0.7892 / hERG 0.7841 / DILI 0.8157)、final 审计全部通过。与 rep 1(11.2 h、超预算)对比:32 核 + idea 选的模型轻,不是工具改动。

#### BabyLM × luna rep 5(`control_e2ebabylm_rep5_babylm02_luna_20260924_051334`,修正 topic + (ii) + v2 参考模块,GPU 5):端到端通过,词级困惑度 **108.11**

- stage 1 第 6 个节点通过(6/7 调参考模块;rep 4 为 5/20)—— 预注册判读落在"(i)+(ii) 足够"。四阶段完成:stage 2 7 节点 1 通过、stage 3 4 节点 1 通过、stage 4 完成。
- 组装第一次选错:stage 1 通过节点在自己代码里重定义了同名 `official_validation`(冒烟版,1200 词,记录里诚实标了 `official: false, smoke_test: true`),我的组装只读 validation_perplexity 未检查 official → 选中 1.77。修:组装只认 `official: true`(参考模块写的)记录;host 重跑(GPU 5)后选 stage 2 的 domain_conditioned_gru_epoch_5,**108.11**(stage 3/4 为 120.8 / 119.3),打分、校验通过。被选节点未调 save_submission,submission/ 只有验证记录(runner 校验块不检查该项,如实记录)。
- ARC × kimi rep 2:stage 1 第 13 个节点通过但未调 local_validation,stage 2–4 共 17 个节点 0 个用提供的记录(working 里是 synthetic_ground_truth.npy 等),组装无官方验证记录 → 失败。主题里的结果规则在 ideation 的命中率不稳:luna rep 3、kimi rep 1 吸收了,ds 两发、kimi rep 2 没有。
- MountainCar 运行镜像 `ai-scientist-v2:runtime-mountaincar`:在 02 镜像上加一层(577 MB):jax[cpu]==0.6.2、flax==0.10.7、optax==0.2.8、tensorflow-probability==0.25.0、gymnax==0.0.9、dotmap(版本对齐能跑的 01 镜像;最新 jax/gymnax 与起始代码不兼容)。验证:起始 PPO 2 万步 CPU 16 核 52 s 出 5 个 checkpoint,冻结 evaluate.py 11 s 跑通。Dockerfile 快照在 debug/dawei/ladder/staged/mountaincar/。

#### MountainCar 路线(规格体,2026-09-24)

- 正式 02 wrapper 是占位(调用上游不存在的 `--topic` 参数),从未跑过;02 镜像缺 JAX 栈 → 新层 `ai-scientist-v2:runtime-mountaincar`(见上)。
- 参考模块 `mountaincar_reference_v1.py`(经 `--add_dataset_ref`):`starter_src()` / `copy_starter(dest)`(冻结起始代码可改,类名 Model 不变)、`run_starter_training(src)`(起始 CLI,种子 42,写 config-42-{0..4}.pkl;陈述成本事实:2000 万步需数小时,2 万步约 1 分钟/16 核;单条训练命令契约上限 1800 s)、`official_evaluation(name, src_dir, checkpoints_dir)`(在干净目录里放 src + 5 个 checkpoint + 冻结 evaluate.py 的字节副本,运行并解析 Reward Mean,写 working/<name>.evaluation.json 与 .submission/)。
- 组装:复现各阶段 best_solution(JAX CPU 镜像,32 核,单次上限 3600 s),只认 `official: true` 且 submission 完整(5 个 checkpoint + evaluate.py)的记录,选官方 Reward Mean 最高者,提升 src/、checkpoints/、evaluate.py(冻结副本,host 打分校验哈希)、trace、报告。host 校验块从 mountaincar runner 逐行抽出;host 打分用正式 `run_mountaincar_continuous_host_score.py`,`--python` 指向 `mc_python.sh`(在镜像里跑 evaluate.py,因为 host 没有 JAX)。
- 离线链路测试(两份起始基线 best_solution,2 万 / 4 万步):复现 64 s / 100 s,组装、校验通过,host 打分 −11.30(official_evaluate_py)。

#### MountainCar × luna rep 1(`control_e2emcar_rep1_mcar02_luna_20260924_085312`,规格体 + 参考模块 v1,CPU 32 核):stage 1 失败(0/20)

- 20 个节点:5 个崩溃,15 个跑通被判"没有做要求的冻结官方评估";只有 1 个节点调了 `official_evaluation`(且调用方式不对,checkpoint 命名也不符)。其余节点自己写 PPO/评估、把自己的 rollout 均值标成"Official Evaluation",或手动拷 evaluate.py 去跑然后失败。判官(luna)每条都以参考模块的 official_evaluation 为标准。
- 与 BabyLM rep 4 同一形态:任务里节点自己能算出"奖励",参考模块对它没有必要性;正式 topic2_topic.md 只说"improves the official Average Reward / delivers five checkpoints",没有"结果只以提供的评估函数为准"。预期下一步同 BabyLM:在 02 的 topic 渲染(`generate_topic2_native_inputs.py::render_ai_scientist_topic`,mountaincar 生成脚本包装它)加 (ii),待用户决定。

#### MountainCar (ii)(用户同意,仅 02 渲染)+ rep 2

`generate_topic2_native_inputs.py::render_ai_scientist_topic`(mountaincar 生成脚本包装它,其他框架的 brief 未变,已验证):Inputs 下加"a reference module is provided at run time with the starter-code helpers and the official evaluation function";Concrete Goal 第 2 条加"a result of this task is the Reward Mean reported by the provided reference `official_evaluation` (the frozen evaluate.py on exactly five checkpoints); a reward computed any other way (own rollouts, own evaluator, fewer checkpoints) is not a result of this task"。预注册判读同 BabyLM:official_evaluation 使用率从 1/20 明显上升且 stage 1 通过 → (i)+(ii) 足够。rep 2 发出。

#### BabyLM × ds rep 1(`control_e2ebabylm_rep1_babylm02_ds_20260924_093724`,修正 topic + (ii) + v2 参考模块,GPU 5,VLM=luna):失败(native=143 assembly=4)
- stage 1:DS 作 judge 把两个合成随机数据、未调 official_validation 的节点判为非 bug,血统钉死;stage 2/3/4 新增 14 节点全 buggy(后期 judge 反而抓出"合成数据")。
- 装配:四段 best_solution 回放,只有 stage 3 的 d7f436 产出困惑度 **1.003**——该节点把参考模块整段内联进自己的代码(自定义 `official_validation`,`official: true` 也照抄),nll_fn 泄漏(验证 loss 0.0015 < 训练 loss),judge 已判 buggy 但仍是该 stage 的 best_solution。契约需要 ≥2 段有困惑度 → assembly exit 4,不出分。
- 两个弱点记录:(a)`official: true` 守卫防不住节点内联参考模块;(b)official_validation 信任 nll_fn,泄漏得 ppl≈1。按"合成数据 = 失败"入账,不重发。

#### MountainCar × luna rep 2(`control_e2emcar_rep2_mcar02_luna_20260924_103646`,(i) 参考模块 v1 + (ii) 结果定义句,CPU 32 核 JAX 镜像):端到端通过,Reward Mean **−10.78**(冻结 evaluate.py)
- stage 1:19 节点,18 buggy / 1 good;good 节点(第 19 个,`epc_preliminary_fixed`)是第一个把交付格式做对并调用 `official_evaluation` 的节点。前 11 个节点全部用 PyTorch 重写策略、绕过或做不对冻结评估(节点自算本地奖励 −0.22 vs 官方 −10.78)。
- stage 2/3/4 各达迭代上限;装配回放:stage 2 −10.778、stage 3 −10.778(同一套 checkpoint)、stage 1/4 无官方记录;选 stage 2。writeup 后框架自行清理进程(native=143,与 BabyLM rep 5 同形)。
- host 校验通过,host 用镜像内冻结评分器复算 −10.78。02 MountainCar 首格出分。

#### BabyLM × kimi rep 1(`control_e2ebabylm_rep1_babylm02_kimi_20260924_100543`,GPU 4,judge=kimi):失败(assembly=4,0 段回放有困惑度)
- stage 1:15 节点,1 good——用合成数据、未调 official_validation(kimi 作 judge 与 DS 同样放行合成节点;对比 luna 作 judge 在 rep 5 全程拦住)。stage 2:6 节点 3 good 全合成;stage 3:7 节点 2 good;stage 4:3 节点 1 good。
- 磁盘上 3 条官方记录都来自 buggy 节点;四段 best_solution 回放(1149/905/1790/2461 s)均无困惑度。按"合成数据 = 失败"入账,不重发。
- 至此 02 规格臂:BabyLM luna 108.11 / ds 失败 / kimi 失败;MountainCar luna −10.78。

#### MountainCar × ds rep 1(`control_e2emcar_rep1_mcar02_ds_20260927_055912`,主题含"只用提供数据"句、参考模块为旧 docstring,VLM=luna):失败(native=1 assembly=3)
- stage 1 跑满 20 节点,20/20 buggy,0 good。只有 6/20 节点的代码调了 `official_evaluation`;9 个没调;7 个是 NameError/TypeError 之类代码错误;1 个只存了 4 个 checkpoint 被官方评估拒。
- DS 作 judge 这次没有放行自评或非官方结果(与 ARC/BabyLM 的宽松放行不同),失败在 coder 能力:20 个节点内没写出一个跑通冻结评估的实现。
- stage 1 无 good node,框架不进入 stage 2;随后框架自己的 `overall_summarize` 因只有 1 个 stage 抛 ValueError(expected 4, got 1),native 退出 1。装配只找到 1 个 stage 的 best_solution,契约要求 2–4,exit 3。

#### MountainCar × kimi rep 1(`control_e2emcar_rep1_mcar02_kimi_20260927_055932`,主题句已加、参考模块旧 docstring):失败(assembly=4,0 段有官方记录)
- stage 1:14 节点 2 good——两个 good 节点都是 gymnasium 真环境 + 自写 PyTorch PPO + 自评奖励(92.6/93.7),未调 official_evaluation;kimi 作 judge 放行自评分数(与 DS 在 ARC/BabyLM 的放行同型)。
- 四个 stage 的 best_solution 全是同一个 stage-1 节点 411646e0(血统锁死的极端形态:后续 stage 从未产出更好节点);回放 4 次均无官方记录 → assembly exit 4,不出分。
- 入账:研究未完成;kimi 判官对"日志干净的自评结果"不执行任务文本规范,再添一例。

#### ARC × ds rep 5(`control_e2earc_rep5_arc02_ds_20260927_122453`,A5+A6+B11 全套,VLM=luna):端到端通过,官方分 **0.14**(whest,越低越好)
- 与 rep 3 的唯一变量是 B11。stage 1:7 节点全部 import 参考模块、全部调 local_validation、0 合成;四个 stage 全走完,四份 best_solution 里三份有官方记录。
- 但方法退化:所有配置的本地验证 MSE 都是 1.4499(退化为平凡预测,深层激活趋零),官方分 0.14 ≈ 1.45×0.1 算力下限系数,明显差于 luna 的 0.0988。02×ARC×ds 首次出分,分数诚实反映"协议已遵守、方法平凡"。
- 判定:research_completed=true,scored=true;B11 单变量证据成立(DS coder 的合成行为由框架原生指令驱动)。

#### ARC × kimi rep 5(同版本):失败(native=1 assembly=3)
- stage 1 跑满 20 节点 0 good(kimi 判官把产出合法官方记录的节点也判 buggy);无 stage 2;overall_summarize 因单 stage 崩(已知工程杂音,用户决定不修)。装配只见 1 个 stage,契约需 2-4,诚实失败。
- 行为有改善:6/20 调官方验证、4 条合法记录(全为退化 MSE 1.4499),但 kimi 严格判官加方法平凡,过不了 stage 1。

#### MountainCar × ds rep 2(`control_e2emcar_rep2_mcar02_ds_20260927_132821`,A5+A6+A7+B11):失败(native=1 assembly=3,stage 1 20 节点跑满)
- 对比 rep 1(6/20 调官方评估):rep 2 首节点即调官方评估,全程约 7-8/20;但没有一个节点跑通冻结评估(PyTorch 权重与加载接口的搏斗贯穿始终),0 条官方记录;唯一 is_buggy=False 的节点其实调了官方评估(记录未写成)但被 VLM 判 is_buggy_plots=True,不算 good node,stage 1 因此无通过节点。
- A7 把失败原因从"不知道接口"变成"知道接口但转换不动"(节点尝试 torch→flax 转换失败);判定仍是 DS 实现能力,按封线决定入账,不再补丁。

#### 夜间批次终态(2026-09-28 晨)
- **BabyLM × ds rep 3(A5+A6+B11+B12 终版,GPU 4):端到端通过,词级困惑度 85.28**——全表最好(01-ds 106.58、02-luna 108.11)。选中 stage 3 的 divide_conquer_fusion;同 stage 另一配置 92.39 互为佐证;记录 official:true,固定验证行常数(33583 行/975273 词)与参考一致,nll 与 ppl 自洽。已知弱点同 luna 108.11:获胜节点内联参考模块(非 import)、未存模型工件(submission 只有验证记录),口径与 luna 格一致故接受。
- **BabyLM × kimi rep 3(终版):失败** assembly=4,0 段回放有困惑度。kimi × BabyLM 两版本均失败,封线入账。
- **ARC × kimi rep 6(B11,用户点名重发):失败** assembly=4,仅 1 段回放有合格 estimator(契约需 2)。stage 1 血统锁于自评节点,stage 2-4 未恢复官方调用。ARC × kimi 封线入账为失败。
- **ARC × ds rep 3 装配(旧输入版,历史遗留):失败**(0 段合格),不影响表格(该格由 rep 5 的 0.14 代表)。stage 3/4 回放各超时,旧装配脚本各泄漏一个容器(已由用户处置)。
- **01 ARC × kimi(空闲超时试点):历史性地跑完全流程但被门槛拒(42)**。五份交付物齐全、4 个实验、选中 exp_003_rcae_calibrated;拒因=trace 的 framework_internal_model 写成 "gpt-4"、base_url 写成 api.openai.com(kimi 幻觉填表;实际注入模型为 kimi-k2.6)。**空闲超时补丁夜间触发 5 次、每次通道恢复,kimi 首次未卡死走到交付**——工具目标达成;失败性质=trace 元数据不实,按契约判 conformance 失败。estimator 留存,可做诊断性离线打分(未做,待示)。
- **01 MountainCar × ds:门槛拒(42)**:agent 自己把 5 个 checkpoint 放到根目录(交付桥无需搬运),但 trace 只记 1 个实验(exp_001_ds_epac_full),门槛需 2-4。run-local 措辞已是 2-4,DS 没有照做——与 luna run 2 同型的"1 实验"失败,这次不是措辞背锅。
- **01 MountainCar × kimi:native 崩溃(rc=1)**:AI-Researcher 原生脆弱点——ML 阶段未产出 experiment_report 时,run_infer_idea.py:517 直接 KeyError。无交付物。候选 01 稳健性适配器(记入待办,未做)。
- 夜间花费(账号侧,账单页仅覆盖到 20:39):窗口内约 $7.9,其中合作者(gpt-6-luna+ds-pro)约 $2.2;我们侧多为 ds(babylm rep3 长训练)。总体与睡前预估一致。

#### gpt-6-luna 列首批终态(2026-09-28 晨)
- **01 ARC × gpt-6-luna:通过,官方分 0.142**(whest,越低越好;第 2 发,回退层每次调用触发一次、共 78 次全过)。
- **01 psydef × gpt-6-luna:通过,0.1294**(第 3 发;tool_choice 预清洗后一次通关)。
- **02 ARC × gpt-6-luna:通过,官方分 0.138**(rep 1 一次通关;四个 stage 全部有官方验证记录,g6 判官全程执行协议)。
- **02 psydef × gpt-6-luna:装配中**(四 stage 全过,13/19 节点 good,官方调用全覆盖,历史最干净的 02 运行形态)。
- **01 ARC × kimi(本轮):失败于包装脚本尾部缺陷**。研究本体完成:五份交付物齐全、trace 模型字段正确(模型字面值补丁生效)、7 个实验;native 末尾以 127 退出,未到门槛。离线门槛回放:即便到达也会因"7 个实验超出 2-4"被拒——kimi 这次输在超量而非缺量。**包装脚本尾部缺陷(开放 bug,只记确证事实)**:仅出现在尾部失败的运行(本发与 g6 首发),成功运行日志中不存在;日志恰终止于该行;报错指向外层脚本 629 行并含被截断的探针路径;两次深入分析被安全层拦截,不再沿原路径追查,待新思路或单独复现环境再议。
- **TDC × gpt-6-luna(02, rep 1):端到端通过,隐藏标签 main_score 0.7697**(AMES 0.8104 / hERG 0.7277 / DILI 0.7709);框架审计与最终审计双过。g6 列 02 侧第三格。
- **TDC × gpt-6-luna(01):端到端通过,隐藏标签 main_score 0.8212**——TDC 全表新高(此前最好 02×g6 之外的三模型均 ≤0.79;02×g6 反而是 TDC 四模型最低 0.7697)。调研 235 轮后 65 轮实现,墙钟内完赛。
- **BabyLM × gpt-6-luna(01, rep 2)**:keepalive 移植后首发即触发一次并成功续跑(上一发同点位直接全场报废)——补丁当日回本。

#### gpt-6-luna 列第二批终态(2026-09-28 上午)
- **MountainCar × gpt-6-luna(02, rep 1,`control_e2emcar_rep1_mcar02_g6luna_20260928_061454`):端到端通过,Reward Mean −10.777684,std 2.2127767**。但与 luna rep 2 的分数**到机器精度逐位相同**(mean 与 std 均为 −10.777684211730957 / 2.2127766609191895)。冻结 evaluate.py 是把全部 5 个 checkpoint × 各 seed 的回报汇入同一数组再取 mean/std——两组 5 个 checkpoint 里只有 `config-42-1.pkl` 字节相同(md5 cb79ee…,且该文件同时出现在 g6 自己的 20000/100000 两个 submission 里),其余 4 个字节不同却完全不改变汇总分布 ⇒ 两次运行交付的 5 个策略在评估分布上行为完全一致,唯一共同的确定性来源是参考模块 seed-42 起始训练。**结论:02×MountainCar 的 −10.78 是"起始配置不动点",luna 与 g6 两格都是管线通过、但无可归因于模型的策略改进**;表格入分时带此脚注。
- **BabyLM × gpt-6-luna(02, rep 1,GPU 5):失败**(assembly 中止:仅 1 个 stage 选择,契约需 2-4)。stage 1 共 20 节点 0 good、0 官方记录;异常谱:SyntaxError 9(已知 code-only 回复解析缺陷形态)、OOM 3、AcceleratorError 1、RuntimeError 1、无异常判 buggy 6。BabyLM×02 至此四个模型(luna/ds/kimi/g6)全部未通过,维持"框架属性"判定,不加补丁。
- **01 MountainCar × gpt-6-luna(rep 1,`fullrun_mcar_01_g6luna_20260928_061154`):门槛拒(42),0 checkpoint**。agent 自行编写了依赖 GPU 的训练管线,GPU 预检 exit 3(本 topic 包装器统一 `FRAMEWORK_DISABLE_GPU=1`,CPU-only,对所有模型一致;同期 kimi 在纯 CPU 上以 ~52 核正常训练),此后未转向 CPU 方案,90 分钟即自行收尾且未写正式报告。预算对等已核实:g6 与 kimi 的 native 均为 `timeout 86400s`,budget_clock 仅可见性不强制。判定:模型自身失败,列入 3 发通过率协议的重发候选。
- **01 MountainCar × kimi(`fullrun_mcar_01_kimi_20260928_044203`):终态 failed/137(用户授权提前 stop,09:48)**。经过:训练完成、`workspace/checkpoints/` 5/5 齐全,但 06:39 起 `execute_command('… run_training_testing.py | head -100')` 结果再未返回(terminal_tools 第二通道缺口;冻结期间零 API 消耗)。用户明示后 09:48 `docker stop`——**事后发现 handoff/门槛/评分整段都在容器内命令尾部(PYRELOC heredoc),container 级杀灭把它们一并跳过**,宿主侧仅补写 failed/137;此前"stop 与 24h 上限等价"的判断有误:上限路径是容器内 `timeout` 只 TERM python、bash 尾部照常执行 handoff。表格结论不变:trace 仅 1 个实验(`sde-dp3-mountaincar-001`),即便 handoff 跑了也会被门槛(2-4)拒,与 mcar×ds 先例同型 → 该格第 1 发失败入账,省下 ~19h。运行目录完整保留(checkpoint、trace、全量日志)。**教训:今后对 01 wrapper 提前收割,正确杠杆是 `docker exec kill` 容器内 run_infer 进程(与上限 TERM 语义一致,容器内尾部继续跑),而不是 docker stop 整个容器。**不对本 run 目录做任何事后补跑(host 不回填框架侧流程)。
- **01 BabyLM × gpt-6-luna(rep 2,进行中)**:08:18–09:25 停摆一小时(外层框架与内层 tcp_server 同时单核 100%、无 LLM 流量;此形态既不抛连接异常(keepalive 不触发)也不满足 run_command 静默(空闲超时不触发)),09:25 **自行恢复**继续运行。我在恢复前尝试的手动沙箱重启被权限层拒绝、未执行,run 未被干预。
- **第二命令通道(terminal_tools execute_command)缺口升级**:一夜之内实际冻结 mcar×kimi 一格(至上限),且 babylm 停摆形态疑似相关。候选补丁 = 把空闲超时/keepalive 语义延伸到该通道(仍为 wrapper 层 adapter,不动框架源码)。按"先汇总再修"纪律**未实施**,待用户裁决。

#### MountainCar 实验数契约统一为 ≥1(2026-09-28,用户三项逐项批准)
- 裁定方向:回到上游 topic2 原版的 "one or more"(≥1,**上限亦随之取消**;预算由 24h 墙钟兜底),而非契约文字向 2-4 看齐。考古结论支撑:topic2 原版契约与门槛自洽(≥1);2-4 随 00da561(08-19)的 mountaincar 分叉进入且从无契约文字支撑;本地 09-03 用 topic2 文本填 0 字节契约时埋下文字/门槛分裂。
- 三项改动:**7945411** 共享门槛 2-4→≥1(逐字取自 topic2 runner);**c1b7fd0** 撤 01 wrapper 的 [mcar-01-wording] run-local 改写(agent 此后读契约原文);**9129f60** 02 装配 stage-selection 下限 2→1(staged 实盘同步)。其余 topic(ARC/psydef/TDC/babylm)契约与门槛本就自洽 2-4,不联动。补丁链健康检查 111 项全 OK。
- **追溯重裁**(bd54 系列 adjudicate_mountaincar_ge1.sh;独立目录 `real_eval/runs/adjudication_mcar01_ge1_20260928/`,原 run 目录零接触;门槛从现行 runner 运行时逐字抽取,官方评分在 ai-researcher-exec:mountaincar-jax 镜像内、--network none):
  - **01 mcar × ds(124914):≥1 门槛通过,官方分 −13.4445**(std 2.00,official_evaluate_py,5 checkpoint)→ 入表并注明"≥1 追溯重裁"。**01 MountainCar 首格出分。**
  - **01 mcar × luna(121831):重裁仍拒**——research_idea.json 缺契约必需的全部四字段(hypothesis/method_rationale/expected_failure_modes/comparison_logic;用了自有 schema)。该检查自 00da561 就在门槛里,09-24 被排在其前的计数检查掩盖;拒因由"计数"更正为"idea schema 违约"。当年 −9.44 系交付桥验证的非正式数字,不入表;Q10 "应过门槛"的预期被此深层违规推翻。
  - kimi(044203)五件交付物意外齐全(含 final_report.md),但未被计数拒过(容器级终止),不在批准名单;是否同法重裁待用户表态。
  - **kimi 重裁(用户随后批准,同日执行):gate 拒**——trace 的 `framework_internal_api_base_url` 写成幻觉的 `https://api.openai.com/v1`(实际注入为 bianxie 中转;`framework_internal_model` 倒是写对了 kimi-k2.6)。与 ARC kimi 幻觉 "gpt-4" 同族:模型侧溯源违约,契约明文要求记录注入的 base URL。拒因=溯源失实,非计数。ARC 侧当年以 [arc01-model-fact] run-local 注入事实补齐;mcar 无对应补丁——是否移植(A 类输入事实,run-local)待用户决定;g6 rep2 未带,与既往发次同条件。
  - **三重裁总结:除 ds 外,计数从来不是真实拦截**——ds 全合规 −13.44;luna 倒在 idea schema;kimi 倒在 URL 溯源。旧 2-4 门槛只是把更深的违约挡在了视线外。
- 表格 01 MountainCar 行更新:luna 拒(idea 缺字段)/ ds **−13.44**(≥1 重裁)/ kimi 拒(URL 溯源失实;≥1 重裁)/ g6 拒(0 ckpt,rep2 已重发)。
- **01 mcar × g6 rep2 重发**:首次发射(105316)因发射副本的 ROOT 自推导指向 scratchpad、source lib 失败而当场退出——**未创建任何 run 目录,零残留**;修正 = 按 AGENTS.md 显式导出 `RESEARCHCLAWEVAL_ROOT`,新时间戳重发(权限分类器瞬时故障延迟了重发,恢复即发)。
- **02 mcar 重裁需求初判(基于既有记录,逐 run 扫描待分类器恢复后确认)**:ds rep1/rep2 均以 assembly=3(stage-selection 下限出口)失败 → **程序性候选**:≥1 下装配会继续走回放,能否出分取决于所选 stage 有无 official:true 且 submission 完整的记录(记录显示 ds 两发"0 条官方记录",预期回放仍无分,但按程序应重跑装配定论);kimi rep1 assembly=4(回放后 0 段官方记录)非候选;luna rep1 stage1 0/20、无官方调用,即便过下限也无可回放记录。
- **02 mcar 三发重裁执行完毕(2026-09-28 午,`adjudication_mcar02_ge1_20260928/`,原 run 只读,产物隔离)**:luna rep1、ds rep1、ds rep2 全部 **assembly rc=4,"0 个回放产出官方评估+完整 submission"**——与预测一致,无分;三格拒因由"stage-selection 下限拦截"正式更正为"官方记录缺失"(模型侧:节点代码未跑通冻结评估)。执行中发现装配还有第二道下限(回放后官方记录数 <2 即拒,"contract needs 2")在 9129f60 中漏改,已补齐为 ≥1(8ecb5a5,staged 实盘同步);三格判定不受影响(0 条官方记录两种下限都过不了)。02 babylm/psydef/tdc/arc 的装配下限维持 2-4 不动(它们的契约本就是自洽 2-4,≥1 裁定仅限 mcar)。
- **02 mcar × kimi 考古与 rep3(2026-09-28 午,用户指令重发)**:发现 09-27 下午曾有 rep2(`control_e2emcar_rep2_mcar02_kimi_20260927_132841`,与 ds rep2 同批)——**状态 aborted**,是当日用户喊停省 API 的取消批,非门槛拒,不属重裁对象(2 selections/0 官方,补完也无分);重裁资格扫描结论不变。新发 rep3 首次发射(122942)因我用 awk 从 toml 提 env 只得 2 行、缺 OPENAI_API_KEY,3 分钟内 IDEATION_EMPTY×3 干净自败(**运营配置失误,不计入 kimi 尝试数**,目录保留;顺带验证装配新 "needs at least 1" 出口文案已生效)。修正 = 从 g6 的完整 10 变量 provider env 克隆换模型名(key 同 bianxie 账号,env_key=OPENAI_API_KEY),rep3 二次发射 `control_e2emcar_rep3_mcar02_kimi_20260928_123456` 正常起跑,watcher 挂 `launch_e2emcar_kimi_3b.nohup`。该发将是第一个完整跑在 ≥1 双下限之下的 02 mcar 新运行。
#### 09-28 批次终态清算(2026-10-02 收账;bianxie 额度于 09-28 ~12:43 归零)
- **额度墙时间线**:12:42:10 tdc×kimi(剩余 $0.012)→ 12:42:22 tdc×ds($0.038)→ 12:43:32 02 babylm×g6(−$0.013)→ 12:44:07 arc×kimi → 12:45:32 02 mcar×kimi rep3。此后所有在飞运行于 12:42-12:46 间死亡。
- **死于额度墙(基础设施原因,不计入模型尝试数)**:01 tdc×ds(survey 174 轮、未开始实现)、01 tdc×kimi(survey 710 轮仍未动手;g6 当年 235 轮动手)、01 arc×kimi(ml 24 轮)、01 babylm×kimi(12:45:54 RetryError[APIError],failed_no_artifacts)、02 mcar×kimi rep3(stage1 仅 2 节点)。五格待在新中转上重发。
- **01 mcar×g6 rep2:研究自行完成(12:27 'completed_further_matched_experiment'),五件交付物齐全、trace 真实(gpt-6-luna + bianxie URL),却被门槛以 "must set framework_internal_model=gpt-5.6-luna" 拒(42)——宿主侧缺陷**:共享 runner 的 MC_MODEL 取自 PROVIDER_CONFIG toml(该发射未显式指定,.env 默认为 luna toml),与 wrapper 注入容器的 REAL_EVAL_FRAMEWORK_MODEL 分叉;潜伏于所有非 luna 的 01 mcar 发射(历史 run 均先死于更早的检查,未曾暴露)。10-02 按真实模型复判(`adjudication_mcar01_ge1_20260928/g6_113815`):门槛通过,**官方分 −11.2979**(std 见 score.json)→ 入表。wrapper 加固 2be7bf7:exec runner 前 `export MOUNTAINCAR_CONTINUOUS_MODEL=$MC_MODEL`。注:−11.298 与 02×g6 装配里 stage1 `absolute_ppo_smoke` 配置的值相同,疑似又一个起始配置不动点(trace 仅 1 个实验)。
- **01 babylm×g6 rep2:finished,词级 ppl 2429.9**(trace 两值 2429.9/2563.2)——伤残完赛:keepalive 共触发 5 次(07:21、11:53×2、12:37-38×2;后两对与我同时段密集发射的时间重合,疑似宿主负载导致内层通道断裂),**每次内层沙箱重启后 /workplace/project 被清空(仅数据挂载残留)**,agent 最后一次重建后 12:39 自述无法验证结果并收尾。分数入表但注明"keepalive 重启清空工作区"。keepalive 在 babylm 内层容器的这一副作用是新观察(ARC/mcar 内层未见),待用户裁决是否处理。
- **02 babylm×g6 rep2:finished,词级验证 ppl 185.75**——native 在 stage 3 死于额度墙(native=1),stage1/2 有官方记录,装配选 stage2 `gru_shuffled_lr_2e-03_seed_17`,host 评分+校验通过。02 babylm×g6 首次出分(research_completed 部分、scored/contract_complete 通过)。
- 表格更新:01 mcar×g6 **−11.30**;01 babylm×g6 2429.9(伤残);02 babylm×g6 **185.75**。

#### BabyLM "keepalive 清空工作区"排查结论(2026-10-02):不是 keepalive,是 wrapper 启动时的前缀清容器
- 磁盘证据:01 babylm×g6 rep2 的内层 /workplace 真身在宿主 `…/workplace_paper/task_babylm_10m_idea_openai__gpt-6-luna/workplace/workplace/`,project 完好(44 个文件,模型/训练脚本/checkpoints 10:37/results 11:01),**11:53 之后零文件落盘**——没有任何东西被清空,是 11:53 起 agent 再也连不上原容器。
- 日志证据:11:53:02 起 `wait_for_container_ready` 的 `docker inspect` 返回 rc=1(容器**不存在**,非停止);keepalive 的 `docker restart` 对已移除的容器无效;此后 45 分钟所有工具调用报 "Container …" 错误,agent 自述"工作区被清空"实为"换了个空容器/无容器";12:39 以 11:01 前的真实实验结果收尾(ppl 2429.9 来自死前的真实实验)。
- **根因**:[01_ai_researcher_real_babylm.sh:28](real_eval/scripts/01_ai_researcher_real_babylm.sh#L28) 启动时 `docker ps -a | rg '^ai_researcher_babylm_' | xargs docker rm -f`——**按前缀清掉所有 BabyLM 内层容器**。我 11:52:55 发射 babylm×kimi,7 秒后 g6 的沙箱被它删除。修复 75238c5:删除该前缀清理(第 24 行按本 run 精确名清理保留;孤儿容器清理改为人工操作)。
- **全仓审计(按前缀批量删/停容器)**:psydef wrapper 的清理按 run id 限定(安全);01 TDC/mcar/ARC wrapper 无前缀清理;02 staged launcher 只对自身 $NAME 做时限 stop。**两处共享 runner 的 EXIT trap 为潜在同类隐患**(非 01 路径,01 ARC/babylm wrapper 自包含不经过它们):`babylm_framework_fullrun.sh:61` 退出时删所有 `ai_researcher_babylm_*`;`arc_framework_fullrun.sh:84` 退出时删所有 `arc_wbe_2026_eval_*`(= 01 ARC 内层沙箱的命名前缀)。任何经共享 runner 的 ARC/BabyLM 运行退出都会误杀同时在跑的 01 同 topic 沙箱。属共享层——**用户当日批准**,已改为"前缀 + 本 run 的 RUN_ID"(trap 只删自己的内层沙箱),离线名单测试各仅命中本 run 1 行。
- 推论:01 babylm×g6 的 2429.9 是被外力截断的运行结果;按基础设施原因不计入 g6 的尝试数,可重发。

#### paratera 切换后的首批运行(2026-10-02 午)
- 补遗:provider toml 的 key 走 `experimental_bearer_token` 字段(lib `real_eval_provider_env_from_codex_toml` 只读该字段,不读 env_key)——首发金丝雀 131427 以 401 "Invalid proxy server token"(旧 bianxie key)自败;四个 toml 的 bearer 已换新 key(sha 对齐 .env),scratchpad provider env 的 `OPENROUTER_MODEL` 改指 paratera 上存活的同模型(kimi→Kimi-K2.6,g6→GPT-6-Luna;GPT-5.6-Luna 当前 503)。
- **金丝雀 01 TDC×ds(131845)在 paratera 跑通**:40+ 轮 LLM、零 401/4xx/5xx,模型 DeepSeek-V4-Flash,经 tdc-gpt-relay 中继。provider 链验证完毕,其余四发随后放出。
- 13:25 放出其余四发(均 paratera、精确大小写模型 ID、冻结副本、watcher 齐挂):01 TDC×kimi `fullrun_tdc_01_kimi_20261002_132511`、01 ARC×kimi `fullrun_arc_01_kimi_20261002_132514`(第 3 发)、01 BabyLM×kimi `fullrun_babylm_01_kimi_20261002_132518`(修复前缀清理后的 wrapper 快照)、02 mcar×kimi rep3 `control_e2emcar_rep3_mcar02_kimi_20261002_132526`(第三次物理发射,前两次为配置/额度中止,首个完整运行在 ≥1 双下限之下的 02 mcar 新运行)。
- **BabyLM×g6 两格重跑(用户指令,14:05):**01 babylm×g6 **rep3** `fullrun_babylm_01_g6luna_20261002_140521`(GPU 6;rep2 的 2429.9 为被截断的伤残结果)、02 babylm×g6 **rep3** `control_e2ebabylm_rep3_babylm02_g6luna_20261002_140645`(GPU 2;rep2 的 185.75 为 stage 3 被额度墙截断、未 e2e 跑完的部分结果)。两发均 paratera + GPT-6-Luna,watcher 齐挂;GPU 板上每张卡都有其他租户驻留显存,选的是剩余最多的两张(各余 ~42.7GB)。rep3 落定后替换表格中的两个带注释分数。
- **GPT-6-Luna 在 paratera 也不稳(14:0x 起)**:01 babylm×g6 rep3 前 3 轮里 2 次 502 "BadGatewayError: 模型服务异常,请稍后重试"(Model Group=GPT-6-Luna,Fallbacks=None);02 babylm×g6 rep3 ideation 三次拿到正文 None(解析器 NoneType)→ native=1 当场结束(`control_e2ebabylm_rep3_…_140645`,**基础设施原因不计尝试**)。直接探测偶尔 200(正文正常在 `content` 字段)、偶尔 502,即上游线路抖动。至此 paratera 上:DeepSeek 稳定、Kimi 429、GPT-6-Luna 502 抖动、GPT-5.6-Luna 503。
- **02 × GPT-6-Luna 在 paratera 上被判 blocked(2026-10-02 下午)**:02 babylm×g6 rep3 二次发射(`…_141619`)在 GPT-6-Luna 已稳定(8/8 探测 200)后仍 ideation 三连空。用 `real_eval/scripts/probe_02_ideation_raw.py`(02 镜像内原样复放真实首轮请求,只 dump 原始响应)复现:**13,435-token 的 ideation 提示 → 模型只回 1-2 句"我先去搜文献/看合同,再给方案",finish=stop,74-141 个 completion token,无 tool_calls、无 reasoning token;追加一轮"继续"得到空正文**。参数无效:reasoning_effort high/medium/none、max_completion_tokens、tool_choice=none 均同形;topic 正文截断无效(提示长度来自系统协议提示本身,topic 仅 1,945 字符);同协议的 ~100-token 简化提示则能正确输出 ACTION 块。同一模型在 bianxie 上曾正常完成 02 ideation(09-28 的 ARC/psydef/TDC/mcar/babylm 五格)。判定为**提供商部署行为**,按 AGENTS.md "无法经原生入口运行 → blocked",不做提示注入式绕过;02×g6 列维持 bianxie 时代结果(babylm 185.75 为 stage-3 截断的部分结果)。可向 paratera 提交该复现。01 × GPT-6-Luna 不受影响(litellm 函数调用路径,babylm rep3 正常推进)。
- **根因定位(2026-10-02 傍晚,直连 curl 二分)**:02 真实 ideation 请求只含 system 2,936 字符 + user 2,137 字符(≈1,300 token),paratera 却报 **prompt_tokens=13,435、cached_tokens=13,056**——GPT-6-Luna 路由对该请求**前置注入了约 12k token 的隐藏静态上下文**(缓存命中=固定脚手架)。二分:(a) 真实 system + "hello" → 12,971 token,仍只回计划;(b) 普通 system + 真实 user → 481 token,正常长文;(c) **真实 system 去掉 131 字符的工具描述行**(`- **SearchSemanticScholar**: Search for relevant literature…`)+ 真实 user → 1,036 token、**正确输出 ACTION: SearchSemanticScholar / ARGUMENTS**;(d) system 前半段 → 正常;(e) DeepSeek-V4-Flash 用完全相同的真实提示 → 1,087 token、正常 ACTION;(i) 01 式 API `tools` 函数调用 → 69 token、正常 tool_calls(**01 不受影响**);(ii/iii) 短 system 仅含该工具行 → 不注入;(iv) Kimi 同真实 system → 602 token,不注入。即:触发条件 = GPT-6-Luna 路由 + "带工具描述的长代理人设提示"的组合,被套上提供商自己的代理/工具脚手架后模型把回合交给"工具"。合成长提示(7k/14k 填充、带 THOUGHT/ACTION 协议)均不注入且输出正常,说明不是长度、不是推理关闭(48×17−23 答对)。**结论:不是输出格式问题,也不是服务器阻塞/额度,而是提供商静默改写提示;等待不会自愈。** 技术上去掉那 131 字符即可绕过,但那是改框架原生提示且无法保证提供商不再改写别处,不采用;02×g6@paratera 维持 blocked,建议向 paratera 提交该最小复现。
- **paratera 的 Kimi-K2.6 线路大面积 429(13:4x 起)**:错误文本为上游 "You exceeded your current quota"(中转站 Kimi 线路池部分上游额度耗尽;DeepSeek 完全正常,我们账号无关),8 次探测 6 次失败。三发 01 kimi 原地重试、02 mcar×kimi rep3 停止出新节点并随后自行以 native=1/assembly=4 结束。**用户指令停掉全部 kimi 运行**(13:58):01 TDC×kimi 132511 → failed_native_research、01 ARC×kimi 132514 → failed/143、01 BabyLM×kimi 132915 → failed_no_artifacts(均对容器内 run_infer 发 TERM,与 wrapper 上限路径同语义,wrapper 尾部自行写终态;ARC 的内层沙箱残留按精确名清除);02 mcar×kimi rep3 132526 在停之前已自行结束。**四格均为基础设施原因(中转站上游配额),不计入 kimi 尝试数**,待 paratera Kimi 线路恢复后重发。paratera 的 `/key/info` 管理接口被禁用,预算/账单仍不可见。
- babylm×kimi 132518 **当场失败(发射配置,不计尝试)**:自动挑卡输出为空 → wrapper 回落默认 `REAL_EVAL_ALLOWED_GPUS=0,1,2,3` → 嵌套 GPU 隔离补丁生成 `--gpus device=0,1,2,3` 撞 docker "cannot set both Count and DeviceIDs"。教训:该补丁要求**单卡索引**。挑卡为空的原因是 GPU 板已变:8 张卡全部被其他租户驻留 30-67GB(0% 利用率),无全空卡;按剩余显存最宽裕的 6 号(余 42.7GB)单卡重发(id 见后续扫描)。共享卡上存在与他人驻留模型争抢显存的 OOM 风险,已知悉。

#### 01 算力预算对齐 02(2026-10-02 下午,用户裁定"按 02 的数字给 01,旧格结果不管")
- 起因:01 TDC×ds@paratera 容器 405% CPU——其实是顶着共享 runner 硬编码的 `--cpus 4` 天花板在训练(宿主 384 核、负载 71 为其他租户)。盘点发现 02 的生产 launcher 给 TDC/ARC/psydef/mcar **32 核**、BabyLM **16 核**(+64g),而 01 实际是 TDC 4 核(runner 硬编码 + wrapper `EXEC_CPUS=4`)、其余 topic 嵌套沙箱 8 核(隔离补丁默认值)——同 topic 两框架差 2-8 倍,TDC 又受契约 3,600s 累计训练时长约束,01 被系统性饿着。
- 改动:共享 runner [tdc_admet_tox_framework_fullrun.sh:329](real_eval/scripts/tdc_admet_tox_framework_fullrun.sh#L329) `--cpus 4→32`(用户批准);五个 01 wrapper 向框架容器注入 `AI_RESEARCHER_EXEC_CPUS`(TDC/psydef/mcar/ARC=32,BabyLM=16)供嵌套沙箱隔离补丁取用。内存不动(01 沙箱本不限内存,≥02 的 64g)。
- 口径:已出分的 01 旧格(ARC/psydef/TDC g6 与 luna 等)为旧预算结果,用户决定不重跑、不纠结;新发射一律新预算。正在跑的 TDC×ds(131845,4 核)按用户指令 kill(容器内 TERM,wrapper 自行收尾),在新预算下重发:`fullrun_tdc_01_ds_20261002_145722`(容器核验 NanoCpus=32、EXEC_CPUS=32、16g)。01 babylm×g6 rep3(140521,沙箱 8 核+GPU 6)用户未点名,**暂未动**,待示下。

#### kimi 三发 01 终态(2026-10-03 下午收账;02 mcar×kimi rep3 仍在 stage 1)
- **01 TDC×kimi(072253):门槛拒——溯源字段写错**。交付物齐全且框架阶段审计离线复跑通过(2 个实验、选中 pcnn_etr_v1、1,685 条预测、3 条论文数字可溯),但 trace 的 `framework_internal_model='PCNN-ETR'`、`framework_internal_api_base_url='local'`——kimi 把两个字段理解成"实验里用的模型/本地",而 `tdc01-model-fact` 已把字面值(Kimi-K2.6 / relay URL)追加进 run-local brief(日志确认触发)。宿主判 "framework_internal_model does not match the injected model",未评分。这是 kimi 第三次溯源失实(ARC "gpt-4"、mcar "api.openai.com"、TDC "PCNN-ETR/local"),且本次是在事实已披露的情况下——模型侧失败,计入尝试。调研 329 轮占去一小时,09:16 才交付。
- **01 ARC×kimi(072256):超时被杀(137)**,旧 2h 墙钟(发射于墙钟对齐前,用户决定不重发);被杀时仍在写估计器代码,无任何交付物。残留内层沙箱已按精确名清除。
- **01 BabyLM×kimi(072259):状态 finished,但 score.json 的 ppl 1.0314 是无效度量,不入表**。取证:该值来自最早一次评估 `results.json`(loss 0.0309)——数据集把每行 pad 到 128,而损失 `F.cross_entropy(..., reduction='mean')` 未忽略 padding,padding 位主导了平均损失。agent 随后自己写了 "Fixed perplexity computation (only non-padding tokens)" 的 v2/v3,得到 baseline 68.08 / v2 65.16 / v3 64.21(见 project 下 results_*.json 与 experiment_trace_final.json),但根目录最终 `experiment_trace.json` 与报告只记了那条过期的 1.03。即便修正后的 64-68 也不可与他格直接比:词表仅 5,000(大量 UNK)、验证只取 50 个 batch。
  - **1.03 不是编造的数,是"过期交付物"**(时间线取证):08:50:07 第一版脚本同时写出 `project/results.json` 与工作区根的规范名 `experiment_trace.json`(1.03,真实计算、度量有 bug)→ 08:56 起 agent 自行修正,新结果全部写进 `project/` 下的**非规范文件名**(`experiment_trace_v2/_baseline/_v3.json`,09:19:51 汇总为 `experiment_trace_final.json`:68.08/65.16/64.21)→ 09:20:09 agent 调 `case_resolved` 结束,从未回写根目录那份规范名 trace → 09:20:16 交付地图按规范名取走过期的 1.03。此外 agent 退出时未写 `research_idea.json` 与 `final_report.md`,由 wrapper 的 exit-delivery 步骤调用框架模型在 09:20:28/09:20:43 事后补出——报告因此是围绕那份过期 trace 写的("hypothesis not recovered")。宿主不替换框架交付物,故官方记录仍是 1.03(无效),框架自己的最终对比值 64.21 仅作脚注。
- **系统性提示**:01 BabyLM 的宿主评分是 `source: framework_experiment_trace`——**直接采信框架自报值,没有宿主侧复算**(02 侧由参考模块在固定验证行上计算)。01 该行已入表的 742.97 / 106.58 / 577.24 同样是未经独立验证的自报值,词表/分词/验证子集口径均未受约束。是否给 01 BabyLM 加宿主侧复算或口径约束,待用户裁决。
- **用户裁决(2026-10-03):01 不改。** 核实:01 与 02 读的是同一份 `automation/babylm_contract.md`(契约内无固定验证集、无官方验证函数,明文要求框架自行切分);02 之所以可信,是因为契约之外单独拿到了参考模块(`--add_dataset_ref`)和生成器 `render_ai_scientist_topic` 里的专属句子——偏离共用契约的是 02(已标为诊断路线),不是 01。参考模块的用途是解决"模型自造数据/自算指标"的可信度问题。03-07 由团队其他成员负责,其 BabyLM 口径未知;未与团队对齐前不单方面改 01,以免 01 偏离七框架共用的尺子。此类改动应作为契约级提案七框架同改。
- 落实(不动 01 的输入与评分路径):kimi 格的 score.json 1.03 原样保留为运行记录,表内标"自报值无效(度量 bug;框架自行修正值为 64-68),不参与比较";01 BabyLM 整行加脚注"共用契约下的框架自报值,验证口径由各框架自定;02 该行为诊断路线、使用宿主固定验证集,二者不是同一个量"。待与团队对齐的问题:03-07 的 BabyLM 分数是否同为自报;是否把固定验证函数升为契约内容。
- 表格:01 TDC kimi → 拒(溯源);01 ARC kimi → 超时(旧墙钟);01 BabyLM kimi → 无效分数(度量 bug)。
- **02 mcar×kimi rep3(`control_e2emcar_rep3_mcar02_kimi_20261003_072307`,07:23→15:22):失败(native=1 assembly=4)**。完整的一次真实尝试,无 API 报错(429=0)。stage 1 跑满 20 个节点 0 good、0 条官方记录:ModuleNotFoundError 2、NameError 2、TypeError 2、UnboundLocalError 1、RuntimeError 1,其余 12 个无异常但被判 buggy(判官意见集中在"训练完全不学习,评估回报始终≈0"和文件语法错误);7/20 个节点的代码调用了 `official_evaluation`,但没有一个真正跑出官方评估结果。装配在新 ≥1 下限下放行(1 个 stage selection)并执行回放,回放 0 条官方评估 → exit 4——首次由"官方记录缺失"这一真实原因而非下限判负。02 mcar×kimi 计两次真实尝试(rep1、rep3)均失败;rep2 为用户取消、rep3 前两次发射为配置/额度/上游 429 中止,不计。

#### kimi 四格尝试计数(用户 2026-10-03 定:今日这轮记为第 1 次尝试,16:00 发第 2 次)
| 格子 | 第 1 次尝试(今日 07:22 发射) | 第 2 次尝试(今日 16:00 发射) |
|---|---|---|
| 01 TDC×kimi | `…072253`:门槛拒(溯源字段写成 PCNN-ETR/local) | `fullrun_tdc_01_kimi_20261003_160040` |
| 01 ARC×kimi | `…072256`:超时 137(旧 2h 墙钟),无交付物 | `fullrun_arc_01_kimi_20261003_160043`(24h 墙钟) |
| 01 BabyLM×kimi | `…072259`:分数无效(交付过期 trace 1.03) | `fullrun_babylm_01_kimi_20261003_160046`(GPU 2) |
| 02 mcar×kimi | rep3 `…072307`:失败(20 节点 0 官方记录) | rep4(`launch_e2emcar_kimi_4.nohup`) |

- **16:22 用户调整(第 2 次尝试重排)**:24h 跑 01 不可控 → 01 ARC 墙钟改 **6h**(b08134a,`AI_RESEARCHER_ARC_TIMEOUT_SECONDS` 默认 21600);BabyLM 不加上限(保持无墙钟);TDC 维持契约 7000s 未动、继续跑(`…160040`);02 mcar×kimi 取消不重发。16:00 那批的 ARC `…160043`、BabyLM `…160046`、02 mcar rep4 `…160054` 均为用户取消(不计尝试;ARC/BabyLM 以容器内 TERM 收尾,02 以 launcher 的 docker stop 路径收尾,ARC 残留内层沙箱按精确名清除)。**第 2 次尝试的现行 run:01 TDC `…160040`、01 ARC `fullrun_arc_01_kimi_20261003_162459`(6h)、01 BabyLM `fullrun_babylm_01_kimi_20261003_162502`(GPU 2);02 mcar×kimi 暂无第 2 次。** 注:psydef / mcar 的 01 wrapper 默认墙钟仍为今晨改的 24h,未随 ARC 一并改。
- 不计入尝试的历史发射:09-28 额度墙、10-02 上游 429 被停、各次发射配置中止;更早的真实失败(ARC×kimi 两发、02 mcar×kimi rep1)属协议开始前的历史,单独留档。
- **第 2 次尝试的补丁栈与第 1 次不同**(用户当日清理所致,非同条件复跑):已无预算时钟、已无 exit-delivery(BabyLM/ARC 不再有事后补写,agent 不自己写 idea/报告即记缺失)、ARC 墙钟 2h→24h;context hygiene 本就未生效。核验:TDC 容器 32 核且无预算时钟变量、model-fact 触发;ARC 外层 `timeout 86400s` 且日志无已删补丁字样;BabyLM 内层 GPU=[2]/16 核;02 mcar rep4 ideation 正常。发射前 Kimi 线路探测 6/6 正常。

#### 补丁清理台账(2026-10-03 起,用户逐个梳理)
| 补丁 | 处置 | 依据 |
|---|---|---|
| `ai_scientist_v2/exit_delivery_check.py` | **删除**(e784c3b):文件 + 01 BabyLM/ARC 调用块 + 01 mcar 与三个正式 02 wrapper 入口清单条目 + 两处已注释调用 | grill Q6⑤ 否定;02 侧 09-17/18 已禁用,01 侧漏关 |
| `ai_researcher/patch_context_hygiene.py` | **删除**:文件 + 01 ARC wrapper 三处接线(复制、开关块、env 透传) | 09-01 加入当天即改为 opt-in(f6ef98d);全仓仅 ARC 一处接线且默认关;无任何发射脚本/.env 置 1;历史上只在一发 cancelled 的 09-01 kimi ARC 试验里生效过,无入表格子依赖;问题已由堵灌水源的 `patch_idea_loop_fixes` + `patch_file_browser_paging` 在源头解决,且该补丁会改变 agent 可见的对话历史(开/关不可比) |

| `ai_researcher/patch_budget_clock.py` | **删除**(用户决定"先去掉,既有结果不必计较"):文件 + 五个 01 wrapper 的调用、入口清单/复制行、`AI_RESEARCHER_TOTAL_BUDGET_SECONDS` 环境变量注入 | 它向 agent 提示词里加"总预算声明 + 先估算命令耗时"的建议,并给 execute_command/run_python 结果加 `[clock]` 行——属于宿主写给 agent 的信息。无其他补丁依赖它(`patch_resource_visibility` 的锚点是框架原文;该环境变量只有它读)。删除后健康检查 105 项全过。此前所有 01 运行均带此补丁,新发射起不再带 |
| `ai_scientist_v2/patch_worker_future_headroom.py` | **暂不处理**(用户) | 从未接线(4a83595 "add unwired");但所治症状(父进程先于子进程超时、节点以 "Worker process timed out" 无声丢失)在 02 运行中持续出现(BabyLM×kimi rep1 26/29) |

#### exit-delivery(退出时让框架模型补写缺失交付物)核查与关闭(2026-10-03)
- 用户指出该机制应已被否定。核查:`real_eval/adapters/ai_scientist_v2/exit_delivery_check.py`(08-28 为 02 而写,09-02/09-03 以"验收层"接入 01)在 01 BabyLM 与 01 ARC 两个 wrapper 中**默认开启**(`AI_RESEARCHER_EXIT_DELIVERY_CHECK:-1`);脚本自述也写明"judgment call … should be ratified"。09-27 grill 决策 Q6 第⑤条"不替框架写叙述(报告、论文),不补填框架未给的字段"已否定此类做法,但当时"实现动作待确认后再做",开关一直没关——决定与代码脱节。
- 影响面(逐 run 查 `logs/exit_delivery_check.log`):**01 BabyLM 每一个 finished 的运行**都由它在运行结束后补写了 `research_idea.json` 与 `final_report.md`——luna 742.97(09-03)、ds 106.58(09-07)、g6 rep2 2429.9、g6 rep3 577.24、kimi 1.03;困惑度本身来自 agent 自己写的 `experiment_trace.json`(finished 运行中 trace 未被补写)。01 ARC 调用过但所有运行补写 0 个文件(0.0886 / 0.142 不依赖它)。01 mcar / TDC / psydef 不调用。
- 处置:两个 wrapper 的默认值改为 **0**(7944eec,保留开关仅供诊断)。此后 01 BabyLM 若 agent 不自己写 idea/报告,将如实记为交付物缺失。已入表的 01 BabyLM 各格:分数(trace)为框架原生,但 "idea 先于实验锁定" 与 "框架撰写的最终报告" 两项系事后补写,不满足 Q6⑤——是否重跑或加脚注待用户定。

#### 01 墙钟对齐 02(2026-10-03 晨,落实 09-27 "统一 24h/32 核" 的墙钟那一半)
- 盘点:02 五个 launcher 均 `RUN_TIMEOUT=86400`;01 原为 psydef 7200s、ARC 7200s、mcar 7000s(仅我们手动发射时覆盖为 86400)、TDC 硬编码 7000s、BabyLM 无墙钟。09-27 只定了方向"暂不改",10-02 只落实了 CPU 一半。
- 改动(wrapper 层):psydef / ARC / mcar 的原生墙钟默认值 → **86400**(同时驱动 agent 可见的 budget clock);共享 runner 内无先于 wrapper 生效的外层墙钟。
- **TDC 不改**:其契约明文 "3,600 s 累计实验时长 + 7,200 s 总墙钟"([tdc_admet_tox_contract.md:80](automation/tdc_admet_tox_contract.md#L80)),校验器对两框架一视同仁地硬性检查(`total_wall_seconds<=7200`、累计实验 `<=3600`;02 装配把 native 墙钟+回放时长计入 total_wall),01 的 `timeout 7000s` 与之自洽;02 launcher 的 24h 对 TDC 只是外层保险。要给 TDC 24h 须改契约/生成器/校验器(共享层 + topic 定义),未动。
- 在飞影响:01 ARC×kimi 072256 发射于改动前,仍是 7200s(约 09:23 到点);TDC×kimi 7000s 属契约内。

#### 10-02 夜间两发终态(2026-10-03 晨收账)
- **01 TDC×ds(`fullrun_tdc_01_ds_20261002_145722`,paratera,新预算 32 核):端到端通过,隐藏标签 main_score 0.7134**(AMES 0.7681 / hERG 0.6533 / DILI 0.7187)。14:57→16:52 墙钟内完赛,零 4xx/5xx、零 keepalive/idle 触发;调研 115 轮 + ML 207 轮;3 个实验(RandomForest+Morgan 指纹 验证 0.795 被选中、GATv2+GIN 0.603、LogisticRegression 0.696),trace 模型字面值正确。01 TDC×ds 首次出分,也是新预算与 paratera 下第一个完整 01 结果。
- **01 BabyLM×g6 rep3(`fullrun_babylm_01_g6luna_20261002_140521`,paratera,GPU 6,旧预算沙箱 8 核):完赛,词级验证 ppl 577.24**——2 个实验(baseline lookup embeddings 617.24 → compositional rare-token embeddings 577.24),无容器丢失、无工作区异常、case_resolved,报告齐全;仅开头 2 次 502。**取代 rep2 的伤残 2429.9 入表**。
- 表格更新:01 TDC ds **0.7134**;01 BabyLM g6 **577.24**。
- **kimi 四格重发(2026-10-03 07:22,paratera Kimi-K2.6 线路恢复:晨间探测 4/4 正常;用户批准,BabyLM 指定 GPU 2)**:01 TDC×kimi `fullrun_tdc_01_kimi_20261003_072253`(容器 NanoCpus=32)、01 ARC×kimi `fullrun_arc_01_kimi_20261003_072256`、01 BabyLM×kimi `fullrun_babylm_01_kimi_20261003_072259`(内层沙箱 GPU=[2]、NanoCpus=16——新预算首次在 BabyLM 生效)、02 mcar×kimi rep3(`launch_e2emcar_kimi_3d.nohup`,ideation 正常)。全部新预算、冻结副本、watcher 齐挂。GPT-5.6-Luna 在 paratera 仍 503。

#### 中转站切换:bianxie → paratera(2026-10-02)
- 新站 = 并行科技(用户称 bingxing),**API base URL = `https://llmapi.paratera.com/v1`**(`ai.paratera.com` 为门户;`/v1` 无 key 401、带 key 200,118 模型)。
- **模型 ID 大小写严格**(小写 400 "no healthy deployments"):`GPT-5.6-Luna` / `GPT-6-Luna` / `DeepSeek-V4-Flash` / `Kimi-K2.6`。
- 行为探测(与 bianxie 对照):GPT-6-Luna 的 bare tools、tools+tool_choice、reasoning_effort=low **全部 200**——bianxie 的两个怪癖(reasoning_effort 拒、tool_choice-无-tools 拒)在 paratera 不存在,两个 fallback 适配器保留但预期静默。GPT-5.6-Luna 探测日 **503"无可用上游线路"**(部署可用性,非策略;luna 列暂无待发任务,挂起观察)。
- 已切换:`.env`(base_url/key/model;旧 bianxie url+key 注释备份,沿用 gpt5.4 旧例)、4×`my_provider_*.toml`(base_url+模型精确大小写+档案名 bianxie→paratera)、scratchpad 两个 provider env(g6/kimi,全 10 变量)。**明确不切**:两个 adjudicate 脚本内的 bianxie 常量(历史运行溯源期望值)与 gpt5.4 遗留脚本。
- 运营注记:切换操作中旧 bianxie key 在一次会话输出中暴露(验证 grep 漏滤注释行),已建议用户在 bianxie 后台作废旧 key。paratera 的账单/用量查询端点未知,spend 监控暂停待查。模型 ID 变更对评测连续性的影响 = 列仍按底层模型对齐,trace 的 model-fact 注入值自动跟随 env;切换日期以本条为界。下次任何 fullrun 前按 AGENTS.md 先走阻塞 smoke。
- **09-28 午间批量重发(用户指令)**:01 TDC×ds(`fullrun_tdc_01_ds_20260928_115228`)、01 TDC×kimi(115231)、01 ARC×kimi(115234,第 3 发)、01 BabyLM×kimi(115255,**改走现代 real_babylm wrapper + 全适配链,GPU 5**;旧 kimi wrapper 无 adapter 机制不再使用)、02 BabyLM×g6 rep2(`control_e2ebabylm_rep2_..._120606`,**GPU 4**,与 rep1 同配置纯第 2 发)。全部冻结副本发射、独立 run id、watcher+完成标记齐挂。TDC 两发携带新 `tdc01-model-fact` 块;同时段在飞:01 mcar×g6 rep2(带 `mcar01-model-fact`)、01 babylm×g6 rep2。
