# ARC-WBE-2026 Kimi Execution Budget

This budget is mandatory for ARC-WBE-2026 evaluation runs that use the Kimi provider.

1. Run 2 to 4 materially different, framework-native estimator experiments. Do not start a fifth experiment.
2. Keep only a compact experiment ledger in the agent context: experiment id, estimator path, local score result, and decision. Do not paste dataset rows, weights, tensor arrays, or verbose tool outputs into the conversation.
3. Each framework-internal API client must use the injected `OPENAI_BASE_URL`, `OPENAI_API_KEY`, and `OPENAI_MODEL`. Do not hardcode `api.openai.com`, another provider, or a model name.
4. Immediately after the final permitted experiment, select the best valid estimator, invoke `automation/scripts/run_arc_wbe_2026_local_score.py`, and promote the selected root-level artifacts. Do not continue exploration after finalization begins.
5. Before exit, write `/workspace/experiment_trace.json` with `framework_native_execution: true`, `consumed_topic_input: true`, `workspace_trace_root: "/workspace"`, `experiments`, `selected_experiment_id`, `estimator_artifact`, `score_artifact`, `framework_internal_model`, and `framework_internal_api_base_url`.
6. A valid handoff requires framework-produced root-level `/workspace/estimator.py`, `/workspace/submission.json`, `/workspace/score.json`, `/workspace/experiment_trace.json`, and `/workspace/final_report.md`. Do not rely on evaluator post-processing to create any of these files.
7. If the framework cannot finish within its execution budget, exit with a concrete blocker. Do not fabricate metrics, score files, or traces.
