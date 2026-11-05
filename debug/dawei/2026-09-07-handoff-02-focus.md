# 交付文档：当前进度与聚焦问题（2026-09-07）

聚焦 02 (AI-Scientist-v2) 的根因诊断；附 01 两个尚未解决的失败原因。
配套：`2026-09-07-01-scoreboard.md`（01 结果表）、`2026-09-07-campaign-chronicle.md`（127 提交编年）。

---

## 一、02 (AI-Scientist-v2)：主攻方向

### 现状：全 topic 零出分
- ARC 18 run 全 fail、psydef 3 run 全 fail、tdc 3 run 全 fail（均 08-25~08-29，之后一直在做 01，02 久未跑）。

### 根因（已逐层核实，代码+run 双证）：ideation 从 system prompt 层就把每个 topic 重铸成"开放研究命题"
数据流：`perform_ideation_temp_free.py`（ideation，5 轮 reflection 迭代）→ idea.json → `launch_scientist_bfts.py`（BFTS 四阶段）→ 产物。

1. **主因 · ideation 的 prompt 组装**（`perform_ideation_temp_free.py`）
   - system_prompt(:61) 硬编码：*"You are an experienced AI researcher who aims to propose **high-impact research ideas resembling exciting grant proposals**... be **creative**, **novel**... papers **publishable at top ML conferences**."*
   - user prompt(:99)：`{workshop_description}` + *"Begin by generating an interestingly new **high-level research proposal**"*
   - → ideation agent 被双重定义为"研究提案生成器"。**这是框架灵魂,改它=篡改被测对象（越界）。**

2. **跨 topic 复现（证明是框架级,非某 topic 配置）**
   - ARC idea 灵魂：*"Adaptive Probe Consensus: Estimating ARC White-Box Scores..."*（自造研究命题）
   - psydef idea 灵魂：*"Does a Defense Mechanism Reside in the Utterance or in Its Conversational Geometry?"*（研究问句）
   - 两者都不是"实现一个交付物"的工程任务。

3. **reflection 迭代固化跑偏**：5 轮 reflection 的 prompt 明确 *"Stick to the spirit of the original idea"* + 提升 novelty → 初稿一旦跑偏,迭代只会打磨得更精致,不纠偏。

4. **BFTS 承接研究灵魂 → 产研究脚本**
   - 四阶段：`1 initial_implementation(preliminary,goal 明确写"Use a simple dataset")→ 2 baseline_tuning → 3 creative_research → 4 ablation_studies`。
   - ARC run 154034 实证：BFTS 训练在 **1200×8 合成玩具数据**上,产 `best_solution_<hash>.py`（logs 深层）——**从不读真实 MLP 权重,从不产 4 个契约文件**。
   - 注意 stage_1 的设计本意就是"用简单数据先跑通"——**在 stage_1 硬塞契约规格会与阶段语义冲突**（用户判断,已采纳）。

5. **规格投递现状（澄清"是否已注入"）**：**已注入,但性质不对**
   - wrapper 76 行 inline PY 把 handoff contract 追加进 ideation 的 **system_prompt**；50ef542 又把契约追加进 BFTS 读取的 **idea["Experiments"]**（只有 stage 3 经 `_curate_task_desc` 拼进任务描述）。
   - 但注入的是"交付格式清单",不是"任务性质定义",且被"研究提案"定位+"host does not prescribe..."对冲 → 盖不过已成型的研究灵魂。

### 交付物鸿沟（决定修法上限,已实证）
BFTS 结束留下的材料：
- ✅ 有：每节点 code、journal.json（7 节点，含 metric/plan）、experiment_data.npy、曲线图 → **够拼 experiment_trace.json + final_report.md**
- ❌ 无：`estimator.py`（journal 里的 code 是研究脚本，无 predict(mlp)->(32,256) 接口、不读真实数据）；`submission.json`（需真实测试集预测，BFTS 从没碰真实数据）
- → **交付桥能补格式类文件（trace/report），补不出实质产物（estimator/submission）**——验收层不能编造（铁律）。

### 已做的修复
- `patch_ideation_task_framing.py`（提交 1fa852f）：**按用户决定收窄为单一事实修正**——蓝本 `arc_wbe_2026_topic.md` 的 estimator.py 从 "when possible" → "a runnable estimator.py implementing predict(mlp)->(32,256) over real /data/arc_wbe_2026"。**只陈述交付物是什么,不框定模型认知**（去掉了初版的 "not an open research question / concrete task" 等越界措辞）。已接入 02 ARC wrapper（ideation 前 apply）。
- 定位：这是最弱的杠杆（蓝本只是被"请提研究提案"指令包裹的一段描述），**不指望它单独扭转,需实测**。

### 未决 / 下一步（按优先级）
1. **交付桥/验收层（用户定：绝对必做）**——BFTS 后从 run 材料生成 trace/report，把成熟阶段 best_solution 尽力转 estimator（缺实质则诚实记 0，不编造）。02 已有 `exit_delivery_check.py`，需确认覆盖 ARC 5 文件 + 接线。
2. **实测蓝本改动1 的效果**——跑一次 02 ARC，看 idea.json 灵魂被扭动多少（需 provider + S2，ideation 30min + BFTS 1h）。
3. **psydef 02 死在 stage_1 的具体原因**未查——判断"02 是卡范式（没救）还是卡具体 bug（可推进到交付桥）"。
4. **开放判断**：02 是"研究框架 vs 实现任务"的范式错配。能改的只有蓝本（已到上限）；system_prompt 是框架灵魂不能动。交付桥是范式错配下唯一能提取部分价值的环节。

---

## 二、01 (AI-Researcher)：两个尚未解决的失败

### kimi × ARC（六发全 fail，最终 killed）
死因是**一串逐个暴露、逐个修复的放大器**，最后落在模型侧：
- 已修（框架放大器，本轮全部验证不再触发）：幽灵里程碑（e913095）、翻页风暴（54dd739：read_file 缺文件被套翻页外壳→kimi 翻 160 次同一句 cat 报错）、logger 崩全场（71bb82f）、tool args 解析崩（55d9916：畸形 JSON 参数杀全场→改为反弹重试）、上下文爆 270k（翻页下游，随 paging 修复缓解）。
- **末发（151115）真死因（模型侧,未修）**：kimi 在 ML 阶段**任务误读**——以为要调 LLM API，系统性搜刮容器凭证（`env|grep OPENAI_API_KEY`、`cat /proc/self/environ`、`find / | xargs grep API_KEY`），既跑偏又发了病态全盘 find → 触发 `run_command` 的 **pipe_read 挂起**（子进程亡但管道未闭、socket 读循环无超时，继 read_file 之后第二个无超时挂起点）→ 卡死 36min → killed。
- 定性：框架侧已清干净；剩余是 kimi 的任务理解偏差 + 一个未修的 run_command pipe_read 挂起点。

### DS × TDC（两发 fail）
研究能力够（validation macro-AUROC **0.6943**，超 luna 的 0.6311），但两次都没进 host 官方评分：
- 首发（113557）：训练**跑完了**、predictions.csv 在正确位置，但 host 审计 `experiments must be a list`——trace 格式不合 schema（规格已送达 docs/*requirements.md+已挂载，是 DS 没遵循，非未告知）。→ 已上校验器反弹（2a1667f：case_resolved 时跑官方校验器，不合格带原话弹回）。
- 重发（140533）：加了 `--fast` 但训练规模仍超 4 核预算,78min 未返回撞墙钟 → `failed_native_research`，没到收尾（校验器反弹没机会上场）。
- 定性：**资源声明送达改变了行为（加 --fast）,但改不了规模估算的能力短板**——DS 在 TDC 的真实边界；校验器反弹待"训练能在预算内跑完"的一发才验证。

---

## 三、其他状态
- gpt-5.4：**确认不可用**（dts.deepexi.com 的 gpt-5.4 上游持续 503，单模型通道问题；同 key 的 5.5/5.6/5.4-mini 正常）。
- mcar：luna 交付接口不全（缺 helpers/config，与 checkpoint 不配套），其余模型未跑。
- 悬账（未修，有档案可回放）：环形/非连续重复护栏（kimi ARC 周期循环、DS babylm review 翻页）、占位参数护栏（wire_tap 蹲守根因）、run_command pipe_read 挂起点。
- 全部 run 进程已清理；patch_healthcheck.py（scratchpad）基线 92 OK / 0 FAIL。
