# 02（AI-Scientist-v2）专属修订台账（截至 2026-09-24）

目的：把我们为 02 做过的每一处修订按类别记清楚，最后再逐条讨论哪些该合并进正式路线、哪些只是诊断工具、哪些该撤。
本表只记"针对 02 做的事"，不评价对错。每条给出：改了什么、为什么、目前是否进入了出分运行、合并意见（待议）。

## A. 任务渲染（02 专属句子；改在 automation/scripts/generate_*_native_inputs.py 的 AI-Scientist-v2 渲染函数里，不影响其他框架的输入）

| # | 提交 | 话题 | 加了什么 | 为什么 | 进入出分运行 |
|---|---|---|---|---|---|
| A1 | 4824615（09-21） | BabyLM | 域名列表从磁盘读取，替换写死的错列表 | 节点按错列表拼路径失败后退化成合成数据 | 是（luna 108.11） |
| A2 | 89be78d（09-24） | BabyLM | "结果定义句"：只有参考验证函数在固定验证行上报的困惑度才是本任务结果 | 节点自算指标绕过官方验证；判官需要一条可引用的规则 | 是（luna 108.11） |
| A3 | 3d94b0c（09-24） | MountainCar | "结果定义句"：只有参考 `official_evaluation`（冻结 evaluate.py，恰好五个 checkpoint）报的 Reward Mean 才是本任务结果 | 同 A2；rep 1 0/20 全绕过冻结评分 | rep 2 在跑 |
| A4 | b524243（09-21） | ARC | 主题正文加"结果只定义在提供的记录上；参与者自造网络上的数字不是本任务结果"（scratchpad `staged/arc/arc_wbe_2026_native_v2.md`，快照在 debug/dawei/ladder/staged/arc/） | 节点自造小 MLP 训练评估 | 是（luna 0.0988） |
| A5 | 本次（09-24） | psydef / TDC / BabyLM / MountainCar | "仅在提供的数据上做实验；合成、玩具、自造数据上得到的结果不是本任务结果"，四个话题措辞一致，放在 Dataset / Inputs 一节；ARC 已由 A4 覆盖 | 02 自身 stage-1 目标写着 `Use a simple dataset`、设计指引写着 `create synthetic data if needed`；01 的提示词原生写着 `MUST use actual dataset (no toy data)`，02 缺这句 | 尚未（等在跑的结束后再决定重跑哪几格） |
| A6 | 本次（09-27） | 全部五个话题 | 参考模块 docstring 加两句：结果只定义在提供的数据/环境上，合成、玩具、自造数据上的数字不是本任务结果、不能被选择或提交；本模块可直接 `from hf_dataset_reference import <官方函数>`，请 import 而不是粘贴或重写，只有本模块写出的文件才是官方记录 | judge/coder 在每个 stage 看到的 task_desc 只有 idea JSON + 参考模块源码，主题 md 从不进入 stage；A2/A3/A5 的句子只能靠 ideation 吸收（DS/kimi 六份 idea 0 次吸收，luna 5 次）。参考模块源码是唯一稳定到达 judge 的通道 | 尚未（MountainCar ds/kimi rep 1 在此之前发出，用的是旧 docstring） |

作用域证明（A5）：改前改后各生成一次全部框架输入（90 个文件），diff 只有 6 个 AI-Scientist-v2 话题文件不同（babylm/mcar 各含 my_research_topic.md 同名副本）。

## B. 运行时适配器（real_eval/adapters/ai_scientist_v2/，改的是框架代码在容器内的行为）

| # | 文件 / 提交 | 做了什么 | 为什么 | 性质 |
|---|---|---|---|---|
| B1 | patch_ideation_action_format.py（2ed72da） | ideation 解析接受 markdown 装饰的 ACTION/ARGUMENTS 标签 | 模型回复带 `**ACTION**` 之类装饰 | 兼容 |
| B2 | patch_ideation_tolerant_parser.py（f910269） | 多代码块按序执行、忽略尾随散文、拆掉多套一层的 idea 包装 | DS / kimi 的回复形态 | 兼容 |
| B3 | ideation MAX_NUM_TOKENS 4096→16384（abf1a00）、ideation 存 0 个 idea 时重试 ×3（d8a97c6） | 防截断、防空 | 跟随维护者的 BabyLM/TDC wrapper 做法 | 兼容 |
| B4 | patch_semantic_scholar_bounded.py（b73c607、9a68ca4） | Semantic Scholar 请求加 socket 超时和有界退避 | 429 退避 400–500 s、一次读挂 17 分钟 | 稳定性 |
| B5 | patch_ai_scientist_v2_common.py（4457b1d） | provider 拒绝 function tools + reasoning_effort 时以 `reasoning_effort='none'` 重试；backend_openai 走同一 shim | worker 内不可 pickle 的 400 打崩进程池 | 兼容 |
| B6 | patch_worker_future_headroom.py（09-18） | worker future 余量 | TDC 单 worker 运行 | 稳定性 |
| B7 | patch_prompt_logging.py（32dc11e、0dede34） | 只记录：dump Memory 摘要与编译后的 draft/debug/improve 提示 | 诊断 | 仅日志 |
| B8 | patch_task_definition_taskdesc.py（2e99831，TRIAL） | 把官方任务定义塞进各 stage 的 task_desc | 试验，已叫停 | 应撤 |
| B9 | patch_bfts_delivery_contract.py / patch_native_finalization.py / arc_contract_finalization.py（09-17） | 交付契约挂到 BFTS 的每阶段输出流；finalization 从 idea 映射 | 早期交付桥思路，后被 75ef6f6 / 5428b62 "交付属于框架"撤掉 | 已撤或停用 |
| B10 | exit_delivery_check.py（09-03） | 退出时交付检查 | 已由 75ef6f6 移除 | 已撤 |

另：VLM 覆盖（DS 端点对图片返回空 → 只在看图步骤用 gpt-5.6-luna，ed6fb74）是发射器参数，不是适配器；它让 DS 的运行不再是"全角色同一模型"，评估口径上要单独标注。

## C. 规格臂路线工具（scratchpad `staged/`，快照在 debug/dawei/ladder/staged/；诊断路线，出分但不进正式计分板）

| # | 话题 | 参考模块（--add_dataset_ref，进入 task_desc 的 Code To Use） | 装配 / 校验 |
|---|---|---|---|
| C1 | psydef | `official_score(name, id_to_label)` | assemble_psydef.py、psydef_host_validate.py |
| C2 | TDC | v2 `official_evaluation(name, predict_fn)`：验证集打分 + 写测试预测 | assemble_tdc.py（取验证 AUROC 最高）+ 隐藏标签打分 |
| C3 | ARC | v2 `local_validation(name, estimator)`：AST 打包、numpy-only 子进程自测、`class Estimator(<X>)` 子类化 | assemble_arc.py（跳过 submittable:false）、arc_host_validate.py |
| C4 | BabyLM | v2 `official_validation(name, nll_fn)` 在模块内固定验证行上评估，记录带 `official: true` | assemble_babylm.py（只认 official 记录）、babylm_host_validate.py |
| C5 | MountainCar | v1 `official_evaluation(name, src_dir, checkpoints_dir)`：起始代码拷贝、冻结评估 | assemble_mountaincar.py（镜像内跑 evaluate.py）、mountaincar_host_validate.py |

发射器共同项：32 核（BabyLM 16）+ 线程上限、64 GiB、24 h 上限 + docker stop 看门狗、HF 离线、ideation 补丁 B1–B3、每阶段 20/6/6/2 迭代。

## D. 正式 02 wrapper（real_eval/scripts/02_*_fullrun.sh）的改动（09-17 至 09-19，规格臂之前）

| 提交 | 话题 | 改动 |
|---|---|---|
| e3b250a | psydef | 从判官可见的 task_desc 移除 host 契约（只给 coder 看） |
| 415190f、2827593 | psydef | 追踪 schema、预测行 schema、对话结构写进 coder 指引 |
| 7d40cb8、e99d905、c7f3c48、df00cc6 | TDC | coder-only 交付指引 + stage 1 截断；单 worker；wrapper 注释不得提别的话题；reproduce.py 事实 |
| c3eb6a3 | BabyLM | 套用 psydef 的教训 |

## 待讨论的合并问题（先不定）
1. A 类句子哪些是"任务定义"（应同步给全部框架的输入），哪些是"给 02 判官的规则"（只留在 02 渲染）。A5 的措辞对所有框架都成立，但 01 已自带同义句。
2. C 类参考模块是否成为 02 的正式路线（它替代了 D 类的 coder-only 交付指引 + stage 1 截断）。
3. B8–B10 正式删除。
4. VLM 覆盖在结果表里的标注方式。

## E. host 装配选择规则(2026-09-27 修订,用户同意)
- 之前:psydef / ARC 取最后一个 stage;TDC 取验证 AUROC 最高的 stage(luna 一发是 18 个配置里挑)、BabyLM 取困惑度最低、MountainCar 取官方 Reward Mean 最高——host 替框架做跨 stage 选择,违背"选择归框架"。
- 现在:TDC 以外的四个话题统一取"最后一个有官方记录的 stage"的 best_solution(框架链条终点),不做跨 stage 分数比较。节点内多个配置仍由 host 取官方分最好的一个(已在 trace 的 selection_rule / within_node_configuration 注明),是否给参考模块加"节点声明选定配置"接口待议。
- 对已有分数:psydef ×3、ARC luna、MountainCar luna 不变;BabyLM luna 按新规则为 stage 4 的 119.35(旧 108.11);TDC ×3 需按新规则重跑(不对另一份预测用隐藏标签打分)。
- BabyLM/MountainCar 装配脚本开头说明原从 ARC 复制(写着取最后一个 stage、estimator/whest),已改正。
- 更正(同日):TDC 撤回新规则。TDC 契约写明 select using validation evidence only,契约校验器 validate_tdc_admet_tox_run.py 要求 selection_metric=validation_macro_average_auroc 且选中项是 trace 中验证 AUROC 最高者;这条对所有框架(含 01)同样执行,所以 TDC 按验证分挑是契约规则,不是 host 越权。离线用新规则重装配的 TDC 包因此过不了框架阶段审计。TDC 三格原分数有效,不重跑。其余话题契约没有此类规则,保留"最后一个有官方记录的 stage"。
- 旁证:同一份 best_solution 离线回放,验证分与原运行不完全一致(ds stage 4 0.8271→0.8224,kimi stage 4 0.8153→0.8357),回放存在非确定性。
- 两发 TDC rep 3(control_e2etdcspec_rep3_tdc02_{luna,ds}_20260927_*)启动约 10 分钟后由操作者中止(用户要的是离线重装配,不是重跑),目录保留,state=aborted。
- 更正(同日,用户同意):BabyLM 也撤回"最后一个 stage"规则,改回取验证困惑度最低的实验。原因:BabyLM 的官方分数由 automation/scripts/run_babylm_score.py 给出,它不看 selected_experiment_id,直接取 trace 中所有实验的最低困惑度;01 与 02 都用它打分(01 luna 的 trace 甚至没写选中项,742.97 就是它取的最小值)。装配选择须与打分一致,否则提交的模型与被打分的实验不是同一个。02 BabyLM luna 维持 108.11(离线按最后 stage 重装配得 119.35,仅作记录)。注:该脚本来自 08-19 原始发布,共享 BabyLM 运行器从未调用它;01 的 BabyLM wrapper 与我们的 02 发射器各自接入了它。
- 至此各话题选择规则:TDC(契约校验器)与 BabyLM(打分脚本)= 在记录的实验里取验证最优;psydef、ARC、MountainCar = 框架链条终点(最后一个有官方记录的 stage)。
- 契约核对(09-27,只记录不改):验收方由各契约明文规定,但两处与我们的做法有出入。(a) psydef 契约要求 score.json 由**框架自己**跑提供的打分器产出——01 自打分合规;02 路线上该文件由 host 重算写出,记为偏差。(b) BabyLM 契约明文"框架必须自行把训练数据切成 train/validation"——v2 参考模块的固定验证行把切分收归 host,与契约冲突,记入重要改动登记(与"参考模块只给 02"同组);01 自行切分反而是合规做法。
