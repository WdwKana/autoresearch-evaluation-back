from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "automation/scripts/generate_psydefdetect_native_inputs.py"


def test_generate_psydefdetect_native_inputs_writes_split_and_scorer(tmp_path: Path) -> None:
    output_root = tmp_path / "pack"
    subprocess.run(
        [
            "python3",
            str(SCRIPT),
            "--output-root",
            str(output_root),
            "--dataset-root",
            str(ROOT / "data/psydefdetect"),
            "--contract-file",
            str(ROOT / "automation/psydefdetect_contract.md"),
            "--provider-base-url",
            "https://example.invalid/v1",
            "--primary-model",
            "gpt-5.4",
        ],
        check=True,
        cwd=ROOT,
    )

    split = json.loads((output_root / "automation/psydefdetect_split.json").read_text(encoding="utf-8"))
    assert split["topic"] == "psydefdetect"
    assert split["seed"] == 42
    assert split["train_record_count"] > 0
    assert split["eval_record_count"] > 0
    assert (output_root / "automation/scripts/run_psydefdetect_local_score.py").exists()
    assert (output_root / "automation/psydefdetect_runtime_brief.md").exists()
    assert "Do not rely on downloading new Hugging Face models during runtime" in (
        output_root / "automation/psydefdetect_runtime_brief.md"
    ).read_text(encoding="utf-8")
    assert (output_root / "docs/psydefdetect_experiment_requirements.md").exists()
    assert (output_root / "AI-Researcher/benchmark/final/psydefdetect/psydefdetect.json").exists()
    assert (output_root / "AI-Researcher/benchmark/process/dataset_candidate/psydefdetect/metaprompt.py").exists()
    ai_scientist_topic = (
        output_root / "AI-Scientist-v2/ai_scientist/ideas/psydefdetect_topic.md"
    ).read_text(encoding="utf-8")
    assert 'framework_internal_model: "gpt-5.4"' in ai_scientist_topic
    assert 'framework_internal_api_base_url: "https://example.invalid/v1"' in ai_scientist_topic
    assert "kimi-k2.6" not in ai_scientist_topic
    assert (output_root / "Auto-claude-code-research-in-sleep/PSYDEFDETECT_BRIEF.md").exists()
    assert (output_root / "DeepScientist/PSYDEFDETECT_BRIEF.md").exists()
    assert (output_root / "EvoScientist/psydefdetect_start_message.txt").exists()
    arc_config = (output_root / "AutoResearchClaw/config.psydefdetect.yaml").read_text(encoding="utf-8")
    assert 'primary_model: "gpt-5.4"' in arc_config
    assert 'base_url: "https://example.invalid/v1"' in arc_config
    assert 'metric_key: "macro_f1_positive"' in arc_config
    assert 'metric_direction: "maximize"' in arc_config
    arc_code_prompt = (
        output_root / "AutoResearchClaw/evaluation_prompts/psydefdetect_code_generation.md"
    ).read_text(encoding="utf-8")
    assert "/workspace/automation/scripts/run_psydefdetect_local_score.py" in arc_code_prompt
    assert "subprocess.run(..., check=True)" in arc_code_prompt
    assert "let `subprocess.CalledProcessError` propagate" in arc_code_prompt
    assert "Never invoke the scorer in-process through `runpy`" in arc_code_prompt
    assert "No generated Python file may import or call `runpy`" in arc_code_prompt
    assert "write a null/placeholder score" in arc_code_prompt
    assert "never use a fallback summary" in arc_code_prompt
    assert "framework_native_execution: true" in arc_code_prompt
    assert "framework_internal_model" in arc_code_prompt
    assert "exec_fix_max_iterations: 0" in arc_config
    assert "hard_validation_max_repairs: 8" in arc_config
    assert "review_max_rounds: 0" in arc_config
