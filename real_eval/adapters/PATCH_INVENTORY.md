# ResearchClawEval 补丁清单(01 AI-Researcher / 02 AI-Scientist-v2 / 共享层)

状态日期:2026-10-16。分支 `fix/01-arc-delivery-v2`,基线为分叉时的上游 `0110a50`。
上游 `main` 已于 2026-10-13 重写为无共同祖先的新历史(`e742d15`),并附带 `real_eval/adapters/ai_researcher/adapter-policy.v1.json`;本清单每条都标注了它在该 policy 里的归类(允许类 / 禁止类 / 未定义类),供团队对齐用。

"归类"一栏的含义:
- **允许类**:canonical_imports / dataset_mount / local_command_server / relay_env / context_truncation / schema_tools
- **禁止类**:hardcoded_prepare / agent_prompt_replacement / method_baseline_strategy / host_handoff_promotion / score_creation / hidden_label_access
- **未定义**:policy 的封闭清单里没有对应类别(主要是"崩溃护栏/稳健性"和"观测"),需要团队新增类别才能归位

所有运行时补丁的共同机制:在容器内、框架启动前,对该次 run 的源码副本做锚点替换;锚点找不到即报错退出(不静默跳过);已打过标记即幂等跳过。框架的 git 检出从不被修改。

---

## 一、01 · AI-Researcher(`real_eval/adapters/ai_researcher/`,21 个)

### A1. 实现错误修正(1)

| 补丁 | 改哪里 | 做什么 | 为什么(触发案例) | 归类 |
|---|---|---|---|---|
| `patch_idea_loop_fixes` | `research_agent/run_infer_idea.py`、`inno/workflow/flowcache.py` | 修两处实现错误:idea 循环 `messages.extend(survey_messages)` 实为列表自我扩展,每轮把整段历史翻倍(42→86→174→350→702 条,86% token 为重复);另一处变量标错。API 调用次数不变,只去掉错误的重复 | kimi 的 262k 窗口被此一项单独撑爆(证据 `debug/dawei/evidence/2026-09-01-context-bloat/`) | 未定义(实现缺陷修正) |

### A2. 工具 / 基础设施稳健性(10)

成功路径逐字节不变,只改"本来会崩/会卡死"的路径;对不遵守工具协议的模型(主要是 kimi)客观上有利——上游原版下这些运行会直接失败。

| 补丁 | 改哪里 | 做什么 | 触发案例 | 归类 |
|---|---|---|---|---|
| `patch_logger_resilience` | `inno/logger.py::_warp_args` | 日志美化时的 `json.loads` 失败不再杀死整个运行,改记原文(截断 2000 字) | kimi ARC `…120826`,5.6 KB 参数在第 5645 字符解析失败,整个运行 exit 1 | 未定义 |
| `patch_tool_args_resilience` | `inno/core.py` 工具参数解析 | 参数 JSON 非法时以 `[Tool Call Error]` 工具消息退回模型让其重发,而非崩溃 | kimi 两次运行各因一个语法错误全盘死亡 | 未定义 |
| `patch_refine_report_fallback` | `run_infer_idea.py` / `run_infer_plan.py` refine 循环 | 分析 agent 未通过工具提交报告时,保留框架一行之前已从消息文本取得的同一份报告,`further_plan` 置空并打标记,继续;有提交则逐字节不变 | mcar×kimi `…124934` 跑 4 小时后 KeyError 崩溃、零交付 | 未定义 |
| `patch_loop_guard` | `inno/core.py` agent 循环 | 连续相同工具调用 3 次提示、8 次后一轮宽限再停;`max_turns` 由无穷改为 300;空回复重试 1 次后不再当作"继续" | 79 分钟 Coding Plan 空转、峰值 105k token、从不收尾 | 未定义 |
| `patch_browser_tool_timeout` | 三个重型浏览工具 | 整页问答 / 本地文件转换 / 看图各加 240 s 上限;实验命令路径不碰 | TDC 一天两次卡在整页问答 30–50 分钟 | 未定义 |
| `patch_file_browser_text` | markdown 文件浏览器 | 接受 json/jsonl/yaml/toml/csv/tsv/log 等文本扩展名;"Download complete." 改为如实说明 | kimi 对同一 JSON 文件打开 261 次 | 未定义 |
| `patch_file_browser_paging` | `read_file` 与分页壳 | 文件不存在时返回诚实错误而非"第 1 页/共 1 页";单页时提示无更多页 | kimi 对不存在的文件翻页 160 次 | 未定义 |
| `patch_run_command_idle_timeout` | `docker_env.run_command` | 命令输出完全静默 1800 s 后,在沙箱内杀该命令的进程树、回收串行命令通道 | ARC×kimi `…151115` 卡死 36 分钟 | 未定义 |
| `patch_run_command_keepalive` | 同上 | 沙箱命令服务器死亡("Connection refused")时按框架自身的初始化方式重启容器并重试 | BabyLM×g6 `…061209` 连续 23 次拒绝,工作区丢失 | 未定义(接近 local_command_server) |
| `patch_reasoning_effort_fallback` | `inno/core.py::acompletion` | 提供商拒绝带工具的请求(要求 `reasoning_effort='none'`)时用同一请求重发一次 | 09-24 bianxie 线路让 01 第一个 agent 直接死亡 | relay_env(允许类) |

### A3. 资源隔离与可见性(4)

| 补丁 | 做什么 | 触发案例 | 归类 |
|---|---|---|---|
| `patch_nested_cpu_isolation` | 内层实验容器加 `--cpus N`(`AI_RESEARCHER_EXEC_CPUS`)与线程数环境变量;原生毫无 CPU 限制 | kimi 的 torch 默认抢 190 核两小时 | 未定义(多租户隔离) |
| `patch_nested_gpu_isolation` | 外层 `CUDA_VISIBLE_DEVICES` 不会传进内层容器;改为 `--gpus device=…` 物理只挂允许的卡 | agent 训练代码可见全部 8 卡 | 未定义(多租户隔离) |
| `patch_exec_env_provision` | 容器建好后安装 pyarrow/pandas(运行镜像没有);以前靠 Prepare Agent 的副作用 pip 掩盖 | deepseek ARC `…101926` 第一次读 parquet 即 ModuleNotFoundError | 未定义(环境供给) |
| `patch_resource_visibility` | 向 agent 声明可用核数/GPU;长命令结束后附一行实际 CPU 用量 | DS 声明 cuda 却在 CPU 上训练等 | **agent_prompt_replacement 边缘**(往提示词加内容) |

### A4. 流程与交付门槛(3,需团队表态)

| 补丁 | 做什么 | 触发案例 | 归类 |
|---|---|---|---|
| `patch_prepare_bypass` | 自定义题目没有源论文,Prepare Agent 被要求"从零个候选里选五个仓库";输入为空时合成它本来会产出的空结果并跳过该 agent;`AI_RESEARCHER_PREPARE_BYPASS=1` 开关 | kimi 自造搜索 505 条消息撑爆窗口 | **hardcoded_prepare(禁止类)** |
| `patch_empty_input_truth` | 三处提示词断言"你已读过这些论文",而论文列表为空;输入确实为空时把假前提换成真话 | kimi 猜文件名 536 条消息 | **agent_prompt_replacement(禁止类)** |
| `patch_ml_delivery_validation` | ML 阶段结束按磁盘上的真实文件(estimator.py)判定能否 `case_resolved`,缺则退回具体缺项;`case_not_resolved`(承认失败)仍允许 | 空的 case_resolved | 未定义(接近 schema_tools) |

### A5. 纯观测(3)

| 补丁 | 做什么 | 归类 |
|---|---|---|
| `patch_request_probe` | 记录每个出站请求的逐条消息构成(角色、token、哈希、预览、发出的 agent) | 未定义(观测) |
| `patch_response_probe` | 记录每个回复的 finish_reason、token 数、内容/推理长度、工具调用数 | 未定义(观测) |
| `patch_wire_tap` | httpx 传输层记录原始响应字节(含每个 tool_call 的原始参数串) | 未定义(观测) |

交付运行记录时这三者的输出(`request_probe.jsonl` / `response_probe.jsonl` / `wire_tap.jsonl`)按用户决定整体剔除。

### 01/02 包装器内嵌的 inline 补丁 → 已抽成独立文件(2026-10-16;我们新增的 13 段;psydef 01 包装器里的 2 段是上游自带的)

包装器相对上游的改动分四种:调用上述补丁文件的命令行(01 各包装器 18–21 行)、环境/预算设置(CPU 32、墙钟、`AI_RESEARCHER_MAX_TURNS=300`、loop-guard 上限、HF 离线、探针日志路径、`AI_RESEARCHER_PREPARE_BYPASS=1`、交付文件 glob 等)、overlay 重定向(exec 物化后的共享 runner)、以及原先以 `python3 - <<'PY…'` 写在 RUNTIME_COMMAND / 宿主侧的 13 段 inline 块。第四种已于 2026-10-16 逐段抽成独立文件:正文逐字节不变,原块前的注释并入文件头 WHY;包装器原位改为一行调用(留一行指向注释),文件加进 `FRAMEWORK_ENTRY_PATHS`(mcar / TDC / 02 ARC / 02 psydef)或 01 ARC 的 `cp` 清单带进容器,BabyLM 的五段本就在宿主侧按 `$ROOT/...` 调用:

| 原包装器 · 块 | 现文件(`real_eval/adapters/…`) | 运行侧 | 做什么 | 归类 |
|---|---|---|---|---|
| 01 ARC · `PYMODELFACT` | `arc_wbe_2026/patch_model_fact_ai_researcher.py` | 容器内,原生入口前 | model-fact 注入:把容器里实际注入的模型名/base URL 字面值追加到每份 run 内 brief,防止 agent 写占位符或臆造公开 URL(`…131103` 写成 "gpt-4") | agent_prompt_replacement 边缘(只加事实) |
| 01 mcar · `PYMODELFACT` | `mountaincar_continuous/patch_model_fact_ai_researcher.py` | 容器内,原生入口前 | 同上(mcar) | 同上 |
| 01 mcar · `PYRELOC` | `mountaincar_continuous/relocate_handoff_ai_researcher.py` | 容器内,原生入口后、门槛前 | 把框架存在子目录里的一套完整 checkpoint(最新)连同其 src/ 原样搬到契约位置;idea/trace/report 同理(最新者胜);`MCAR_HANDOFF_WORKSPACE` 可对留存 run 离线重放 | host_handoff_promotion 边缘(只搬不写) |
| 01 TDC · `PYMODELFACT` | `tdc_admet_tox/patch_model_fact_ai_researcher.py` | 容器内,原生入口前 | 同上(TDC) | 同上 |
| 01 BabyLM · `PY` | `babylm/patch_entrypoint_ai_researcher.py` | 宿主侧,启动前改源码副本 | `constant.py` 缺 `PLATFORM`、工具模块显式注册、`main()` 模块级调用缺参数、GitHub 搜索无 token(ARC 包装器已有同样修法) | 实现缺陷修正 |
| 01 BabyLM · `PYTT` | `babylm/patch_tiktoken_special_tokens.py` | 宿主侧 | `count_tokens()` 对含 `<\|endoftext\|>` 的语料抛错;按普通文本计数 | 稳健性 |
| 01 BabyLM · `PYMODEL` | `babylm/patch_writeup_model_routing.py` | 宿主侧 | 论文撰写阶段默认模型名硬编码(22 次 403,研究完成后 writeup 全丢);改用注入模型;`chat()` 失败返回 "" 而非 None | relay_env |
| 01 BabyLM · `PYCACHE` | `babylm/patch_writeup_agent_cache_files.py` | 宿主侧 | `compose_section()` 硬编码的 agent 缓存文件名与研究阶段实际写出的不符;对齐,缺失者跳过 | 实现缺陷修正 |
| 01 BabyLM · `PYNONE` | `babylm/patch_writeup_none_guard.py` | 宿主侧 | LLM 返回 None 时 `write_temp_log()` / `structure.split` 崩溃;加保护 | 稳健性 |
| 01 BabyLM · `PYSCORE` | `babylm/relocate_trace_ai_researcher.py` | 宿主侧,运行后、官方评分前 | 把框架自写的 `experiment_trace.json` 原样复制到工作区根并记 `handoff_relocation.json`;score.json 由官方 `run_babylm_score.py` 写(此前表格误写为"写 score.json") | host_handoff_promotion 边缘(只抄) |
| 02 ARC(旧正式包装器)· `PY` | `ai_scientist_v2/patch_bfts_cleanup_guard.py` | 容器内 | 上游"有则复制 experiment_results,随后无条件删除"的顺序缺陷;孤儿进程清理不杀自身 | 实现缺陷修正 |
| 02 ARC(旧正式包装器)· `PYSPEC` | `arc_wbe_2026/patch_idea_delivery_spec_ai_scientist_v2.py` | 容器内 | 把交付契约写进 idea JSON,使 BFTS 编码 agent 能看到(它看不到 ideation 的系统提示) | agent_prompt_replacement |
| 02 psydef(旧正式包装器)· `PYTOK` | `ai_scientist_v2/patch_ideation_max_tokens.py` | 容器内 | ideation 输出上限 `MAX_NUM_TOKENS` 4096→16384(推理模型把 FinalizeIdea JSON 截断;此前表格误写为 tiktoken 修法) | 稳健性 |

抽出时的核验(scratchpad `extract_verify/`):13 段正文与原 heredoc 文本逐字节一致;旧块(`python3 -` 读 stdin)与新文件在相同夹具副本上的输出逐字节一致——宿主可跑的 10 段直接比对(含 mcar 留存 run `…153128` 的两套 checkpoint 工作区副本),3 段绑定 `/workspace` 的 model-fact 在 `ai-researcher:runtime-ready` 镜像里比对(含幂等第二遍);六个包装器 `bash -n` 通过;01 五个包装器的补丁序列重放 112 OK / 0 FAIL;`shared_layer_overlay.py check` 不受影响。

**抽出时发现(01 ARC `PYMODELFACT`)**:该块原来位于包装器**未加引号**的 heredoc `RUNTIME_COMMAND=$(cat <<EOF …)` 内,宿主 bash 对第二个锚点里的 `` `OPENAI_BASE_URL` `` 做了命令替换(宿主 stderr "OPENAI_BASE_URL: command not found"),容器收到的锚点是三个空格 + "environment variable",永远匹配不上。留存的 9 个 01×ARC 运行日志全部是 "1 literal(s) appended":只追加了模型名字面值,base URL 字面值从未追加(kimi 20261008 的 run 内 brief 可证)。独立文件按原文执行,两条都追加——这是一处**行为变化**(更接近 09-28 的本意),已写进该文件头。

仍留在包装器里的 heredoc 均为上游自带;01 ARC 的两个交付门槛块(handoff gate / postscore gate)与上游逐字一致,只多了 `2>"$LOG_DIR/*.err"` 的 stderr 落盘。另:`real_eval/scripts/resolve_native_artifacts.py`(交付映射:把框架原生位置的交付物链接到工作区根,host_handoff_promotion 边缘)是我们在 910df40 新增的独立脚本而非 inline 块,却放在共享脚本目录——属"代码位置迁移"议题,建议移入 `real_eval/adapters/`。

其它 01 专属文件:`mountaincar_continuous/patch_ai_researcher.py`(mcar 运行时适配)、`mountaincar_continuous/host_python_jax.sh`(让共享 runner 的官方评分在 JAX 镜像内执行)、`tdc_admet_tox/patch_ai_researcher.py`(TDC 运行时适配,610 行;上游 e742d15 已用 `install_runtime_adapter.py` 重写)。

---

## 二、02 · AI-Scientist-v2(`real_eval/adapters/ai_scientist_v2/`,13 个 + 现役管线)

### B0. 模型 / 传输接入(2,重建件)

| 补丁 | 做什么 | 归类 |
|---|---|---|
| `patch_ai_scientist_v2_common` | 生成 `gpt_responses_compat.py` 垫片,把所有 `client.chat.completions.create` 改经它:转发到 OpenAI 兼容端点,提供商拒绝 `max_tokens` 时改用 `max_completion_tokens` 重试 | relay_env(允许类) |
| `tdc_admet_tox/patch_ai_scientist_v2`(所有 02 发射器都用) | 注册 `OPENAI_MODEL`、客户端走注入的 base_url/key;token 统计对 None 保护;`bfts_config.yaml` 所有模型引用指到同一模型(否则 journal 回退硬编码 gpt-4o) | relay_env / canonical_imports |

两者是按包装器调用约定重建的(公开发布缺失原件);上游 e742d15 已放入同路径的不同内容,整理时须对照。

### B1. 基础设施稳健性(4)

| 补丁 | 做什么 | 触发案例 | 归类 |
|---|---|---|---|
| `patch_semantic_scholar_bounded` | Semantic Scholar 查询的无上限退避改为 3 次/60 s,失败后走工具原生 "No papers found." 并记录 | 949 秒退避吃光 ideation 预算 | 未定义 |
| `patch_ideation_action_format` | 容忍 `**Action**:` 这类 markdown 装饰的标签,否则上游丢弃整个有效 idea("Stored 0 ideas") | deepseek psydef `…212250` | 未定义 |
| `patch_ideation_tolerant_parser` | 一条回复多个 ACTION/ARGUMENTS 块按顺序执行;`{"idea":{"idea":…}}` 去掉多余一层;JSON 仍无效则照旧失败 | kimi 多块回复、deepseek 嵌套 | 未定义 |
| `patch_worker_future_headroom` | 父进程等 worker 的超时多留 900 s,使子进程的超时反馈能到达父进程 | BabyLM `…051954` 两个草稿无声丢失;**从未接线** | 未定义 |

### B2. 纯观测(1)

`patch_prompt_logging`:每阶段 Memory 摘要、每条编译后的提示词与原始回复写到 `prompt_logs/`;返回值与上游一致。交付时剔除。

### B3. 框架认知改动(2,用户 2026-09-27 逐条批准,台账 B11/B12)

| 补丁 | 做什么 | 归类 |
|---|---|---|
| `patch_remove_synthetic_data_guideline` | 删掉草稿指南里 "Make sure to create synthetic data if needed." 一句(在有固定数据集与冻结评分器的题目上是反向指令) | **agent_prompt_replacement** |
| `patch_remove_hf_dataset_goals` | 删掉阶段目标里"再引入两个/共三个 HuggingFace 数据集"及完成判据里"至少两个数据集"(HF 离线、单数据集下必然失败) | **agent_prompt_replacement** |

使用它们的每个 02 结果都必须标注"原生指南行已删除"。

### B4. 旧 ARC 正式包装器专用(5,遗留,现役不用)

| 补丁 | 做什么 | 归类 |
|---|---|---|
| `patch_ideation_task_framing` | ARC 蓝图里 "when possible 输出 estimator.py" 改为明确交付要求并点明接口与数据位置 | agent_prompt_replacement |
| `patch_task_definition_taskdesc` | 试验:把 ARC 官方任务定义追加到 BFTS task_desc 末尾 | agent_prompt_replacement |
| `patch_bfts_delivery_contract` | 把 ARC 交付接口(`predict(mlp)->(32,256)`、真实数据要求)挂进 stage 2+ 的实现指南 | agent_prompt_replacement |
| `patch_native_finalization` + `arc_contract_finalization` | 在原生 writeup 槽(传 `--skip_writeup` 后空置)插入"按契约收尾"阶段,用框架自存的各阶段 best_solution 拼交付物 | **host_handoff_promotion** |

仅被 `02_ai_scientist_v2_arc_wbe_2026_fullrun.sh` 引用;建议归档。

### B5. 现役管线在容器内做的其它事(`debug/dawei/ladder/`,待迁移)

| 组件 | 做什么 | 归类 |
|---|---|---|
| `tier_apply.py`(容器内套补丁器)| 依序执行 B0/B1/B2/B3;发射器另设 `MAX_NUM_TOKENS` 4096→16384、ideation 最多 3 次尝试、`num_workers=1`、各阶段迭代 `20/6/6/2`、可选 VLM 模型覆盖 | 配置项(context_truncation 相关) |
| `*_reference_v2.py`(参考模块,经 `--add_dataset_ref` 交给框架)| 数据加载、固定验证集、官方验证/打包函数——契约之外只给 02 的可信度装置,01 无对等物 | 需团队定性 |
| `assemble_*.py` + `*_host_validate.py` | 从 BFTS 各阶段 best_solution/journal 确定性地拼出契约交付物并在宿主侧校验 | **host_handoff_promotion** |
| 主题文件 | 由共享生成器 + 02 的 4 个共享层补丁渲染(见第三节) | 见第三节 |

---

## 三、共享层补丁(`real_eval/adapters/<框架>/shared_layer_patches/`,20 个)

共享文件本身与上游逐字节一致;这些 `.patch` 由 `real_eval/adapters/shared_layer_overlay.py` 在运行时套到副本上(生成器在进程内、runner 物化到 `real_eval/run_checks/shared_layer_overlay/`)。每个 hunk 必须在上游原文中恰好匹配一次,否则发射当场停止。对上游 e742d15 的新版共享文件,20 个中 **5 个已失配**(两框架的 babylm、psydef runner 补丁及 02 的 arc runner 补丁——都是 `--gpus all` 那一段,上游改成了 `--gpus "${FRAMEWORK_GPUS:-all}"`),需重滚。

### C1. 给框架的输入文本(生成器,8 个)

| 补丁 | 影响 | 内容 | 来源 | 归类 |
|---|---|---|---|---|
| 01 `generate_arc_wbe_2026_native_inputs.py` | 仅 01 渲染 | 把 ARC brief 放进 AI-Researcher 的 dataset_candidate 副本,并附 trace 字段的精确取值要求与官方评分器对 estimator.py 的运行时约束(numpy-only、类名、禁止常量预测);EVALUATION 加"根目录"位置说明;REF 改指容器内可达路径 | 3dd3c50…910df40(08-26–09-03) | schema_tools / dataset_mount 为主 |
| 01 `generate_tdc_admet_tox_native_inputs.py` | 仅 01 | predictions.csv 精确 schema;契约的 3,600 s 累计实验上限。**已知措辞错位**(上限句插在 "predictions" 与 ".csv" 之间)原样保留 | 15522e0、4878c71(08-28) | schema_tools |
| 01 `generate_topic2_native_inputs.py` | 仅 01(mcar 经适配器消费) | experiment_trace.json 顶层键 schema;REF 改为容器内 `/workspace/automation/` 路径 | 8ef1c1f、0acb39c(09-03) | schema_tools |
| 01 `generate_babylm_native_inputs.py` | 仅 01 | EVALUATION 加"根目录"位置说明 | 910df40 | schema_tools |
| 02 `generate_babylm_native_inputs.py` | 仅 02 主题 | 域名列表改读磁盘(硬编码列表与实际文件不符,节点据此构造路径失败后转向合成数据);"提供参考模块"句;"只用提供语料"句;结果定义为参考验证函数在固定验证集上的 ppl | 4824615、6ccf3c8、89be78d | agent_prompt_replacement(主题文本) |
| 02 `generate_psydefdetect_native_inputs.py` | 仅 02 | "只用提供数据集"句 | 6ccf3c8 | 同上 |
| 02 `generate_tdc_admet_tox_native_inputs.py` | 仅 02 | "只用提供文件"句 | 6ccf3c8 | 同上 |
| 02 `generate_topic2_native_inputs.py` | 仅 02(mcar) | "提供参考模块 / 只在提供环境里"句;结果定义为参考 `official_evaluation` 的 Reward Mean | 6ccf3c8、3d94b0c | 同上 |

### C2. 共享 runner 行为(12 个;01 五个、02 七个)

| 改动 | 出现在 | 内容 | 来源 |
|---|---|---|---|
| 生成器重定向 | 01:babylm、mcar、tdc;02:babylm、mcar、psydef、tdc、topic2 | runner 内的生成器调用改经 overlay / mcar 适配器(机械性,一行) | 10-04 转换 |
| mcar 交付门槛 ≥1 | 01、02 mcar runner | trace 实验数由 2–4 改为 ≥1,与契约文字 "one or more" 一致 | 7945411(用户裁定 09-28) |
| mcar 零 checkpoint 保护 | 同上 | 没有 checkpoint 时不再因 `set -e` 在写终态前死亡 | a8eaa3c |
| EXIT 清理收窄 | 01/02 babylm、02 arc | 退出时只删本次 run 的内层沙箱,不按前缀删主机上所有同类容器 | d216e4f(用户批准 10-02) |
| GPU 限定钩子 | 01/02 psydef、01/02 babylm、02 arc | `REAL_EVAL_ALLOWED_GPUS` 设定时用 `--gpus device=…`;未设则 `--gpus all` 不变 | 04b49db、c3eb6a3、37c9ea1/0c85257 |
| HF 离线默认 | 02 arc | `HF_HUB_OFFLINE`/`HF_DATASETS_OFFLINE` 默认 1(题目全本地,误触 hub 会挂网) | a6bdfab |
| psydef 退出码与终态 | 01/02 psydef | EXIT trap 不再吞掉真实退出码;校验失败写终态并 exit 44 | 868d755 |
| psydef 超时接受 | 同上 | 超时(124/137)但交付物合规的运行不再被丢弃 | e656e4b |
| psydef kimi 直连 | 同上 | `PSYDEFDETECT_KIMI_ALLOW_DIRECT=1` 允许直连提供商;默认关 | 2e0281d |
| TDC 容器 32 核 | 01/02 tdc | `--cpus 4` → `32`,与 02 发射器预算对齐 | b68e0db(用户裁定 10-02) |
| TDC smoke 探针 | 01/02 tdc smoke | `REAL_EVAL_SMOKE_PROBE=script` 用与 agent 无关的接线探针代替 Codex smoke | 9e122d2 |

---

## 四、建议的处置分类(待用户/团队确认)

- **保留并提议上游新增类别**:A1、A2、B1(崩溃护栏/稳健性),A5、B2(观测),A3(多租户隔离)。
- **保留但必须标注**:A4、B3、C1 的 02 主题句、B5 的参考模块与装配——它们改变了框架看到的文本或交付流程,按上游 policy 多属禁止类。
- **归档**:B4 的 5 个;旧 02 正式包装器;`patch_worker_future_headroom`(未接线)。
- **重滚**:对上游 e742d15 失配的 5 个共享层补丁。
