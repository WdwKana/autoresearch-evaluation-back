# 上下文膨胀证据包 (2026-09-01, DS×ARC 探针采样)

来源 run: probe_ds_20260901_181553 (deepseek-v4-flash × 01×ARC, 观测型探针,
patch_request_probe.py, 零内容干预)。采样 ~75 分钟, 175 次请求, 花费 ~$0.5。

## 文件

- giant_evidence.json — 13 个 >=250k tokens 请求的完整分解: 逐条消息的
  role/token数/sha256前缀/200字符预览, 按角色汇总, 全程增长序列。不含原文,可外发审计。
- request_probe_ds_20260901.jsonl — 全部 175 次请求的原始探针记录(每行一个请求)。

## 核心发现(独立审计者可从数据自行验证)

1. 指数倍增 (Paper Survey Agent): growth_series 中消息数 42→86→174→350→702
   (每轮×2+2); 最大请求 241,746 tokens 的 702 条消息只有 32 种唯一 sha,
   86% token 为字节级重复(同一 11-token 错误信息重复 176 次)。
   代码位置: run_infer_idea.py:180 messages.extend(survey_messages) 与
   core.py:585 return Response(messages=history[init_len:]) 的组合。
2. 重复堆积 (Machine Learning Agent): 256k 请求中同一"想法选型块"(~28k)
   出现 6 份(其中两份 sha 完全相同: fa127f16d999), 加一条 65,569-token
   常驻 assistant 消息(sha aeff3162be87, 连续 6+ 次请求携带);
   真正的当前工作内容仅占 ~13%。
   代码位置: run_infer_idea.py 中 survey_res 被内插 12 处, 其中 judge 循环
   (408-435行)每轮追加 2 份且 judge_messages 从不清理。
3. 常态而非极值: ML Agent 进入平台期后连续 11+ 次请求全部 >250k —— 对
   262,144 上限的 kimi-k2.6 意味着该阶段每次调用必然失败(实测 kimi 死于
   "Range of input length should be [1, 262144]")。

## 设计/缺陷边界(论文 arXiv:2505.18705 已核实)

迭代评审(Advisor/Judge loop)与"每个 agent 看到 idea"是论文设计;
同一内容重复 6-176 次、历史不去重不压缩是实现缺陷 —— 论文对
history/token limit/truncation 零提及, 该维度在设计中缺失。

## 用途

修复前基线。修复(去重,不改变信息集合)后用同一探针重采样对比。
