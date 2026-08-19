from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

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


def test_find_estimator_candidates_prioritizes_root_estimator(tmp_path: Path) -> None:
    module = load_module()
    workspace = tmp_path / "workspace"
    (workspace / "nested").mkdir(parents=True)
    (workspace / "estimator.py").write_text("# root estimator\n", encoding="utf-8")
    (workspace / "nested" / "estimator.py").write_text("# nested estimator\n", encoding="utf-8")

    candidates = module.find_estimator_candidates(workspace)

    assert candidates[0] == workspace / "estimator.py"
    assert workspace / "nested" / "estimator.py" in candidates


def test_try_generate_official_adapter_for_aris_workspace(tmp_path: Path) -> None:
    module = load_module()
    workspace = tmp_path / "workspace"
    output_dir = tmp_path / "generated"
    workspace.mkdir()
    (workspace / "estimator.py").write_text(
        "class Estimator:\n    def predict(self, mlp, budget=None):\n        return mlp.weights\n",
        encoding="utf-8",
    )

    path, meta = module.try_generate_official_adapter(workspace, "03", output_dir)

    assert path == output_dir / "estimator.py"
    assert meta["adapter_kind"] == "aris_estimator_predict"


def test_try_generate_official_adapter_for_drclaw_workspace(tmp_path: Path) -> None:
    module = load_module()
    workspace = tmp_path / "workspace"
    output_dir = tmp_path / "generated"
    workspace.mkdir()
    (workspace / "estimator.py").write_text(
        "class DiagonalGaussianEstimator:\n"
        "    def predict(self, mlp, budget=None):\n"
        "        return mlp.weights\n"
        "\n"
        "def build_estimator():\n"
        "    return DiagonalGaussianEstimator()\n",
        encoding="utf-8",
    )

    path, meta = module.try_generate_official_adapter(workspace, "06", output_dir)

    assert path == output_dir / "estimator.py"
    assert meta["adapter_kind"] == "drclaw_build_estimator_predict"


def test_try_generate_official_adapter_for_deepscientist_alias_workspace(tmp_path: Path) -> None:
    module = load_module()
    workspace = tmp_path / "workspace"
    output_dir = tmp_path / "generated"
    workspace.mkdir()
    (workspace / "estimator.py").write_text(
        "class DiagonalMomentEstimator:\n    def predict(self, weights):\n        return weights\n",
        encoding="utf-8",
    )

    path, meta = module.try_generate_official_adapter(workspace, "DeepScientist", output_dir)

    assert path == output_dir / "estimator.py"
    assert meta["adapter_kind"] == "deepscientist_weights_predict"
    assert meta["source_symbol"] == "DiagonalMomentEstimator"


def test_try_generate_official_adapter_for_deepscientist_mlp_signature_workspace(
    tmp_path: Path,
) -> None:
    module = load_module()
    workspace = tmp_path / "workspace"
    output_dir = tmp_path / "generated"
    workspace.mkdir()
    (workspace / "estimator.py").write_text(
        "class DiagonalMomentEstimator:\n"
        "    def predict(self, mlp, budget=None):\n"
        "        return mlp.weights\n",
        encoding="utf-8",
    )

    path, meta = module.try_generate_official_adapter(workspace, "05", output_dir)

    assert path == output_dir / "estimator.py"
    assert meta["adapter_kind"] == "deepscientist_weights_predict"
    assert meta["predict_input"] == "mlp"


def test_build_adapter_output_root_is_workspace_isolated(tmp_path: Path) -> None:
    module = load_module()
    base_root = tmp_path / "out"
    workspace_a = tmp_path / "framework-a" / "workspace"
    workspace_b = tmp_path / "framework-b" / "workspace"
    workspace_a.mkdir(parents=True)
    workspace_b.mkdir(parents=True)

    root_a = module.build_adapter_output_root(base_root, workspace_a, "03")
    root_b = module.build_adapter_output_root(base_root, workspace_b, "05")

    assert root_a != root_b
    assert root_a.parent == base_root
    assert root_b.parent == base_root
    assert root_a.name.startswith("generated_official_adapter_")
    assert root_b.name.startswith("generated_official_adapter_")


def test_main_uses_generated_official_adapter_before_local_score(
    tmp_path: Path, monkeypatch
) -> None:
    module = load_module()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "estimator.py").write_text(
        "class Estimator:\n    def predict(self, mlp, budget=None):\n        return mlp.weights\n",
        encoding="utf-8",
    )
    output_score = tmp_path / "score.json"
    dataset_root = tmp_path / "dataset"
    dataset_root.mkdir()

    monkeypatch.setattr(
        module,
        "run_whest",
        lambda **kwargs: (
            tmp_path / "official.json",
            {"score": 0.33, "score_source": "official_adapter_whest_run"},
        ),
    )

    rc = module.main(
        [
            "--workspace",
            str(workspace),
            "--output-score",
            str(output_score),
            "--dataset-root",
            str(dataset_root),
            "--framework-hint",
            "03",
        ]
    )

    assert rc == 0
    assert "official_adapter_whest_run" in output_score.read_text(encoding="utf-8")


def test_main_refuses_framework_authored_score_before_running_whest(
    tmp_path: Path, monkeypatch
) -> None:
    module = load_module()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    output_score = workspace / "score.json"
    output_score.write_text(
        json.dumps({"score": 0.0, "score_source": "official_adapter_whest_run"}) + "\n",
        encoding="utf-8",
    )
    called = False

    def fake_run_whest(**_kwargs):
        nonlocal called
        called = True
        return None, None

    monkeypatch.setattr(module, "run_whest", fake_run_whest)

    with pytest.raises(RuntimeError, match="sole score owner"):
        module.main(
            [
                "--workspace",
                str(workspace),
                "--output-score",
                str(output_score),
                "--dataset-root",
                str(tmp_path / "dataset"),
                "--framework-hint",
                "03",
            ]
        )

    assert called is False


def test_main_refuses_preexisting_official_scorer_output_directory(
    tmp_path: Path,
) -> None:
    module = load_module()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    scorer_output = workspace / "whest_official_eval"
    scorer_output.mkdir()

    with pytest.raises(RuntimeError, match="pre-existing official scorer output"):
        module.main(
            [
                "--workspace",
                str(workspace),
                "--output-score",
                str(workspace / "score.json"),
                "--dataset-root",
                str(tmp_path / "dataset"),
                "--framework-hint",
                "03",
            ]
        )


def test_run_whest_uses_absolute_estimator_path(tmp_path: Path, monkeypatch) -> None:
    module = load_module()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    estimator = workspace / "estimator.py"
    estimator.write_text("class Estimator: pass\n", encoding="utf-8")
    dataset_root = tmp_path / "dataset"
    dataset_root.mkdir()
    output_root = tmp_path / "out"
    calls: dict[str, object] = {}

    monkeypatch.setattr(module.shutil, "which", lambda _: "/tmp/fake-whest")
    monkeypatch.setattr(module, "ensure_dataset_root", lambda *args, **kwargs: dataset_root)

    class Completed:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(cmd, cwd=None, text=None, capture_output=None, env=None):
        calls["cmd"] = cmd
        calls["cwd"] = cwd
        return Completed()

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    monkeypatch.setattr(
        module, "extract_score_payload", lambda _: (tmp_path / "score.json", {"score": 0.1})
    )

    artifact_path, payload = module.run_whest(
        whest_bin="whest",
        estimator=estimator.relative_to(tmp_path),
        dataset_root=dataset_root,
        runner="local",
        output_root=output_root,
    )

    assert artifact_path == tmp_path / "score.json"
    assert payload == {"score": 0.1, "score_source": "local_official_eval"}
    assert calls["cwd"] == output_root
    assert Path(calls["cmd"][3]).is_absolute()


def test_extract_score_payload_prefers_latest_valid_score_json(tmp_path: Path) -> None:
    module = load_module()
    older = tmp_path / "older" / "score.json"
    newer = tmp_path / "newer" / "report.json"
    older.parent.mkdir(parents=True)
    newer.parent.mkdir(parents=True)
    older.write_text(json.dumps({"score": 1.25, "score_source": "old"}) + "\n", encoding="utf-8")
    newer.write_text(json.dumps({"score": 0.75, "score_source": "new"}) + "\n", encoding="utf-8")
    older_stat = older.stat()
    os.utime(newer, ns=(older_stat.st_atime_ns, older_stat.st_mtime_ns + 1_000_000))

    path, payload = module.extract_score_payload(tmp_path)

    assert path == newer
    assert payload == {"score": 0.75, "score_source": "new"}


def test_extract_score_payload_prefers_official_score_over_newer_local_score(
    tmp_path: Path,
) -> None:
    module = load_module()
    official = tmp_path / "official" / "score.json"
    local = tmp_path / "local" / "report.json"
    official.parent.mkdir(parents=True)
    local.parent.mkdir(parents=True)
    official.write_text(
        json.dumps({"score": 0.11, "score_source": "official_adapter_whest_run"}) + "\n",
        encoding="utf-8",
    )
    local.write_text(
        json.dumps({"score": 9.99, "score_source": "local_full_split_final_layer_mse"}) + "\n",
        encoding="utf-8",
    )
    official_stat = official.stat()
    os.utime(local, ns=(official_stat.st_atime_ns, official_stat.st_mtime_ns + 1_000_000))

    path, payload = module.extract_score_payload(tmp_path)

    assert path == official
    assert payload == {"score": 0.11, "score_source": "official_adapter_whest_run"}


def test_extract_score_dict_preserves_official_adapter_source() -> None:
    module = load_module()
    payload = {"score": 0.12, "score_source": "official_adapter_whest_run"}

    result = module.extract_score_dict(payload)

    assert result == {"score": 0.12, "score_source": "official_adapter_whest_run"}


def test_extract_score_payload_prefers_official_adapter_over_newer_local_official_eval(
    tmp_path: Path,
) -> None:
    module = load_module()
    official = tmp_path / "official" / "score.json"
    local = tmp_path / "local" / "report.json"
    official.parent.mkdir(parents=True)
    local.parent.mkdir(parents=True)
    official.write_text(
        json.dumps({"score": 0.11, "score_source": "official_adapter_whest_run"}) + "\n",
        encoding="utf-8",
    )
    local.write_text(
        json.dumps({"score": 9.99, "score_source": "local_official_eval_stdout"}) + "\n",
        encoding="utf-8",
    )
    official_stat = official.stat()
    os.utime(local, ns=(official_stat.st_atime_ns, official_stat.st_mtime_ns + 1_000_000))

    path, payload = module.extract_score_payload(tmp_path)

    assert path == official
    assert payload == {"score": 0.11, "score_source": "official_adapter_whest_run"}


def test_extract_score_payload_accepts_official_whest_json_shape(tmp_path: Path) -> None:
    module = load_module()
    report = tmp_path / "official-run.json"
    report.write_text(
        json.dumps(
            {
                "results": {
                    "adjusted_final_layer_score": 0.349483323097229,
                    "final_layer_mse": 3.49483323097229,
                }
            }
        )
        + "\n",
        encoding="utf-8",
    )

    path, payload = module.extract_score_payload(tmp_path)

    assert path == report
    assert payload == {
        "score": 0.349483323097229,
        "score_source": "local_official_eval_adjusted_final_layer_score",
    }


def test_extract_score_payload_reconstructs_adjusted_score_from_per_mlp_results(
    tmp_path: Path,
) -> None:
    module = load_module()
    report = tmp_path / "result.json"
    report.write_text(
        json.dumps(
            {
                "results": {
                    "primary_score": 3.0,
                    "per_mlp": [
                        {
                            "final_mse": 2.0,
                            "flops_used": 5,
                            "breakdowns": {
                                "estimator": {
                                    "flop_budget": 100,
                                }
                            },
                        },
                        {
                            "final_mse": 4.0,
                            "flops_used": 60,
                            "breakdowns": {
                                "estimator": {
                                    "flop_budget": 100,
                                }
                            },
                        },
                    ],
                }
            }
        )
        + "\n",
        encoding="utf-8",
    )

    path, payload = module.extract_score_payload(tmp_path)

    assert path == report
    assert payload == {
        "score": 1.3,
        "score_source": "local_official_eval_reconstructed_from_per_mlp",
    }


def test_extract_score_from_stdout_supports_scientific_notation() -> None:
    module = load_module()
    stdout = "Adjusted Final-Layer Score 2.97e+01   <- primary score"

    payload = module.extract_score_from_stdout(stdout)

    assert payload == {"score": 29.7, "score_source": "local_official_eval_stdout"}


def test_resolve_dataset_root_prefers_baked_manifest_entry(tmp_path: Path) -> None:
    module = load_module()
    dataset_root = tmp_path / "arc"
    baked_root = dataset_root / "baked" / "full"
    baked_root.mkdir(parents=True)
    (dataset_root / "materialization_manifest.json").write_text(
        json.dumps(
            {
                "splits": {
                    "full": {
                        "baked_path": str(baked_root),
                    }
                }
            }
        )
        + "\n",
        encoding="utf-8",
    )

    resolved = module.resolve_dataset_root(dataset_root)

    assert resolved == baked_root


def test_resolve_dataset_root_maps_raw_full_export_to_default_baked_target(tmp_path: Path) -> None:
    module = load_module()
    raw_full = tmp_path / "arc" / "arc-whestbench-full"
    raw_full.mkdir(parents=True)
    (raw_full / "dataset_info.json").write_text("{}", encoding="utf-8")

    resolved = module.resolve_dataset_root(raw_full)

    assert resolved == tmp_path / "arc" / "baked" / "full"


def test_run_whest_passes_absolute_dataset_path_and_writable_hf_home(
    tmp_path: Path, monkeypatch
) -> None:
    module = load_module()
    workspace_dataset = tmp_path / "arc" / "baked" / "full"
    workspace_dataset.mkdir(parents=True)
    (workspace_dataset / "metadata.json").write_text("{}", encoding="utf-8")
    estimator = tmp_path / "estimator.py"
    estimator.write_text("print('stub')\n", encoding="utf-8")
    output_root = tmp_path / "out"

    monkeypatch.setattr(module.shutil, "which", lambda value: value)
    monkeypatch.setattr(module, "extract_score_payload", lambda _root: (None, None))
    monkeypatch.setattr(module, "extract_score_from_stdout", lambda _stdout: {"score": 0.5})

    calls: list[dict[str, object]] = []

    def fake_run(
        cmd,
        cwd=None,
        text=None,
        capture_output=None,
        check=False,
        stdout=None,
        stderr=None,
        env=None,
    ):
        calls.append({"cmd": cmd, "cwd": cwd, "env": env})

        class Completed:
            returncode = 0
            stdout = "score: 0.5"
            stderr = ""

        return Completed()

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    artifact_path, payload = module.run_whest(
        whest_bin="/tmp/fake-whest",
        estimator=estimator,
        dataset_root=workspace_dataset,
        runner="local",
        output_root=output_root,
    )

    assert artifact_path == output_root / "whest.stdout.log"
    assert payload == {"score": 0.5}
    dataset_index = calls[-1]["cmd"].index("--dataset")
    assert calls[-1]["cmd"][dataset_index + 1] == str(workspace_dataset.resolve())
    assert calls[-1]["env"]["HF_HOME"] == str((output_root / ".hf_home").resolve())


def test_arc_fullrun_wrappers_invoke_local_score_helper() -> None:
    wrappers = sorted((ROOT / "real_eval" / "scripts").glob("0*_arc_wbe_2026_fullrun.sh"))
    shared_runner = (ROOT / "real_eval" / "scripts" / "arc_framework_fullrun.sh").read_text(
        encoding="utf-8"
    )
    for wrapper in wrappers:
        text = wrapper.read_text(encoding="utf-8")
        combined = text + "\n" + shared_runner
        assert "run_arc_wbe_2026_local_score.py" in combined, (
            f"{wrapper.name} should invoke the ARC local score helper"
        )
