# ARC-WBE-2026 Contract

## Topic

- Topic id: `arc_wbe_2026`
- Topic label: `ARC-WBE-2026`
- Dataset environment variable: `ARC_WBE_2026_DATASET_ROOT`
- Canonical dataset root: `data/arc_white_box_estimation_2026`

## Objective

Produce an official-comparable ARC White-Box Estimation Challenge 2026 result. A framework must consume the local ARC-WBE inputs, implement or execute a reproducible estimator workflow, and preserve evidence for the reported score.

## Required Inputs

- The materialized ARC-WBE dataset under `ARC_WBE_2026_DATASET_ROOT`.
- The generated topic-native inputs under `inputs/`, including `docs/arc_wbe_2026_summary.md` and this contract.
- The local scorer `automation/scripts/run_arc_wbe_2026_local_score.py` and its official adapter.

## Required Outputs

- An official-format submission artifact when the selected workflow can produce one.
- Root-level `estimator.py`, `submission.json`, `score.json`, `experiment_trace.json`, and `final_report.md`, all produced by the framework workflow in the current workspace.
- `score.json` must be produced by the local scorer and identify its score source. An official-comparable completion requires `score_source: "official_adapter_whest_run"`.
- `experiment_trace.json` must prove 2 to 4 materially different experiments, identify the selected experiment, and record framework-native execution and the injected internal API model/base URL.

## Execution Rules

- Use only ARC-WBE-2026 inputs from the current fresh run workspace and read-only dataset mount.
- Do not route this topic to any other topic's inputs, runners, contracts, datasets, or scores.
- Keep raw weights, complete tensor arrays, `all_layer_means`, and `final_means` out of logs and prompts.
- Use the configured provider and model for framework reasoning. For Kimi runs, use `api/codex_kimi_k27_code_relay_container.toml` and `kimi-k2.6`.
- Framework-internal OpenAI-compatible clients must read `OPENAI_BASE_URL`, `OPENAI_API_KEY`, and `OPENAI_MODEL` from the injected environment. Do not hardcode an endpoint or model.
- Follow `automation/arc_wbe_2026_execution_budget.md`. Immediately promote the selected experiment after the final allowed experiment.
- Treat tool-call scoring as out of scope unless the official ARC adapter explicitly supports it; preserve trace evidence instead.
- Do not claim successful scoring without a real local score artifact or official-format evidence.

## Isolation

- Every evaluation uses a fresh physical workspace under `real_eval/runs/<run_id>/<framework>/workspace`.
- Fixed framework repositories are templates only and must not receive generated artifacts.
