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
