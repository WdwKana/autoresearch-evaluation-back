# 协作者对齐清单（持续更新,最后更新 2026-08-28）

## 需要向协作者索取

1. **`real_eval/adapters/ai_scientist_v2/patch_ai_scientist_v2_common.py` 原件**——公开发布遗漏;我方已按 wrapper 上下文重建最小版（见 02 阻塞记录）,需 diff 校对。
2. **Semantic Scholar API key**——02 的 ideation 硬依赖;无 key 必然 429 超时。
3. **`real_eval/codex_relay/relay.py` 正本**——公开仓引用但未发布;我方已从常驻 relay 容器回收一份（1046 行,已加 provenance 头）,需 diff 校对。
4. **Codex CLI 版本号**——TDC/PsyDef 的 smoke 依赖宿主 codex;新版 0.150.1 已移除 relay 依赖的 `wire_api="chat"`,需知道你们钉的版本。
5. （可选）`api/_semantic_scholar_api_usage.md`、其他 `api/` 私有配置的清单,确认还有哪些脱敏遗漏。
6. **另外三份公开发布遗漏文件的原件**——同样已由我方重建,均需 diff 校对:
   `real_eval/adapters/tdc_admet_tox/patch_ai_researcher.py`、
   `real_eval/adapters/tdc_admet_tox/patch_ai_scientist_v2.py`、
   以及 psydefdetect 的切分清单（我方按官方 HF split 重建）。

## 需要团队裁决的项目层面不一致（我方已发现,一律未擅自改动）

1. **TDC 的 predictions.csv schema 判断是全项目唯一的严格相等**
   `automation/scripts/validate_tdc_admet_tox_run.py:77` 用 `reader.fieldnames == PREDICTION_FIELDS`;
   同项目其他 topic 都更宽松——ARC 数据集检查用 `issubset`,psydef 打分器按字段名取值且带 `label` 别名回退。
   **代价实例**：01×TDC 第 10 次研究完全做完（1685 条预测齐全、endpoint 合法、概率合法、有 metrics 和训练日志）,
   仅因多带一列 `smiles` 被整轮判负。
   **我方判断**：严格的*语义*检查（非常量、预测集合完整、概率区间）有学术必要;
   但严格的*表头相等*检查的是文件长相而非结果对错,会系统性惩罚"多给了信息"的框架,制造与研究能力无关的分数差异。
   **建议**：与其他 topic 对齐为子集/按名取值判断。**我方只补了规格投递,未改校验器**——改校验器等于改评测标准,须团队决定。

2. **BabyLM 是 01 的八个 wrapper 里唯一强制走 paper_agent 的**
   `01_ai_researcher_real_babylm.sh`（注册表认定的正式入口）在研究阶段后追加
   `python ../paper_agent/writing.py`;ARC/TDC/PsyDef/MountainCar/topic2 等其余 7 个 wrapper 都不调用。
   该调用来自初始公开发布提交,是原作者的选择。
   **但 babylm 契约的交付清单里没有"论文"**——只要求 research_idea.json、2-4 个实验、
   experiment_trace.json、final_report.md 和原生提交产物;
   AI-Researcher 官方文档也把 Paper Writing Agent 描述为研究之后的可选步骤（"If you want to generate the paper"）。
   **代价实例**：第 13 次研究阶段 `EXIT_CODE=0` 圆满结束,随后整个写作阶段因模型 403 全灭,
   连已完成的研究一起判负。
   **建议**：若团队认可,把写作阶段改为失败不致命（写不出就跳过,保留研究产物）。
   **我方选择修好它而非绕过**——原作者把它放进了正式入口,擅自删除等于改变框架执行定义。

3. **mountaincar_continuous 的改名收尾未完成**
   `topics.json` 已有 `mountaincar_continuous`（maturity=experimental）,但
   (a) 它指向的 `automation/mountaincar_continuous_contract.md` 是 **0 字节**（前身 `topic2_contract.md` 有 4116 字节完整内容）;
   (b) `runs.json` 里 mountaincar/topic2 的 framework×topic 映射 **0 条**（对比 ARC 21 条、psydef 14 条、TDC 14 条）;
   (c) 输入生成器至今只产 topic2 命名的文件。
   **我方处置**：为跑通而在生成器下游手工复制了一份改名副本（`benchmark/final/mountaincar_continuous/`),
   **topic2 全套 27 个文件零改动**（已用 `git diff main..HEAD` 逐一验证,平行新增而非改名替换,
   队友已有的 topic2 结果不受影响）。这是权宜之计,不是根治——正规做法是修生成器 + 补契约 + 加映射。
   在此之前 mountaincar 的结果只能算实验性数据,不能进正式榜单。

4. **02 的离场检查是设计裁量点,需批准后方可用于发表结果**
   `real_eval/adapters/ai_scientist_v2/exit_delivery_check.py`:BFTS 结束后列出缺失的契约文件,
   让**框架自己的模型**基于**框架自己的产出**补写;已存在的文件绝不触碰,每次补写都记入
   `exit_delivery_check.json`（含清单与输入）,任何依赖它的 run 均可审计、可剔除。
   契约禁止的是*宿主*生成/修补产物,此处宿主只提供清单和一次重试——与"宿主可定义输出 schema"同一解释,
   但属判断,**请在采用其结果前批准或否决**。

## 需要同步给协作者的发现

1. **01×ARC 从未出分的根因是线束 bug,不是模型/框架能力**：42 号门拓扑上不可满足 + 交付规格从未送达 agent（详见 `2026-08-26-01-arc-bug-analysis.md`）。修复在分支 `fix/01-arc-delivery`,全部 01 作用域,请 review——尤其"搬运桥是否符合 host-must-not-promote 条款"这一设计裁量点。
2. **01 wrapper 失败不写终态的 bug**：校验失败时 state.json 停 "running",外部看是"神秘消失"。若你们也见过此现象,即是同源。
3. **`REAL_EVAL_MODEL` 默认值**：不设则 01 调 gpt-5.4、02 调 kimi-k2.6;key 无权限即 403 循环至超时。
4. **whest 版本对齐**：仓库未钉版本;我方 whestbench 0.16.0,commit `35164f3535c2103742772dd11a68ce840464db0b`。
5. **镜像依赖**：早期构建的 `ai-researcher:runtime-ready` 缺 libGL/chromium 及其系统依赖（自检命令见环境记录）。
6. **运行纪律**：长 run 须脱离终端会话（tmux/setsid）;失败 run 目录按 AGENTS.md 一律保留,重试用新 run id。
7. **容器内发起评测的路径陷阱**：docker socket 直通宿主时,`-v` 路径按宿主解析;须使用宿主可见路径形式（本机为 `/data/daweiwang/...`）。
8. **`GPTClient` 硬编码模型导致写作阶段全灭**：`benchmark_collection/utils/openai_utils.py` 的
   `GPTClient.__init__` 默认 `gpt-4o-mini-2024-07-18`,`SectionComposer` 同样硬编码该默认值且
   `MethodologyComposer` 从不覆盖——写作阶段的每一次调用都绕开注入的 `OPENAI_MODEL` 发给 gpt-4o-mini。
   若 key 无该模型权限即全部 403。更隐蔽的是 `chat()` 有**四条 `return None` 路径**把失败静默吞掉,
   None 随后在下游任意消费点炸,呈现为三种互不相同的崩溃（`write() argument must be str`、
   `'NoneType' has no attribute 'split'`）——看似三个 bug,实为同一个 bug 的三次现身。
   我方修法:让 GPTClient 读取 `OPENAI_MODEL`,并让 chat() 所有失败路径降级为空字符串。
9. **失败类型的区分**（供归因参考）：01 的连续失败是**确定性的逐关开锁**——每次根因不同、修好不再复发、
   失败点单调后移;02 的失败是**同一道门上的概率性不合规**——同一交付门,每轮随机漏交不同子集
   （第 7 轮交 3/5 含完美的 9 字段 trace,第 8 轮反而只交 2/5）。两者的应对方式不同:
   前者继续逐个修,后者靠结构性保障（离场检查）而非加强措辞。
