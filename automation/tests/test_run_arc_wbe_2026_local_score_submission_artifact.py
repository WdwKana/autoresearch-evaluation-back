from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "automation" / "scripts" / "run_arc_wbe_2026_local_score.py"


def load_module():
    spec = importlib.util.spec_from_file_location("run_arc_wbe_2026_local_score", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load module from {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_find_estimator_candidates_prefers_submission_estimator_artifact(tmp_path: Path) -> None:
    module = load_module()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    explicit = workspace / "project" / "estimator.py"
    explicit.parent.mkdir(parents=True)
    explicit.write_text("print('explicit')\n", encoding="utf-8")
    fallback = workspace / "reference" / "estimator.py"
    fallback.parent.mkdir(parents=True)
    fallback.write_text("print('fallback')\n", encoding="utf-8")
    (workspace / "submission.json").write_text(
        json.dumps({"estimator_artifact": str(explicit), "estimator_candidates": [str(fallback)]}) + "\n",
        encoding="utf-8",
    )

    candidates = module.find_estimator_candidates(workspace)

    assert candidates[0] == explicit
    assert fallback in candidates
