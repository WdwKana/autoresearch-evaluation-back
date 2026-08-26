# 2026-08-26 框架 02 (AI-Scientist-v2) × arc_wbe_2026 阻塞记录

## 已解决

1. **通用 wrapper 需要显式 `REAL_EVAL_RUN_ID`**（01 专用脚本自派生,02 经 `arc_framework_fullrun.sh` 不会）→ 启动时导出即可。
2. **公开仓缺失 `real_eval/adapters/ai_scientist_v2/patch_ai_scientist_v2_common.py`**（脱敏发布遗漏,02 所有 topic 的 wrapper 第一步都要执行它;全盘搜索无副本）。
   - 依据 wrapper 上下文重建了最小版本：仅创建 `ai_scientist/gpt_responses_compat.py`,提供 `chat_create(client, **kwargs)` 传输层垫片（wrapper 会把全部 `client.chat.completions.create(` 调用改写为 `chat_create(client,`;垫片处理 `max_tokens`→`max_completion_tokens` 等供应商差异,零科学逻辑）。文件头已标注 "reconstructed"。
   - **待办：向持有私有仓的协作者索取原件 diff 校对。**

## 当前硬阻塞：Semantic Scholar API key

- run `fullrun_arc_02_20260826_062148`（保留）：exit 124,ideation 阶段 30 分钟超时。
- 根因：无 `S2_API_KEY` 时 S2 检索被 429 限流（57 次）,且上游 `ai_scientist/tools/semantic_scholar.py` 的 `backoff.expo` **无 max_tries/max_time 上限**,实测退避到 949 秒/次——ideation 预算全部耗在退避睡眠,加大超时无意义。
- 01 不依赖 S2（用浏览器环境）,故未受影响。
- **解法（二选一）**：协作者提供在用的 S2 key（顺带保证环境一致）;或自行申请（https://www.semanticscholar.org/product/api#api-key-form,免费）。
- **注入方式**：`FRAMEWORK_DOCKER_ARGS="-e S2_API_KEY=<key>"`（通用 wrapper 自带口子,零脚本改动）。注意 `lib_real_eval.sh` 的 semantic-env 解析用硬编码 `RZGQ...` 前缀正则匹配原作者私有 key,对新 key 无效,勿走 `api/_semantic_scholar_api_usage.md` 路径。
