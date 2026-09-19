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
