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
