from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "automation/scripts/validate_project_alignment.py"


def test_psydefdetect_smoke_alignment_accepts_topic4_runtime_config() -> None:
    proc = subprocess.run(
        [
            "python3",
            str(VALIDATOR),
            "--project-id",
            "04",
            "--phase",
            "smoke",
            "--topic-label",
            "PsyDefDetect",
            "--dataset-root",
            str(ROOT / "data/psydefdetect"),
            "--contract-file",
            str(ROOT / "automation/psydefdetect_contract.md"),
        ],
        cwd=ROOT,
        env={**os.environ, "RESEARCHCLAWEVAL_ROOT": str(ROOT), "RESEARCHCLAWEVAL_AUTOMATION_DIR": str(ROOT / "automation")},
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    assert payload["smoke_alignment"]["ok"] is True
    assert "submit_seven_serial_psydefdetect_fullrun_systemd_user.sh" in payload["smoke_alignment"]["rendered_e2e_cmd"]


def test_psydefdetect_e2e_alignment_accepts_systemd_submission_metadata(tmp_path: Path) -> None:
    log_root = ROOT / "real_eval/systemd_runs/test-topic4-e2e-align"
    log_root.mkdir(parents=True, exist_ok=True)
    submission = log_root / "submission.json"
    state = log_root / "state.json"
    child_summary = log_root / "child_summary.md"
    submission.write_text(
        json.dumps(
            {
                "topic": "PsyDefDetect full-run",
                "run_root": str(ROOT / "real_eval/runs/test-topic4-e2e-align"),
                "log_root": str(log_root),
                "serial_runner": str(ROOT / "real_eval/scripts/run_seven_serial_psydefdetect_fullrun.sh"),
                "framework_config": str(ROOT / "real_eval/config/seven_psydefdetect_fullrun_frameworks.json"),
            }
        ),
        encoding="utf-8",
    )
    state.write_text(
        json.dumps({"topic": "PsyDefDetect full-run", "status": "running", "run_root": str(ROOT / "real_eval/runs/test-topic4-e2e-align")}),
        encoding="utf-8",
    )
    child_summary.write_text("PsyDefDetect full-run child summary\n", encoding="utf-8")

    proc = subprocess.run(
        [
            "python3",
            str(VALIDATOR),
            "--project-id",
            "04",
            "--phase",
            "e2e",
            "--topic-label",
            "PsyDefDetect",
            "--dataset-root",
            str(ROOT / "data/psydefdetect"),
            "--contract-file",
            str(ROOT / "automation/psydefdetect_contract.md"),
        ],
        cwd=ROOT,
        env={
            **os.environ,
            "RESEARCHCLAWEVAL_ROOT": str(ROOT),
            "RESEARCHCLAWEVAL_AUTOMATION_DIR": str(ROOT / "automation"),
            "REAL_EVAL_SYSTEMD_LOG_ROOT": str(log_root),
        },
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    assert {Path(item["path"]).name for item in payload["results"]} >= {"submission.json", "state.json", "child_summary.md"}
