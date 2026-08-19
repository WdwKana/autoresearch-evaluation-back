from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
HARNESS = REPO_ROOT / "babylm_10m_harness" / "scripts" / "run_proxy_babylm_pipeline.py"


def test_proxy_harness_materializes_expected_artifacts(tmp_path: Path) -> None:
    dataset_root = tmp_path / "dataset"
    dataset_root.mkdir()
    (dataset_root / "sample.train.txt").write_text("a b c\n", encoding="utf-8")
    contract_file = tmp_path / "contract.md"
    contract_file.write_text("# Contract\n", encoding="utf-8")
    output_root = tmp_path / "output"

    proc = subprocess.run(
        [
            sys.executable,
            str(HARNESS),
            "--framework",
            "dr-claw",
            "--output-root",
            str(output_root),
            "--topic-label",
            "GAVE2 Task 2",
            "--dataset-root",
            str(dataset_root),
            "--contract-file",
            str(contract_file),
            "--provider-config",
            "/tmp/provider.toml",
            "--semantic-scholar-source",
            "/tmp/semantic.md",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(proc.stdout)
    assert payload["framework"] == "dr-claw"
    assert payload["baseline_proxy_score"] == 0.00221178
    assert payload["improved_proxy_score"] == 0.00166223

    eval_payload = json.loads((output_root / "eval" / "proxy_strict_small_eval.json").read_text(encoding="utf-8"))
    assert eval_payload["topic_label"] == "GAVE2 Task 2"
    assert eval_payload["dataset_root"] == str(dataset_root)
    assert eval_payload["contract_file"] == str(contract_file)
    assert (output_root / "reports" / "proxy_report.md").exists()
    assert (output_root / "artifacts" / "topic_context.json").exists()
    assert (output_root / "submission" / "collated_submission.json").exists()
    assert (output_root / "baselines" / "unigram_baseline" / "metrics.json").exists()
    assert (output_root / "experiments" / "interpolated_bigram" / "metrics.json").exists()
