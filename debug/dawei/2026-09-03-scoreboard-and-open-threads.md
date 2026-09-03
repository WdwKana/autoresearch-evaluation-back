# 2026-09-03 战绩留档 + 明日靶子

一天内让两个"从未通关"的 topic×model 首次出分,并把 psydefdetect 接入通用栈后
复跑刷新分数。记录当前榜单、今日修复、以及两条已诊断清楚但未根治的线索。

## 当前榜单(official / framework-scored)

| Topic × Model | 结果 | 来源 |
|---|---|---|
| DS × ARC | **0.0886** | official_adapter_whest_run — 今日首次,DeepSeek 首个 ARC 官方分 |
| luna × ARC | 0.09 | 此前 |
| luna × TDC | 0.6311 macro-AUROC | 此前(host_hidden_test_labels) |
| luna × babylm | **finished, val_ppl 742.97** | 今日首次通关(自动收尾+验收层补件) |
| luna × psydef | **0.1393** | 今日,最新栈复跑(此前 0.1070,分数提升) |
| luna × mcar | ❌ 交付接口不全 | 见下 |
| DS × psydef / mcar | ❌ DS 空占位顽症 | 见下 |

## 今日修复(提交区间 85e11b4 .. 3871cee)

- 十层栈接入 babylm/mcar(85e11b4);路径教义:规格翻译+交付地图+持久化不变量(910df40);
  workplace 布局统一到 ARC 约定(8ed4b2c)。
- loop-guard v3(空 completion 重试/熔断)+ 响应侧探针(84eedf7);
  v4 截断感知引导重试(4a005ed)——响应探针实证 churn 空响应=finish_reason=length(网关窗口预算截断,max_tokens 被无视,不可在本层预防,故引导重试是唯一治疗)。
- babylm SIGPIPE 收尾崩溃修复(c7e87a8):`find|head` 在 set -euo pipefail 下 SIGPIPE(141)杀掉收尾链;手动补收尾验证过可行,随后自动收尾也走通。
- mcar 一串:/project 持久化挂接(f943c72)、timeout 透传(10a7efb)、schema 送达+死链(8ef1c1f)、
  0字节契约填充(ea70e1f)、metaprompt 引号致 SyntaxError(0acb39c)、timeout 不再跳收尾(03ae210)。
- psydef 接入通用栈 7/9(3424438,冲突矩阵验证;prepare_bypass/empty_input_truth 因 psydef 已有更优等效物而跳过)、
  timeout 不弃已算分(e656e4b)、exec 预装 sklearn 栈(3871cee)。
- 三 topic timeout→评分行为统一(ARC/mcar/psydef:超时也尝试评分,合格即算,记0锚点保留)。

## 明日靶子 1:DS 空占位参数顽症(已诊断,未根治)

**现象**:DS 在复杂上下文下,tool-call 参数塌缩成空/占位,跨 3 topic 同签名复现:
- ARC Coding Plan:空参 transfer 乒乓 `{}`
- mcar ML:空 `case_resolved({})`
- psydef ML:`write_file(content="{...}")`(整条 70 token,content 字面就是省略号)+ 空 `case_not_resolved({})`

luna 从不出现(参数总饱满)→ 确定是 DS 模型侧退化,非 harness bug。
排除史:reasoning_content 丢失、length 截断、FIX3 无源 —— 均被证伪;跨 3 topic 一致 + 完整参数实锤后定性为"占位参数生成退化"。

**为何 loop-guard v4 没拦住(真盲区)**:v4 的"空 completion"要求 `not message.tool_calls`(这里有 tool_call),
"重复熔断"要求参数逐字相同(中间插不同调用会重置计数)。"有 tool_call 但参数空/占位"两头都漏。

**修法方向**(明日,需离线测,对 luna 无害):给护栏加一维——tool_call 参数为空/占位
(`{}`/`{...}`/空串/仅省略号/仅 null 字段)时判无效,拦+提示"参数缺失,请补全实质内容";
连续 N 次仍占位则按无效终态处理。

## 明日靶子 2:mcar 接口交付不全(已诊断)

luna 保留了 get_model_ready/Model 接口(此前误判为"自造结构",已更正),但交付缺
`src/helpers.py` + `config.yaml`(冻结 evaluate.py 硬依赖 `from src.helpers import ...`),
且 handoff 未能组装出可评分的 src(根是 starter 原版,与 checkpoint 不匹配;project/src 缺 helpers/config)。
根因同家族:mcar EVALUATION 未把接口文件清单送达 agent(未提 get_model_ready/helpers)。
mcar 叠加接口刚性+慢(3h)+luna 完美主义发散,是最难 topic。
**选择**:低成本强化送达(接口文件清单写进 EVALUATION)试最后一次,或放一放。

## 记账(裁量点 / 框架交付质量,非 harness 可修,待团队 ratify)

- 契约 "root-level" 经交付地图重释;exec 预装库(pyarrow/sklearn)为环境准备而非 agent 装包;
  验收层用框架模型补件 —— 三者同属"宿主辅助边界",上正式榜单前需批准。
- babylm 742 困惑度偏高:luna 交了诊断实验值(模型交付选择),非 harness。
- 仓库 automation/mountaincar_continuous_contract.md 曾 0 字节(已从 topic2 填充);
  mcar contract 内容仍带 topic2 命名(表面不一致,已知)。
- babylm 无 wrapper 墙钟(唯一);明示墙钟目前无证据表明必需,暂不做。

## 状态
今日全部 run 落定,无活跃烧钱。收尾链保持现状(babylm 实证其必要:两次 finished 均靠验收层补 idea/report)。
