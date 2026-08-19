from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "automation" / "scripts"))

from generate_arc_wbe_2026_native_inputs import generate_native_inputs  # noqa: E402


def in_root_contract(repo_root: Path) -> Path:
    return repo_root / "automation" / "arc_wbe_2026_contract.md"


def test_generator_builds_manifest_for_all_frameworks(tmp_path: Path) -> None:
    out = tmp_path / "outputs"

    manifest = generate_native_inputs(
        repo_root=tmp_path,
        output_root=out,
        dataset_root=Path("/data/arc"),
        contract_file=in_root_contract(tmp_path),
    )

    assert "AI-Researcher/benchmark/final/arc_wbe_2026/arc_wbe_2026.json" in manifest["files"]
    assert (
        "AI-Researcher/benchmark/process/dataset_candidate/arc_wbe_2026/metaprompt.py"
        in manifest["files"]
    )
    assert "AI-Scientist-v2/ai_scientist/ideas/arc_wbe_2026_topic.md" in manifest["files"]
    assert "Auto-claude-code-research-in-sleep/ARC_WBE_2026_BRIEF.md" in manifest["files"]
    assert "AutoResearchClaw/config.arc.yaml" in manifest["files"]
    assert "DeepScientist/DEEPSCIENTIST_BRIEF.md" in manifest["files"]
    assert "dr-claw/research_brief.json" in manifest["files"]
    assert "EvoScientist/arc_wbe_2026_start_message.txt" in manifest["files"]
    assert manifest["topic"]["label"] == "ARC-WBE-2026"


def test_generator_writes_ai_researcher_arc_metaprompt(tmp_path: Path) -> None:
    out = tmp_path / "outputs"

    generate_native_inputs(
        repo_root=tmp_path,
        output_root=out,
        dataset_root=Path("/data/arc"),
        contract_file=in_root_contract(tmp_path),
    )

    metaprompt = (
        out
        / "AI-Researcher"
        / "benchmark"
        / "process"
        / "dataset_candidate"
        / "arc_wbe_2026"
        / "metaprompt.py"
    ).read_text(encoding="utf-8")
    assert "/data/arc_wbe_2026" in metaprompt
    assert "official-format outputs" in metaprompt
    assert "Do not use unrelated benchmarks" in metaprompt


def test_generator_writes_ai_researcher_metaprompt_with_large_tensor_logging_guard(
    tmp_path: Path,
) -> None:
    out = tmp_path / "outputs"

    generate_native_inputs(
        repo_root=tmp_path,
        output_root=out,
        dataset_root=Path("/data/arc"),
        contract_file=in_root_contract(tmp_path),
    )

    metaprompt = (
        out
        / "AI-Researcher"
        / "benchmark"
        / "process"
        / "dataset_candidate"
        / "arc_wbe_2026"
        / "metaprompt.py"
    ).read_text(encoding="utf-8")
    assert "Do not print raw weights" in metaprompt
    assert "schema, column names, dtypes, shapes, and concise scalar summaries only" in metaprompt


def test_generator_writes_method_free_ai_researcher_payload(tmp_path: Path) -> None:
    out = tmp_path / "outputs"

    generate_native_inputs(
        repo_root=tmp_path,
        output_root=out,
        dataset_root=Path("/data/arc"),
        contract_file=in_root_contract(tmp_path),
    )

    payload = json.loads(
        (
            out / "AI-Researcher" / "benchmark" / "final" / "arc_wbe_2026" / "arc_wbe_2026.json"
        ).read_text(encoding="utf-8")
    )
    assert payload["source_papers"] == []
    assert "framework-chosen experiments" in payload["task1"]
    assert "method choice" in payload["task2"]


def test_generator_requires_pre_experiment_idea_without_prescribing_method(
    tmp_path: Path,
) -> None:
    out = tmp_path / "outputs"

    generate_native_inputs(
        repo_root=tmp_path,
        output_root=out,
        dataset_root=Path("/data/arc"),
        contract_file=in_root_contract(tmp_path),
    )

    prompt_paths = [
        out / "AI-Researcher/benchmark/process/dataset_candidate/arc_wbe_2026/metaprompt.py",
        out / "AI-Scientist-v2/ai_scientist/ideas/arc_wbe_2026_topic.md",
        out / "Auto-claude-code-research-in-sleep/ARC_WBE_2026_BRIEF.md",
        out / "AutoResearchClaw/topic.txt",
        out / "DeepScientist/DEEPSCIENTIST_BRIEF.md",
        out / "EvoScientist/EVOSCIENTIST_BRIEF.md",
    ]
    for path in prompt_paths:
        text = path.read_text(encoding="utf-8")
        assert "research_idea.json" in text
        assert "framework" in text.lower()
        assert "Covariance Propagation" not in text


def test_generator_records_score_fields_in_shared_contract_summary(tmp_path: Path) -> None:
    manifest = generate_native_inputs(
        repo_root=tmp_path,
        output_root=tmp_path / "outputs",
        dataset_root=Path("/data/arc"),
        contract_file=in_root_contract(tmp_path),
    )

    assert manifest["result_fields"] == [
        "score",
        "score_source",
        "score_artifact",
        "submission_artifact",
    ]

    summary = (tmp_path / "outputs" / "docs" / "arc_wbe_2026_summary.md").read_text(
        encoding="utf-8"
    )
    assert "estimator.py" in summary


def test_generator_writes_authoritative_contract_file_contents(tmp_path: Path) -> None:
    out = tmp_path / "outputs"
    contract_file = tmp_path / "automation" / "arc_white_box_estimation_2026_contract.md"
    contract_file.parent.mkdir(parents=True, exist_ok=True)
    contract_body = "# ARC Contract\n\nFULL CONTRACT ONLY MARKER\n"
    contract_file.write_text(contract_body, encoding="utf-8")

    generate_native_inputs(
        repo_root=tmp_path,
        output_root=out,
        dataset_root=Path("/data/arc"),
        contract_file=contract_file,
    )

    generated_contract = (out / "automation" / "arc_wbe_2026_contract.md").read_text(
        encoding="utf-8"
    )
    summary = (out / "docs" / "arc_wbe_2026_summary.md").read_text(encoding="utf-8")

    assert generated_contract == contract_body
    assert generated_contract != summary
    assert "FULL CONTRACT ONLY MARKER" in generated_contract
    assert "FULL CONTRACT ONLY MARKER" not in summary


def test_generator_mounts_in_root_contract_relative_to_supplied_root(tmp_path: Path) -> None:
    output_root = tmp_path / "outputs"
    contract_file = in_root_contract(tmp_path)

    generate_native_inputs(
        repo_root=tmp_path,
        output_root=output_root,
        dataset_root=Path("/data/arc"),
        contract_file=contract_file,
    )

    config = (output_root / "AutoResearchClaw/config.arc.yaml").read_text(encoding="utf-8")
    assert 'contract_file: "/workspace/automation/arc_wbe_2026_contract.md"' in config


def test_generator_mounts_contract_from_symlinked_supplied_root(tmp_path: Path) -> None:
    physical_root = tmp_path / "physical-root"
    physical_root.mkdir()
    symlink_root = tmp_path / "linked-root"
    symlink_root.symlink_to(physical_root, target_is_directory=True)
    output_root = tmp_path / "outputs"
    contract_file = in_root_contract(symlink_root)

    generate_native_inputs(
        repo_root=symlink_root,
        output_root=output_root,
        dataset_root=Path("/data/arc"),
        contract_file=contract_file,
    )

    config = (output_root / "AutoResearchClaw/config.arc.yaml").read_text(encoding="utf-8")
    assert 'contract_file: "/workspace/automation/arc_wbe_2026_contract.md"' in config


def test_generator_rejects_contract_outside_supplied_root(tmp_path: Path) -> None:
    outside_contract = tmp_path.parent / "outside-contract.md"

    try:
        generate_native_inputs(
            repo_root=tmp_path,
            output_root=tmp_path / "outputs",
            dataset_root=Path("/data/arc"),
            contract_file=outside_contract,
        )
    except ValueError as error:
        assert "outside supplied repo root" in str(error)
    else:
        raise AssertionError("expected an outside-root contract to be rejected")


def test_generator_writes_minimal_autoresearchclaw_required_fields(tmp_path: Path) -> None:
    out = tmp_path / "outputs"

    generate_native_inputs(
        repo_root=tmp_path,
        output_root=out,
        dataset_root=Path("/data/arc"),
        contract_file=in_root_contract(tmp_path),
        provider_base_url="https://proxy.example.invalid/v1",
    )

    config_text = (out / "AutoResearchClaw" / "config.arc.yaml").read_text(encoding="utf-8")
    for marker in [
        "runtime:",
        'timezone: "Asia/Shanghai"',
        "notifications:",
        'channel: "none"',
        "knowledge_base:",
        'root: "./knowledge_base"',
        "llm:",
        'primary_model: "gpt-5.4"',
        "fallback_models: []",
        'base_url: "https://proxy.example.invalid/v1"',
        'api_key_env: "OPENAI_API_KEY"',
    ]:
        assert marker in config_text


def test_cli_writes_manifest_and_prints_summary_json(tmp_path: Path) -> None:
    output_root = tmp_path / "arc-pack"
    script = ROOT / "automation" / "scripts" / "generate_arc_wbe_2026_native_inputs.py"

    proc = subprocess.run(
        [
            "python3",
            str(script),
            "--output-root",
            str(output_root),
            "--dataset-root",
            "/data/arc",
            "--contract-file",
            str(ROOT / "automation/arc_wbe_2026_contract.md"),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(proc.stdout)
    assert payload["topic"] == "arc_wbe_2026"
    assert payload["output_root"] == str(output_root)
    assert payload["manifest"] == str(output_root / "arc_wbe_2026_manifest.json")
    assert (output_root / "arc_wbe_2026_manifest.json").exists()
