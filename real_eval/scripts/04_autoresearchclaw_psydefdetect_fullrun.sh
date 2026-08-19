#!/usr/bin/env bash
set -euo pipefail
ROOT="${RESEARCHCLAWEVAL_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
source "$ROOT/real_eval/scripts/lib_real_eval.sh"
export FRAMEWORK_NAME="AutoResearchClaw"
export FRAMEWORK_SLUG="04_autoresearchclaw_psydefdetect_fullrun"
export FRAMEWORK_SRC="${RESEARCHCLAWEVAL_AUTORESEARCHCLAW_ROOT:-$(real_eval_resolve_framework_source "$ROOT" 04)}"
export FRAMEWORK_ENTRY_PREFIX="AutoResearchClaw"
export FRAMEWORK_ENTRY_PATHS=$(cat <<'EOF'
AutoResearchClaw/config.psydefdetect.yaml
AutoResearchClaw/topic.psydefdetect.txt
AutoResearchClaw/evaluation_prompts/psydefdetect_search_strategy.md
AutoResearchClaw/evaluation_prompts/psydefdetect_literature_collect.md
AutoResearchClaw/evaluation_prompts/psydefdetect_literature_screen.md
AutoResearchClaw/evaluation_prompts/psydefdetect_experiment_design.md
AutoResearchClaw/evaluation_prompts/psydefdetect_code_generation.md
AutoResearchClaw/psydefdetect_benchmark_knowledge.yaml
automation/psydefdetect_contract.md
automation/psydefdetect_execution_budget.md
EOF
)
export FRAMEWORK_RUNTIME_KIND="docker"
export FRAMEWORK_RUNTIME_IMAGE="${AUTORESEARCHCLAW_RUNTIME_IMAGE:-autoresearchclaw:runtime-ready}"
export FRAMEWORK_ENTRYPOINT="bash"
export FRAMEWORK_NATIVE_ENTRYPOINT="python -m researchclaw.cli run"
export FRAMEWORK_PROVIDER_INJECTION="config.psydefdetect.yaml OpenAI-compatible client uses OPENAI_BASE_URL, OPENAI_API_KEY, and OPENAI_MODEL"
export FRAMEWORK_NATIVE_LOG_MARKER="AUTORESEARCHCLAW_NATIVE_RUN"
export FRAMEWORK_EXECUTOR_KIND="framework_cli"
export FRAMEWORK_COMMAND_LABEL="python3 -m researchclaw.cli run --config config.psydefdetect.yaml"
export FRAMEWORK_RUNTIME_COMMAND=$(cat <<'EOF'
set -euo pipefail
echo "AUTORESEARCHCLAW_NATIVE_RUN"
python3 - \
  researchclaw/data/benchmark_knowledge.yaml \
  psydefdetect_benchmark_knowledge.yaml \
  researchclaw/agents/benchmark_agent/surveyor.py \
  researchclaw/pipeline/stage_impls/_experiment_design.py \
  researchclaw/pipeline/code_agent.py \
  researchclaw/pipeline/stage_impls/_code_generation.py \
  researchclaw/pipeline/stage_impls/_literature.py \
  researchclaw/experiment/agentic_sandbox.py \
  researchclaw/experiment/sandbox.py \
  researchclaw/pipeline/stage_impls/_execution.py \
  researchclaw/pipeline/stage_impls/_analysis.py <<'PY'
from pathlib import Path
import sys
import yaml

knowledge_path = Path(sys.argv[1])
projection_path = Path(sys.argv[2])
knowledge = yaml.safe_load(knowledge_path.read_text(encoding="utf-8")) or {}
projection = yaml.safe_load(projection_path.read_text(encoding="utf-8")) or {}
knowledge.setdefault("domains", {})["psydefdetect"] = projection["domains"]["psydefdetect"]
knowledge_path.write_text(yaml.safe_dump(knowledge, sort_keys=False), encoding="utf-8")

surveyor_path = Path(sys.argv[3])
text = surveyor_path.read_text(encoding="utf-8")
old = '''        domain_ids = self._match_domains(topic)
        if hypothesis:
            domain_ids = list(dict.fromkeys(
                domain_ids + self._match_domains(hypothesis)
            ))'''
new = '''        psydefdetect_topic = "psydefdetect" in topic.lower()
        domain_ids = ["psydefdetect"] if psydefdetect_topic else self._match_domains(topic)
        if hypothesis and not psydefdetect_topic:
            domain_ids = list(dict.fromkeys(
                domain_ids + self._match_domains(hypothesis)
            ))'''
if old not in text:
    raise SystemExit("AutoResearchClaw benchmark-domain routing insertion point not found")
surveyor_path.write_text(text.replace(old, new, 1), encoding="utf-8")

design_path = Path(sys.argv[4])
text = design_path.read_text(encoding="utf-8")
old = '''    if _time_budget > 7200:
        _max_conditions = 20'''
new = '''    if _time_budget > 7200:
        _max_conditions = 20
    if "psydefdetect" in config.research.topic.lower():
        _max_conditions = 2'''
if old not in text:
    raise SystemExit("AutoResearchClaw PsyDefDetect condition-budget insertion point not found")
text = text.replace(old, new, 1)
old = '''    return result


def _execute_experiment_design('''
new = '''    return result


def _psydefdetect_plan_errors(plan: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    baselines = _normalize_plan_field(plan.get("baselines"))
    proposed = _normalize_plan_field(plan.get("proposed_methods"))
    ablations = _normalize_plan_field(plan.get("ablations"))
    condition_names = [
        name.strip().lower()
        for name in _plan_field_names(baselines + proposed + ablations)
    ]
    if len(condition_names) != 2:
        errors.append(
            f"expected exactly 2 baselines/proposed_methods/ablations conditions, got {len(condition_names)}"
        )
    if ablations:
        errors.append("ablations must be empty for the two-condition recovery contract")
    has_word_lr = any(
        "word" in name
        and ("tfidf" in name or "tf-idf" in name)
        and "logistic" in name
        for name in condition_names
    )
    has_char_svc = any(
        ("char" in name or "character" in name)
        and ("tfidf" in name or "tf-idf" in name)
        and ("svc" in name or "svm" in name or "support vector" in name)
        for name in condition_names
    )
    if not has_word_lr:
        errors.append("missing word TF-IDF LogisticRegression condition")
    if not has_char_svc:
        errors.append("missing character TF-IDF LinearSVC condition")

    compute_budget = plan.get("compute_budget")
    if not isinstance(compute_budget, dict):
        errors.append("compute_budget must be a mapping")
    else:
        budget_conditions = _normalize_plan_field(compute_budget.get("conditions"))
        budget_names = [
            name.strip().lower() for name in _plan_field_names(budget_conditions)
        ]
        if len(budget_names) != 2:
            errors.append(
                f"compute_budget.conditions must contain exactly 2 conditions, got {len(budget_names)}"
            )
        if compute_budget.get("total_runs") != 2:
            errors.append("compute_budget.total_runs must equal 2")

    rendered = yaml.safe_dump(plan, sort_keys=False).lower()
    normalized_rendered = rendered.translate(str.maketrans({"\u2013": "-", "\u2014": "-"}))
    if "psydefconv.json" not in rendered:
        errors.append("plan must name /data/psydefdetect/PsyDefConv.json")
    if "psydefdetect_split.json" not in rendered:
        errors.append("plan must name /workspace/automation/psydefdetect_split.json")
    if not any(
        marker in rendered
        for marker in ("9 classes", "classes: 9", "num_classes: 9", "labels 0-8", "labels: 0-8")
    ):
        errors.append("plan must state 9 classes with labels 0-8")
    if not any(marker in rendered for marker in ("macro-f1", "macro_f1", "f1_macro")):
        errors.append("plan must use macro-F1 as the primary metric")
    metrics = plan.get("metrics")
    positive_label_evidence = "1-8" in normalized_rendered
    metric_candidates = []
    if isinstance(metrics, dict):
        metric_candidates.append(metrics)
    elif isinstance(metrics, list):
        metric_candidates.extend(item for item in metrics if isinstance(item, dict))
    if isinstance(plan.get("primary_metric"), dict):
        metric_candidates.append(plan["primary_metric"])
    for metric in metric_candidates:
        labels = metric.get("labels")
        if isinstance(labels, list):
            try:
                positive_label_evidence = positive_label_evidence or {
                    int(label) for label in labels
                } == set(range(1, 9))
            except (TypeError, ValueError):
                pass
    if not positive_label_evidence:
        errors.append("plan must define macro-F1 over positive labels 1-8")
    primary_metric = None
    if isinstance(metrics, dict):
        for primary_key in ("primary", "primary_metric"):
            candidate = metrics.get(primary_key)
            if isinstance(candidate, dict):
                primary_metric = candidate
                break
    elif isinstance(metrics, list):
        for candidate in metrics:
            if not isinstance(candidate, dict):
                continue
            candidate_name = str(candidate.get("name", "")).lower()
            if any(marker in candidate_name for marker in ("macro-f1", "macro_f1", "f1_macro")):
                primary_metric = candidate
                break
    if primary_metric is None and isinstance(plan.get("primary_metric"), dict):
        primary_metric = plan["primary_metric"]
    primary_direction = (
        str(primary_metric.get("direction", "")).strip().lower()
        if isinstance(primary_metric, dict)
        else ""
    )
    if primary_direction != "maximize":
        errors.append(
            "primary macro-F1 direction must be maximize, "
            f"got {primary_direction or 'missing'}"
        )
    return errors


def _execute_experiment_design('''
if old not in text:
    raise SystemExit("AutoResearchClaw PsyDefDetect plan-validator insertion point not found")
text = text.replace(old, new, 1)
old = '''    plan.setdefault("topic", config.research.topic)

    # BUG-R41-09: Enforce condition count limit based on time budget.'''
new = '''    plan.setdefault("topic", config.research.topic)

    if "psydefdetect" in config.research.topic.lower():
        plan_errors = _psydefdetect_plan_errors(plan)
        rewrite_attempts = 0
        if plan_errors and llm is not None:
            (stage_dir / "plan_rewrite_input.yaml").write_text(
                yaml.safe_dump(plan, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
            for rewrite_attempts in range(1, 3):
                rewrite_prompt = (
                    "Repair this PsyDefDetect experiment plan. Return ONLY valid YAML and "
                    "preserve the framework plan schema. Fix every validation error below. "
                    "Re-read the returned YAML before answering and ensure none of the listed "
                    "errors remains.\\n\\n"
                    "VALIDATION ERRORS FROM THE MOST RECENT FRAMEWORK PLAN:\\n- "
                    + "\\n- ".join(plan_errors)
                    + "\\n\\nFIXED CONTRACT:\\n"
                    "- Exactly two total conditions and total_runs: 2.\\n"
                    "- Baseline: word_tfidf_logistic_regression using class-balanced LogisticRegression.\\n"
                    "- Proposed method: char_tfidf_linear_svc using class-balanced LinearSVC.\\n"
                    "- ablations: [] and compute_budget.conditions contains exactly those two names.\\n"
                    "- Dataset /data/psydefdetect/PsyDefConv.json is a JSON list with id, "
                    "dialogue_id, dialogue, current_text, and integer label 0-8.\\n"
                    "- Use /workspace/automation/psydefdetect_split.json with train_record_ids "
                    "and eval_record_ids joined through row id.\\n"
                    "- The primary macro-F1 metric over positive labels 1-8 MUST have direction: "
                    "maximize. Never assign minimize to macro-F1.\\n"
                    "- State 9 classes, labels 0-8. No new split, repeated seeds, grid search, "
                    "significance tests, synthetic labels, downloads, or extra conditions.\\n\\n"
                    "CURRENT PLAN:\\n"
                    + yaml.safe_dump(plan, sort_keys=False, allow_unicode=True)
                )
                rewrite_response = _chat_with_prompt(
                    llm,
                    "You repair experiment plans and output YAML only.",
                    rewrite_prompt,
                    max_tokens=8192,
                )
                response_text = _extract_yaml_block(rewrite_response.content)
                (stage_dir / f"plan_rewrite_response_{rewrite_attempts}.yaml").write_text(
                    response_text,
                    encoding="utf-8",
                )
                try:
                    rewritten = yaml.safe_load(response_text)
                except yaml.YAMLError:
                    rewritten = None
                if isinstance(rewritten, dict):
                    plan = rewritten
                    plan.setdefault("topic", config.research.topic)
                plan_errors = _psydefdetect_plan_errors(plan)
                if not plan_errors:
                    break

        (stage_dir / "psydefdetect_plan_validation.json").write_text(
            json.dumps(
                {
                    "status": "valid" if not plan_errors else "invalid",
                    "framework_rewrite_attempts": rewrite_attempts,
                    "errors": plan_errors,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        if plan_errors:
            logger.error(
                "Stage 9: PsyDefDetect plan remains invalid after framework rewrite: %s",
                "; ".join(plan_errors),
            )
            return StageResult(
                stage=Stage.EXPERIMENT_DESIGN,
                status=StageStatus.FAILED,
                artifacts=("plan_rewrite_input.yaml", "psydefdetect_plan_validation.json"),
                evidence_refs=("stage-09/psydefdetect_plan_validation.json",),
                error="PsyDefDetect experiment plan failed semantic validation",
                decision="invalid_plan",
            )

    # BUG-R41-09: Enforce condition count limit based on time budget.'''
if old not in text:
    raise SystemExit("AutoResearchClaw PsyDefDetect plan-rewrite insertion point not found")
text = text.replace(old, new, 1)
old = '''    (stage_dir / "exp_plan.yaml").write_text(
        yaml.dump(plan, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )
    return StageResult(
        stage=Stage.EXPERIMENT_DESIGN,
        status=StageStatus.DONE,
        artifacts=("exp_plan.yaml",),
        evidence_refs=("stage-09/exp_plan.yaml",),
    )'''
new = '''    (stage_dir / "exp_plan.yaml").write_text(
        yaml.dump(plan, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )
    artifacts = ["exp_plan.yaml"]
    if (stage_dir / "plan_rewrite_input.yaml").exists():
        artifacts.append("plan_rewrite_input.yaml")
    if (stage_dir / "psydefdetect_plan_validation.json").exists():
        artifacts.append("psydefdetect_plan_validation.json")
    return StageResult(
        stage=Stage.EXPERIMENT_DESIGN,
        status=StageStatus.DONE,
        artifacts=tuple(artifacts),
        evidence_refs=tuple(f"stage-09/{artifact}" for artifact in artifacts),
    )'''
if old not in text:
    raise SystemExit("AutoResearchClaw PsyDefDetect plan-evidence insertion point not found")
design_path.write_text(text.replace(old, new, 1), encoding="utf-8")

code_agent_path = Path(sys.argv[5])
text = code_agent_path.read_text(encoding="utf-8")
if "import sys\n" not in text:
    text = text.replace("import re\n", "import re\nimport sys\n", 1)
old = "            critical, warnings = self._hard_validate(files)"
new = "            critical, warnings = self._hard_validate(files, topic)"
if text.count(old) != 1:
    raise SystemExit("AutoResearchClaw hard-validation call insertion point changed")
text = text.replace(old, new, 1)
old = '''    def _hard_validate(
        self, files: dict[str, str],
    ) -> tuple[list[str], list[str]]:'''
new = '''    def _hard_validate(
        self, files: dict[str, str], topic: str = "",
    ) -> tuple[list[str], list[str]]:'''
if old not in text:
    raise SystemExit("AutoResearchClaw hard-validation signature insertion point not found")
text = text.replace(old, new, 1)
old = '''        known_modules = {
            fname.replace(".py", "")
            for fname in files
            if fname.endswith(".py")
        }
        for fname, code in files.items():'''
new = '''        known_modules = {
            fname.replace(".py", "")
            for fname in files
            if fname.endswith(".py")
        }
        if "psydefdetect" in topic.lower():
            allowed_imports = set(getattr(self._exp_config.sandbox, "allowed_imports", ()))
            allowed_imports.update(getattr(sys, "stdlib_module_names", ()))
            allowed_imports.update(known_modules)
            for fname, code in files.items():
                if not fname.endswith(".py"):
                    continue
                try:
                    tree = ast.parse(code)
                except SyntaxError:
                    continue
                imported_roots = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        imported_roots.update(alias.name.split(".")[0] for alias in node.names)
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        imported_roots.add(node.module.split(".")[0])
                if "runpy" in imported_roots:
                    critical.append(
                        f"[{fname}] PsyDefDetect official scorer must run through "
                        "subprocess.run(..., check=True); importing runpy in any generated "
                        "file is forbidden"
                    )
                for module in sorted(imported_roots - allowed_imports):
                    critical.append(
                        f"[{fname}] ImportError: module '{module}' is outside the PsyDefDetect "
                        "sandbox allowed_imports and will fail at runtime; remove it and use only "
                        "the configured local packages"
                    )
                if "pd.read_json(" in code or "pandas.read_json(" in code:
                    critical.append(
                        f"[{fname}] PsyDefDetect id integrity error: pandas.read_json may coerce "
                        "string ids such as '0001' to integers. Load PsyDefConv.json with "
                        "json.load and preserve row['id'] exactly before constructing a DataFrame"
                    )
            combined_code = "\\n".join(files.values())
            required_delivery_markers = (
                "/workspace/predictions.jsonl",
                "/workspace/score.json",
                "/workspace/experiment_trace.json",
                "/workspace/final_report.md",
                "/workspace/automation/scripts/run_psydefdetect_local_score.py",
                "--dataset-root",
                "--split-manifest",
                "--predictions",
                "--output-score",
                "psydefdetect_score",
                "score_key",
                "experiments",
                "experiment_id",
                "scorer_command",
                "selected_experiment_id",
                "framework_native_execution",
                "consumed_topic_input",
                "workspace_trace_root",
                "framework_internal_model",
                "framework_internal_api_base_url",
                "OPENAI_MODEL",
                "OPENAI_BASE_URL",
            )
            missing_delivery_markers = [
                marker for marker in required_delivery_markers if marker not in combined_code
            ]
            if missing_delivery_markers:
                critical.append(
                    "PsyDefDetect framework-owned delivery is incomplete in generated code; "
                    "the executable program itself must invoke the official scorer and write "
                    "all four evaluation-root artifacts. Missing literal markers: "
                    + ", ".join(missing_delivery_markers)
                )
            forbidden_delivery_patterns = (
                "fallback_summary",
                "run_official_or_fallback",
            )
            found_forbidden_delivery = [
                marker for marker in forbidden_delivery_patterns if marker in combined_code
            ]
            if "run_psydefdetect_local_score.py" in files:
                found_forbidden_delivery.append(
                    "generated run_psydefdetect_local_score.py shadows the mounted official scorer"
                )
            if found_forbidden_delivery:
                critical.append(
                    "[main.py] PsyDefDetect framework-owned delivery must call the mounted official "
                    "scorer with complete CLI arguments and use its JSON output without fallback or "
                    "a generated scorer substitute. Forbidden patterns: "
                    + ", ".join(found_forbidden_delivery)
                )
            main_code = files.get("main.py", "")
            try:
                main_tree = ast.parse(main_code)
            except SyntaxError:
                main_tree = None
            if main_tree is not None:
                subprocess_runs = []
                uses_runpy = False
                string_constants = []
                dict_nodes = []
                for node in ast.walk(main_tree):
                    if isinstance(node, ast.Constant) and isinstance(node.value, str):
                        string_constants.append(node.value.lower())
                    if isinstance(node, ast.Dict):
                        dict_nodes.append(node)
                    if isinstance(node, ast.Import):
                        if any(alias.name.split(".")[0] == "runpy" for alias in node.names):
                            uses_runpy = True
                    if isinstance(node, ast.ImportFrom) and node.module:
                        if node.module.split(".")[0] == "runpy":
                            uses_runpy = True
                    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                        continue
                    if isinstance(node.func.value, ast.Name) and node.func.value.id == "runpy":
                        uses_runpy = True
                    if (
                        isinstance(node.func.value, ast.Name)
                        and node.func.value.id == "subprocess"
                        and node.func.attr == "run"
                    ):
                        subprocess_runs.append(node)
                if uses_runpy:
                    critical.append(
                        "[main.py] PsyDefDetect official scorer must run through subprocess.run; "
                        "runpy/in-process execution is forbidden"
                    )
                checked_runs = [
                    call for call in subprocess_runs
                    if any(
                        keyword.arg == "check"
                        and isinstance(keyword.value, ast.Constant)
                        and keyword.value.value is True
                        for keyword in call.keywords
                    )
                ]
                if not checked_runs:
                    critical.append(
                        "[main.py] Missing subprocess.run(..., check=True) official scorer call"
                    )
                if any(
                    "placeholder" in value or "fallback" in value
                    for value in string_constants
                ):
                    critical.append(
                        "[main.py] Scorer failure must abort the experiment; placeholder/fallback "
                        "score paths are forbidden"
                    )
                none_score_literals = []
                trace_contract_found = False
                required_trace_keys = {
                    "experiments",
                    "selected_experiment_id",
                    "framework_native_execution",
                    "consumed_topic_input",
                    "workspace_trace_root",
                    "framework_internal_model",
                    "framework_internal_api_base_url",
                }
                for dict_node in dict_nodes:
                    literal_items = {
                        key.value: value
                        for key, value in zip(dict_node.keys, dict_node.values)
                        if isinstance(key, ast.Constant) and isinstance(key.value, str)
                    }
                    if required_trace_keys.issubset(literal_items):
                        trace_contract_found = True
                    score_literal = literal_items.get("psydefdetect_score")
                    if isinstance(score_literal, ast.Constant) and score_literal.value is None:
                        none_score_literals.append(dict_node)
                if none_score_literals:
                    critical.append(
                        "[main.py] psydefdetect_score may not be assigned a None/null placeholder"
                    )
                if not trace_contract_found:
                    critical.append(
                        "[main.py] No actual trace payload dictionary contains the complete "
                        "PsyDefDetect top-level contract"
                    )
        for fname, code in files.items():'''
if old not in text:
    raise SystemExit("AutoResearchClaw strict-import insertion point not found")
text = text.replace(old, new, 1)
old = '''        if self._cfg.review_max_rounds > 0:
            best.files, review_rounds = self._phase4_review(
                best.files, topic, exp_plan, metric,
            )

        elapsed = time.time() - t0'''
new = '''        if self._cfg.review_max_rounds > 0:
            best.files, review_rounds = self._phase4_review(
                best.files, topic, exp_plan, metric,
            )

        if self._cfg.hard_validation and best.files:
            best.files = self._hard_validate_and_repair(
                best.files, topic, exp_plan, metric, pkg_hint, arch_spec,
            )

        elapsed = time.time() - t0'''
if old not in text:
    raise SystemExit("AutoResearchClaw final CodeAgent validation insertion point not found")
code_agent_path.write_text(text.replace(old, new, 1), encoding="utf-8")

generation_path = Path(sys.argv[6])
text = generation_path.read_text(encoding="utf-8")
if "import ast\n" not in text:
    text = text.replace("import json\n", "import ast\nimport json\n", 1)
old = '    if critical_deep and llm is not None:\n'
new = '    if critical_deep and llm is not None and "psydefdetect" not in config.research.topic.lower():\n'
if text.count(old) != 1:
    raise SystemExit("AutoResearchClaw generic deep-repair guard insertion point changed")
text = text.replace(old, new, 1)
old = '''    # --- Validate each file + auto-repair loop ---
    all_valid = True
    attempt = 0
    for fname, code in list(files.items()):'''
new = '''    # CodeAgent already applies the stricter Topic 4 scorer/trace contract.
    # The generic per-file repair treats subprocess scorer calls as unsafe and
    # removes them, so retain the CodeAgent-validated files for PsyDefDetect.
    all_valid = True
    attempt = 0
    files_to_generic_repair = (
        [] if "psydefdetect" in config.research.topic.lower() else list(files.items())
    )
    for fname, code in files_to_generic_repair:'''
if old not in text:
    raise SystemExit("AutoResearchClaw PsyDefDetect generic-repair guard insertion point not found")
text = text.replace(old, new, 1)
old = '''    alignment_ok = True
    alignment_note = ""
    if llm is not None:
        # Build structured code summary for alignment check'''
new = '''    alignment_ok = True
    alignment_note = ""
    if llm is not None and "psydefdetect" not in config.research.topic.lower():
        # Build structured code summary for alignment check'''
if old not in text:
    raise SystemExit("AutoResearchClaw PsyDefDetect alignment-repair guard insertion point not found")
text = text.replace(old, new, 1)
old = '    if llm is not None and main_code and "condition" in main_code.lower():\n'
new = '    if (\n        llm is not None\n        and "psydefdetect" not in config.research.topic.lower()\n        and main_code\n        and "condition" in main_code.lower()\n    ):\n'
if old not in text:
    raise SystemExit("AutoResearchClaw PsyDefDetect ablation-repair guard insertion point not found")
text = text.replace(old, new, 1)
old = '''    # --- Compute budget hint ---
    time_budget_sec = config.experiment.time_budget_sec'''
new = '''    if "psydefdetect" in config.research.topic.lower():
        pkg_hint = (
            "\\nPSYDEFDETECT PACKAGE CONTRACT: Experiment code may use only Python standard "
            "library, numpy, pandas, and scikit-learn. Do not import statsmodels, torch, "
            "transformers, or any package outside config.experiment.sandbox.allowed_imports. "
            "Do not add optional significance-test dependencies; compute only the required "
            "macro-F1/accuracy evidence with scikit-learn. The generated main.py MUST run "
            "exactly two conditions and call /workspace/automation/scripts/"
            "run_psydefdetect_local_score.py for each through subprocess.run(..., check=True) "
            "with --dataset-root, --split-manifest, --predictions, and --output-score. It MUST "
            "select by the returned psydefdetect_score and write /workspace/predictions.jsonl, "
            "/workspace/score.json, /workspace/experiment_trace.json, and "
            "/workspace/final_report.md itself. The trace MUST include both experiment_id and "
            "scorer_command values, selected_experiment_id, framework_native_execution=true, "
            "consumed_topic_input=true, workspace_trace_root=/workspace, and provider values "
            "read from OPENAI_MODEL and OPENAI_BASE_URL. No fallback scorer is allowed.\\n"
        )

    # --- Compute budget hint ---
    time_budget_sec = config.experiment.time_budget_sec'''
if old not in text:
    raise SystemExit("AutoResearchClaw package-guidance insertion point not found")
text = text.replace(old, new, 1)
old = '''    # --- Write spec ---
    file_list = ", ".join(f"`{f}`" for f in sorted(files.keys()))'''
new = '''    if "psydefdetect" in config.research.topic.lower():
        allowed_imports = set(config.experiment.sandbox.allowed_imports)
        allowed_imports.update(getattr(__import__("sys"), "stdlib_module_names", ()))
        allowed_imports.update(
            fname.replace(".py", "") for fname in files if fname.endswith(".py")
        )
        invalid_imports = []
        for fname, code in files.items():
            if not fname.endswith(".py"):
                continue
            try:
                tree = ast.parse(code)
            except SyntaxError:
                continue
            imported_roots = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported_roots.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported_roots.add(node.module.split(".")[0])
            invalid_imports.extend(
                f"{fname}:{module}" for module in sorted(imported_roots - allowed_imports)
            )
            if "pd.read_json(" in code or "pandas.read_json(" in code:
                invalid_imports.append(f"{fname}:pandas.read_json destroys leading-zero ids")
        if invalid_imports:
            message = "PsyDefDetect generated code still has unsupported imports: " + ", ".join(invalid_imports)
            logger.error("Stage 10: %s", message)
            (stage_dir / "validation_report.md").write_text(
                "# Code Validation Report\\n\\n**Status**: BLOCKED\\n\\n" + message + "\\n",
                encoding="utf-8",
            )
            return StageResult(
                stage=Stage.CODE_GENERATION,
                status=StageStatus.FAILED,
                artifacts=("validation_report.md",),
                evidence_refs=(),
                error=message,
            )

        combined_code = "\\n".join(files.values())
        required_delivery_markers = (
            "/workspace/predictions.jsonl",
            "/workspace/score.json",
            "/workspace/experiment_trace.json",
            "/workspace/final_report.md",
            "/workspace/automation/scripts/run_psydefdetect_local_score.py",
            "--dataset-root",
            "--split-manifest",
            "--predictions",
            "--output-score",
            "psydefdetect_score",
            "score_key",
            "experiments",
            "experiment_id",
            "scorer_command",
            "selected_experiment_id",
            "framework_native_execution",
            "consumed_topic_input",
            "workspace_trace_root",
            "framework_internal_model",
            "framework_internal_api_base_url",
            "OPENAI_MODEL",
            "OPENAI_BASE_URL",
        )
        missing_delivery_markers = [
            marker for marker in required_delivery_markers if marker not in combined_code
        ]
        if missing_delivery_markers:
            message = (
                "PsyDefDetect generated code lacks framework-owned delivery markers after repair: "
                + ", ".join(missing_delivery_markers)
            )
            logger.error("Stage 10: %s", message)
            (stage_dir / "validation_report.md").write_text(
                "# Code Validation Report\\n\\n**Status**: BLOCKED\\n\\n" + message + "\\n",
                encoding="utf-8",
            )
            return StageResult(
                stage=Stage.CODE_GENERATION,
                status=StageStatus.FAILED,
                artifacts=("validation_report.md",),
                evidence_refs=(),
                error=message,
            )

        forbidden_delivery_patterns = (
            "fallback_summary",
            "run_official_or_fallback",
            "placeholder",
            "runpy",
        )
        found_forbidden_delivery = [
            marker for marker in forbidden_delivery_patterns if marker in combined_code
        ]
        if "run_psydefdetect_local_score.py" in files:
            found_forbidden_delivery.append(
                "generated run_psydefdetect_local_score.py shadows the mounted official scorer"
            )
        if found_forbidden_delivery:
            message = (
                "PsyDefDetect generated code still substitutes or falls back from the mounted "
                "official scorer: " + ", ".join(found_forbidden_delivery)
            )
            logger.error("Stage 10: %s", message)
            (stage_dir / "validation_report.md").write_text(
                "# Code Validation Report\\n\\n**Status**: BLOCKED\\n\\n" + message + "\\n",
                encoding="utf-8",
            )
            return StageResult(
                stage=Stage.CODE_GENERATION,
                status=StageStatus.FAILED,
                artifacts=("validation_report.md",),
                evidence_refs=(),
                error=message,
            )

        delivery_semantic_errors = []
        main_code = files.get("main.py", "")
        try:
            main_tree = ast.parse(main_code)
        except SyntaxError:
            main_tree = None
        if main_tree is not None:
            subprocess_runs = [
                node for node in ast.walk(main_tree)
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "subprocess"
                and node.func.attr == "run"
            ]
            checked_runs = [
                call for call in subprocess_runs
                if any(
                    keyword.arg == "check"
                    and isinstance(keyword.value, ast.Constant)
                    and keyword.value.value is True
                    for keyword in call.keywords
                )
            ]
            if not checked_runs:
                delivery_semantic_errors.append(
                    "missing subprocess.run(..., check=True) scorer call"
                )
            required_trace_keys = {
                "experiments",
                "selected_experiment_id",
                "framework_native_execution",
                "consumed_topic_input",
                "workspace_trace_root",
                "framework_internal_model",
                "framework_internal_api_base_url",
            }
            trace_contract_found = False
            none_score_found = False
            for dict_node in (
                node for node in ast.walk(main_tree) if isinstance(node, ast.Dict)
            ):
                literal_items = {
                    key.value: value
                    for key, value in zip(dict_node.keys, dict_node.values)
                    if isinstance(key, ast.Constant) and isinstance(key.value, str)
                }
                if required_trace_keys.issubset(literal_items):
                    trace_contract_found = True
                score_literal = literal_items.get("psydefdetect_score")
                if isinstance(score_literal, ast.Constant) and score_literal.value is None:
                    none_score_found = True
            if not trace_contract_found:
                delivery_semantic_errors.append(
                    "no trace payload dictionary has the complete top-level contract"
                )
            if none_score_found:
                delivery_semantic_errors.append(
                    "psydefdetect_score has a None/null placeholder"
                )
        if delivery_semantic_errors:
            message = (
                "PsyDefDetect generated code failed final scorer/trace AST validation: "
                + "; ".join(delivery_semantic_errors)
            )
            logger.error("Stage 10: %s", message)
            (stage_dir / "validation_report.md").write_text(
                "# Code Validation Report\\n\\n**Status**: BLOCKED\\n\\n" + message + "\\n",
                encoding="utf-8",
            )
            return StageResult(
                stage=Stage.CODE_GENERATION,
                status=StageStatus.FAILED,
                artifacts=("validation_report.md",),
                evidence_refs=(),
                error=message,
            )

    # --- Write spec ---
    file_list = ", ".join(f"`{f}`" for f in sorted(files.keys()))'''
if old not in text:
    raise SystemExit("AutoResearchClaw final strict-import gate insertion point not found")
generation_path.write_text(text.replace(old, new, 1), encoding="utf-8")

literature_path = Path(sys.argv[7])
text = literature_path.read_text(encoding="utf-8")
old = '''    # Rebuild candidates_text from filtered rows
    candidates_text = "\\n".join(
        json.dumps(r, ensure_ascii=False) for r in filtered_rows
    )'''
new = '''    # PsyDefDetect's CLI topic includes runtime constraints, so generic token
    # overlap retains broad ML and medical papers. Rank all framework-collected
    # candidates with task-specific domain phrases before asking the LLM.
    candidates_before_projection = len(filtered_rows)
    if "psydefdetect" in config.research.topic.lower():
        projection_rows = _parse_jsonl_rows(
            _read_prior_artifact(run_dir, "candidates.jsonl") or ""
        )
        candidates_before_projection = len(projection_rows)
        for row in projection_rows:
            abstract = row.get("abstract", "")
            if isinstance(abstract, str) and len(abstract) > _MAX_ABSTRACT_LEN:
                row["abstract"] = abstract[:_MAX_ABSTRACT_LEN] + "..."
            row.pop("authors", None)
        direct_phrases = (
            "psydefdetect",
            "psychological defense mechanism",
            "psychological defence mechanism",
            "defense mechanism classification",
            "defence mechanism classification",
        )
        therapy_phrases = (
            "psychotherapy", "psychotherapeutic", "counseling", "counselling",
            "supportive conversation", "therapeutic dialogue",
        )
        nlp_phrases = (
            "natural language processing", "clinical nlp", "text classification",
            "language model", "dialogue classification", "conversation",
        )
        ranked_rows: list[tuple[int, int, str, dict[str, Any]]] = []
        for row in projection_rows:
            title = str(row.get("title", "")).lower()
            abstract = str(row.get("abstract", "")).lower()
            blob = f"{title} {abstract}"
            score = 0
            if "psydefdetect" in title:
                score += 240
            elif "psydefdetect" in blob:
                score += 180
            for phrase in direct_phrases[1:]:
                if phrase in title:
                    score += 120
                elif phrase in abstract:
                    score += 80
            therapy_hits = sum(1 for phrase in therapy_phrases if phrase in blob)
            nlp_hits = sum(1 for phrase in nlp_phrases if phrase in blob)
            if therapy_hits and nlp_hits:
                score += 35 + min(therapy_hits, 3) * 5 + min(nlp_hits, 3) * 5
            elif therapy_hits:
                score += min(therapy_hits, 3) * 8
            if ("mental health" in blob or "clinical psychology" in blob) and nlp_hits:
                score += 25 + min(nlp_hits, 3) * 5
            if str(row.get("source", "")) == "seminal_library":
                score += 20
            if score <= 0:
                continue
            row["psydefdetect_relevance_score"] = score
            citations = int(row.get("citation_count") or 0)
            ranked_rows.append((score, citations, title, row))
        ranked_rows.sort(key=lambda item: (-item[0], -item[1], item[2]))
        filtered_rows = [item[3] for item in ranked_rows[:40]]
        logger.info(
            "PsyDefDetect candidate projection: selected %d of %d candidates",
            len(filtered_rows), candidates_before_projection,
        )

    # Rebuild candidates_text from filtered rows
    candidates_text = "\\n".join(
        json.dumps(r, ensure_ascii=False) for r in filtered_rows
    )'''
if old not in text:
    raise SystemExit("AutoResearchClaw PsyDefDetect literature projection insertion point not found")
text = text.replace(old, new, 1)
old = '''        resp = _chat_with_prompt(
            llm,
            sp.system,
            sp.user,
            json_mode=sp.json_mode,
            max_tokens=sp.max_tokens,
        )
        payload = _safe_json_loads(resp.content, {})
        raw = payload.get("shortlist") if isinstance(payload, dict) else None
        if isinstance(raw, list):
            if len(raw) == 0:
                # Distinguish a valid strict-screen empty result from a
                # malformed list whose entries are not dicts.
                model_rejected_all = True
            else:
                shortlist = [row for row in raw if isinstance(row, dict)]
                if not shortlist:
                    parse_failed = True
        else:
            parse_failed = True'''
new = '''        candidate_by_title = {
            str(row.get("title", "")).strip().lower(): row
            for row in filtered_rows
            if str(row.get("title", "")).strip()
        }
        screen_attempts = 0
        for screen_attempt in (1, 2):
            screen_attempts = screen_attempt
            user_prompt = sp.user
            if screen_attempt == 2:
                user_prompt += (
                    "\\n\\nRETRY AFTER EMPTY OR INVALID SHORTLIST: Re-screen the same compact "
                    "candidate projection. Return one valid JSON object with a non-empty "
                    "shortlist of 15 to 25 supplied papers. PsyDefDetect shared-task papers, "
                    "psychological defense-mechanism studies, and directly applicable "
                    "psychotherapy or clinical-NLP classification papers qualify. Preserve "
                    "their original fields and do not invent papers."
                )
            resp = _chat_with_prompt(
                llm,
                sp.system,
                user_prompt,
                json_mode=sp.json_mode,
                max_tokens=sp.max_tokens,
            )
            payload = _safe_json_loads(resp.content, {})
            raw = payload.get("shortlist") if isinstance(payload, dict) else None
            model_rejected_all = isinstance(raw, list) and len(raw) == 0
            parse_failed = not isinstance(raw, list)
            if isinstance(raw, list) and raw:
                shortlist = []
                for selected_row in raw:
                    if not isinstance(selected_row, dict):
                        continue
                    title_key = str(selected_row.get("title", "")).strip().lower()
                    candidate = candidate_by_title.get(title_key)
                    if candidate is None:
                        continue
                    validated_row = dict(candidate)
                    for field in ("relevance_score", "quality_score", "keep_reason"):
                        if field in selected_row:
                            validated_row[field] = selected_row[field]
                    shortlist.append(validated_row)
                shortlist = shortlist[:25]
                parse_failed = not shortlist
            if shortlist:
                break
            if screen_attempt == 1:
                logger.warning(
                    "Stage 5: first screening returned no valid shortlist; "
                    "retrying once through the framework LLM client"
                )'''
if old not in text:
    raise SystemExit("AutoResearchClaw PsyDefDetect literature retry insertion point not found")
text = text.replace(old, new, 1)
old = '''                    "candidates_screened": len(filtered_rows),
                    "shortlist_size": 0,
                    "note": (
                        "Strict screen returned empty shortlist. Pipeline paused; "'''
new = '''                    "candidates_before_projection": candidates_before_projection,
                    "candidates_screened": len(filtered_rows),
                    "screen_attempts": screen_attempts,
                    "shortlist_size": 0,
                    "note": (
                        "Two framework-owned screens returned an empty shortlist. Pipeline paused; "'''
if old not in text:
    raise SystemExit("AutoResearchClaw empty-screen evidence insertion point not found")
text = text.replace(old, new, 1)
old = '''    out = stage_dir / "shortlist.jsonl"
    _write_jsonl(out, shortlist)
    return StageResult(
        stage=Stage.LITERATURE_SCREEN,
        status=StageStatus.DONE,
        artifacts=("shortlist.jsonl",),
        evidence_refs=("stage-05/shortlist.jsonl",),
    )'''
new = '''    out = stage_dir / "shortlist.jsonl"
    _write_jsonl(out, shortlist)
    (stage_dir / "screen_meta.json").write_text(
        json.dumps(
            {
                "outcome": "shortlist_selected",
                "candidates_before_projection": candidates_before_projection,
                "candidates_screened": len(filtered_rows),
                "screen_attempts": screen_attempts if llm is not None else 0,
                "shortlist_size": len(shortlist),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return StageResult(
        stage=Stage.LITERATURE_SCREEN,
        status=StageStatus.DONE,
        artifacts=("shortlist.jsonl", "screen_meta.json"),
        evidence_refs=("stage-05/shortlist.jsonl", "stage-05/screen_meta.json"),
    )'''
if old not in text:
    raise SystemExit("AutoResearchClaw literature evidence insertion point not found")
literature_path.write_text(text.replace(old, new, 1), encoding="utf-8")

agentic_sandbox_path = Path(sys.argv[8])
text = agentic_sandbox_path.read_text(encoding="utf-8")
old = '''                    # Flatten metrics from various common formats
                    raw = data.get("metrics", data)
                    for k, v in raw.items():
                        try:
                            metrics[k] = float(v)
                        except (TypeError, ValueError):
                            pass'''
new = '''                    # PsyDefDetect experiment programs may emit the documented
                    # per-condition schema instead of a flat metrics object.
                    raw = data.get("metrics")
                    if not isinstance(raw, dict):
                        raw = data.get("conditions", data)
                    leaf_values: dict[str, list[float]] = {}

                    def collect_metrics(prefix: str, value: object) -> None:
                        if isinstance(value, bool):
                            return
                        if isinstance(value, (int, float)):
                            metric_value = float(value)
                            metrics[prefix] = metric_value
                            leaf_key = prefix.rsplit("/", 1)[-1]
                            leaf_values.setdefault(leaf_key, []).append(metric_value)
                            return
                        if isinstance(value, dict):
                            for key, nested in value.items():
                                nested_prefix = f"{prefix}/{key}" if prefix else str(key)
                                collect_metrics(nested_prefix, nested)

                    collect_metrics("", raw)
                    # PsyDefDetect's primary metric is maximized. Expose the best
                    # condition value under its unqualified key for ExperimentRunner.
                    for key, values in leaf_values.items():
                        if values:
                            metrics.setdefault(key, max(values))'''
if old not in text:
    raise SystemExit("AutoResearchClaw structured-results parser insertion point not found")
agentic_sandbox_path.write_text(text.replace(old, new, 1), encoding="utf-8")

sandbox_path = Path(sys.argv[9])
text = sandbox_path.read_text(encoding="utf-8")
if "import json\n" not in text:
    text = text.replace("import logging\n", "import json\nimport logging\n", 1)
old = '''            result = self._result_from_completed(
                completed, elapsed_sec=time.monotonic() - start
            )'''
new = '''            result = self._result_from_completed(
                completed,
                elapsed_sec=time.monotonic() - start,
                results_path=self.workdir / "results.json",
            )'''
if text.count(old) != 2:
    raise SystemExit("AutoResearchClaw ExperimentSandbox completion call shape changed")
text = text.replace(old, new, 1)
new = '''            result = self._result_from_completed(
                completed,
                elapsed_sec=time.monotonic() - start,
                results_path=sandbox_project / "results.json",
            )'''
text = text.replace(old, new, 1)
old = '''    def _result_from_completed(
        completed: subprocess.CompletedProcess[str], *, elapsed_sec: float
    ) -> SandboxResult:
        metrics = parse_metrics(completed.stdout)'''
new = '''    def _result_from_completed(
        completed: subprocess.CompletedProcess[str], *, elapsed_sec: float,
        results_path: Path | None = None,
    ) -> SandboxResult:
        metrics = parse_metrics(completed.stdout)
        if results_path is not None and results_path.exists():
            try:
                structured = json.loads(results_path.read_text(encoding="utf-8"))
                raw = structured.get("metrics", structured) if isinstance(structured, dict) else structured
                leaf_values: dict[str, list[float]] = {}

                def collect_metrics(prefix: str, value: object) -> None:
                    if isinstance(value, bool):
                        return
                    if isinstance(value, (int, float)):
                        metric_value = float(value)
                        metrics[prefix] = metric_value
                        leaf_key = prefix.rsplit("/", 1)[-1]
                        leaf_values.setdefault(leaf_key, []).append(metric_value)
                        return
                    if isinstance(value, dict):
                        for key, nested in value.items():
                            if key in {"condition_name", "metric_source"}:
                                continue
                            nested_prefix = f"{prefix}/{key}" if prefix else str(key)
                            collect_metrics(nested_prefix, nested)
                        return
                    if isinstance(value, list):
                        for index, nested in enumerate(value):
                            condition = (
                                nested.get("condition_name")
                                if isinstance(nested, dict)
                                else None
                            )
                            nested_prefix = str(condition or f"item_{index + 1}")
                            collect_metrics(nested_prefix, nested)

                collect_metrics("", raw)
                for key, values in leaf_values.items():
                    if values:
                        metrics.setdefault(key, max(values))
            except (json.JSONDecodeError, OSError):
                pass'''
if old not in text:
    raise SystemExit("AutoResearchClaw ExperimentSandbox structured-results insertion point not found")
sandbox_path.write_text(text.replace(old, new, 1), encoding="utf-8")

execution_path = Path(sys.argv[10])
text = execution_path.read_text(encoding="utf-8")
old = '''                ),
            )
    return StageResult(
        stage=Stage.EXPERIMENT_RUN,
        status=StageStatus.DONE,
        artifacts=("runs/",),
        evidence_refs=("stage-12/runs/",),
    )'''
new = '''                ),
            )

    if "psydefdetect" in config.research.topic.lower():
        handoff_errors: list[str] = []
        workspace_root = Path("/workspace")
        prediction_paths = (
            workspace_root / "predictions.jsonl",
            workspace_root / "submission.csv",
        )
        if not any(path.is_file() and path.stat().st_size > 0 for path in prediction_paths):
            handoff_errors.append("missing non-empty predictions.jsonl or submission.csv")
        report_path = workspace_root / "final_report.md"
        if not report_path.is_file() or report_path.stat().st_size == 0:
            handoff_errors.append("missing non-empty final_report.md")

        score_payload: dict[str, Any] | None = None
        score_path = workspace_root / "score.json"
        try:
            loaded_score = json.loads(score_path.read_text(encoding="utf-8"))
            if isinstance(loaded_score, dict):
                score_payload = loaded_score
            else:
                handoff_errors.append("score.json must be a JSON object")
        except (OSError, json.JSONDecodeError):
            handoff_errors.append("score.json is missing or invalid JSON")
        score_value = None if score_payload is None else score_payload.get("psydefdetect_score")
        if not isinstance(score_value, (int, float)) or isinstance(score_value, bool):
            handoff_errors.append("score.json must contain numeric psydefdetect_score")
        if score_payload is not None and score_payload.get("score_key") != "psydefdetect_score":
            handoff_errors.append("score.json score_key must equal psydefdetect_score")

        trace_payload: dict[str, Any] | None = None
        trace_path = workspace_root / "experiment_trace.json"
        try:
            loaded_trace = json.loads(trace_path.read_text(encoding="utf-8"))
            if isinstance(loaded_trace, dict):
                trace_payload = loaded_trace
            else:
                handoff_errors.append("experiment_trace.json must be a JSON object")
        except (OSError, json.JSONDecodeError):
            handoff_errors.append("experiment_trace.json is missing or invalid JSON")

        if trace_payload is not None:
            required_values = {
                "framework_native_execution": True,
                "consumed_topic_input": True,
                "workspace_trace_root": "/workspace",
                "framework_internal_model": config.llm.primary_model,
                "framework_internal_api_base_url": config.llm.base_url,
            }
            for key, expected in required_values.items():
                if trace_payload.get(key) != expected:
                    handoff_errors.append(f"experiment_trace.json {key} must equal {expected!r}")
            experiments = trace_payload.get("experiments")
            if not isinstance(experiments, list) or len(experiments) != 2:
                handoff_errors.append("experiment_trace.json must contain exactly two experiments")
            else:
                experiment_ids = [
                    item.get("experiment_id") if isinstance(item, dict) else None
                    for item in experiments
                ]
                if any(not isinstance(item_id, str) or not item_id for item_id in experiment_ids):
                    handoff_errors.append("every experiment must contain a non-empty experiment_id")
                elif len(set(experiment_ids)) != 2:
                    handoff_errors.append("experiment ids must be unique")
                selected_id = trace_payload.get("selected_experiment_id")
                if selected_id not in experiment_ids:
                    handoff_errors.append("selected_experiment_id must identify one experiment")
                for item in experiments:
                    if not isinstance(item, dict):
                        continue
                    metric_value = item.get("psydefdetect_score")
                    if not isinstance(metric_value, (int, float)) or isinstance(metric_value, bool):
                        handoff_errors.append(
                            f"experiment {item.get('experiment_id')!r} lacks numeric psydefdetect_score"
                        )
                    scorer_command = item.get("scorer_command")
                    if not isinstance(scorer_command, list) or not any(
                        str(part) == "/workspace/automation/scripts/run_psydefdetect_local_score.py"
                        for part in scorer_command
                    ):
                        handoff_errors.append(
                            f"experiment {item.get('experiment_id')!r} lacks official scorer_command evidence"
                        )
                if isinstance(score_value, (int, float)) and not isinstance(score_value, bool):
                    selected_records = [
                        item for item in experiments
                        if isinstance(item, dict) and item.get("experiment_id") == selected_id
                    ]
                    if selected_records:
                        selected_score = selected_records[0].get("psydefdetect_score")
                        if not isinstance(selected_score, (int, float)) or abs(
                            float(selected_score) - float(score_value)
                        ) > 1e-12:
                            handoff_errors.append(
                                "score.json must equal the selected experiment official score"
                            )

        (stage_dir / "psydefdetect_handoff_validation.json").write_text(
            json.dumps(
                {
                    "status": "valid" if not handoff_errors else "invalid",
                    "errors": handoff_errors,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        if handoff_errors:
            logger.error(
                "Stage 12: PsyDefDetect framework handoff is invalid: %s",
                "; ".join(handoff_errors),
            )
            return StageResult(
                stage=Stage.EXPERIMENT_RUN,
                status=StageStatus.FAILED,
                artifacts=("runs/", "psydefdetect_handoff_validation.json"),
                evidence_refs=("stage-12/runs/", "stage-12/psydefdetect_handoff_validation.json"),
                error="PsyDefDetect framework-generated handoff failed contract validation",
            )

    return StageResult(
        stage=Stage.EXPERIMENT_RUN,
        status=StageStatus.DONE,
        artifacts=(
            ("runs/", "psydefdetect_handoff_validation.json")
            if "psydefdetect" in config.research.topic.lower()
            else ("runs/",)
        ),
        evidence_refs=(
            ("stage-12/runs/", "stage-12/psydefdetect_handoff_validation.json")
            if "psydefdetect" in config.research.topic.lower()
            else ("stage-12/runs/",)
        ),
    )'''
if old not in text:
    raise SystemExit("AutoResearchClaw Stage 12 handoff-validation insertion point not found")
text = text.replace(old, new, 1)

old = '''    from researchclaw.experiment.factory import create_sandbox
    from researchclaw.experiment.validator import format_issues_for_llm, validate_code

    def _to_float(value: Any) -> float | None:'''
new = '''    from researchclaw.experiment.factory import create_sandbox
    from researchclaw.experiment.validator import format_issues_for_llm, validate_code

    if "psydefdetect" in config.research.topic.lower():
        import shutil

        source_dir_text = _read_prior_artifact(run_dir, "experiment/")
        source_dir = Path(source_dir_text) if source_dir_text else None
        final_dir = stage_dir / "experiment_final"
        if source_dir is None or not source_dir.is_dir():
            return StageResult(
                stage=Stage.ITERATIVE_REFINE,
                status=StageStatus.FAILED,
                artifacts=(),
                error="PsyDefDetect Stage 10 experiment project is unavailable",
            )
        if final_dir.exists():
            shutil.rmtree(final_dir)
        shutil.copytree(source_dir, final_dir)
        log = {
            "generated": _utcnow_iso(),
            "mode": config.experiment.mode,
            "skipped": True,
            "skip_reason": (
                "PsyDefDetect fixed contract completed exactly two framework-owned "
                "experiments in Stage 12; additional refinement runs are not authorized"
            ),
            "metric_key": config.experiment.metric_key,
            "experiments_completed": 2,
        }
        (stage_dir / "refinement_log.json").write_text(
            json.dumps(log, indent=2), encoding="utf-8"
        )
        return StageResult(
            stage=Stage.ITERATIVE_REFINE,
            status=StageStatus.DONE,
            artifacts=("refinement_log.json", "experiment_final/"),
            evidence_refs=("stage-13/refinement_log.json",),
        )

    def _to_float(value: Any) -> float | None:'''
if old not in text:
    raise SystemExit("AutoResearchClaw PsyDefDetect no-extra-refinement insertion point not found")
execution_path.write_text(text.replace(old, new, 1), encoding="utf-8")

analysis_path = Path(sys.argv[11])
text = analysis_path.read_text(encoding="utf-8")
old = '''        _user = sp.user + _degenerate_hint + _diagnosis_hint + _ablation_refine_hint
        resp = _chat_with_prompt(llm, sp.system, _user)'''
new = '''        _fixed_contract_hint = ""
        if "psydefdetect" in config.research.topic.lower():
            _fixed_contract_hint = (
                "\\n\\nPSYDEFDETECT FIXED EXECUTION BUDGET: Stage 12 already completed and "
                "validated exactly two authorized experiments, and the framework selected and "
                "promoted the higher official score. Additional conditions, repeated seeds, "
                "refinement executions, or pivots are forbidden by this evaluation contract. "
                "Base the research decision on the completed evidence and choose PROCEED; record "
                "limitations in the paper instead of requesting REFINE or PIVOT.\\n"
            )
        _user = (
            sp.user + _degenerate_hint + _diagnosis_hint + _ablation_refine_hint
            + _fixed_contract_hint
        )
        resp = _chat_with_prompt(llm, sp.system, _user)'''
if old not in text:
    raise SystemExit("AutoResearchClaw PsyDefDetect proceed-hint insertion point not found")
analysis_path.write_text(text.replace(old, new, 1), encoding="utf-8")
PY
topic="$(tr '\n' ' ' < topic.psydefdetect.txt)"
output="artifacts/psydefdetect-${REAL_EVAL_RUN_ID}"
mkdir -p "$output"
cat > "$output/execution_contract.md" <<'BRIEF'
The AutoResearchClaw pipeline owns planning, experiment execution, comparison, selection, and final delivery. Run exactly 2 materially different experiments on the fixed PsyDefDetect split, each exactly once, then immediately select and promote the better valid result. Do not add repeated seeds, refinements, pivots, ablations, or extra experimental runs after those two executions. For each condition, invoke /workspace/automation/scripts/run_psydefdetect_local_score.py with --dataset-root, --split-manifest, --predictions, and --output-score; generated scorer substitutes and fallback summaries are invalid. Before exiting, the framework must write root-level /workspace/predictions.jsonl or /workspace/submission.csv, /workspace/score.json, /workspace/experiment_trace.json, and /workspace/final_report.md. score.json must retain numeric psydefdetect_score and score_key from the official scorer. experiment_trace.json must contain exactly two experiments with unique experiment_id, numeric psydefdetect_score, complete scorer_command, and selected_experiment_id, plus framework_native_execution=true, consumed_topic_input=true, workspace_trace_root=/workspace, framework_internal_model from OPENAI_MODEL, and framework_internal_api_base_url from OPENAI_BASE_URL. The host will validate but not promote or supplement framework artifacts.
BRIEF
timeout "${AUTORESEARCHCLAW_PSYDEFDETECT_TIMEOUT_SECONDS:-10800}s" \
  python3 -m researchclaw.cli run \
  --config config.psydefdetect.yaml \
  --topic "$topic. Run exactly two fixed-split experiments using only installed numpy, pandas, and scikit-learn components; do not download or import pretrained models. Read automation/psydefdetect_contract.md, automation/psydefdetect_execution_budget.md, and $output/execution_contract.md. Use only /data/psydefdetect and the injected evaluation provider." \
  --output "$output" \
  --auto-approve
EOF
)
exec "$ROOT"/real_eval/scripts/psydefdetect_framework_fullrun.sh
