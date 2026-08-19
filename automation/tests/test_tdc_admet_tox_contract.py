from __future__ import annotations

import csv
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCORER = ROOT / "automation" / "scripts" / "run_tdc_admet_tox_host_score.py"
VALIDATION_SCORER = (
    ROOT / "automation" / "scripts" / "run_tdc_admet_tox_validation_score.py"
)
AUDITOR = ROOT / "automation" / "scripts" / "validate_tdc_admet_tox_run.py"
MATERIALIZER = ROOT / "automation" / "scripts" / "materialize_tdc_admet_tox_dataset.py"
EXPORTER = ROOT / "automation" / "scripts" / "export_tdc_admet_tox_official_splits.py"
REFERENCE_BASELINE = ROOT / "automation" / "scripts" / "run_tdc_admet_tox_reference_baseline.py"
ENDPOINTS = ("AMES", "hERG", "DILI")


def load_exporter():
    spec = importlib.util.spec_from_file_location("export_tdc_admet_tox_official_splits", EXPORTER)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load exporter from {EXPORTER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_reference_baseline():
    spec = importlib.util.spec_from_file_location(
        "run_tdc_admet_tox_reference_baseline", REFERENCE_BASELINE
    )
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load reference baseline from {REFERENCE_BASELINE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_rows() -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    public_rows = []
    prediction_rows = []
    label_rows = []
    for endpoint in ENDPOINTS:
        for suffix, label, probability in (("neg", 0, 0.1), ("pos", 1, 0.9)):
            sample_id = f"{endpoint}_{suffix}"
            public_rows.append({"sample_id": sample_id, "endpoint": endpoint, "smiles": "CC"})
            prediction_rows.append(
                {"sample_id": sample_id, "endpoint": endpoint, "probability": probability}
            )
            label_rows.append({"sample_id": sample_id, "endpoint": endpoint, "label": label})
    return public_rows, prediction_rows, label_rows


def prepare_scoring_inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    public_root = tmp_path / "public"
    hidden_labels = tmp_path / "host-private" / "labels.csv"
    predictions = tmp_path / "workspace" / "predictions.csv"
    public_rows, prediction_rows, label_rows = test_rows()
    write_csv(public_root / "test.csv", ["sample_id", "endpoint", "smiles"], public_rows)
    write_csv(predictions, ["sample_id", "endpoint", "probability"], prediction_rows)
    write_csv(hidden_labels, ["sample_id", "endpoint", "label"], label_rows)
    return public_root, hidden_labels, predictions


def run_scorer(
    public_root: Path, hidden_labels: Path, predictions: Path, output_score: Path
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCORER),
            "--public-dataset-root",
            str(public_root),
            "--hidden-labels",
            str(hidden_labels),
            "--predictions",
            str(predictions),
            "--output-score",
            str(output_score),
        ],
        capture_output=True,
        text=True,
    )


def run_auditor(workspace: Path, stage: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(AUDITOR), "--workspace", str(workspace), "--stage", stage],
        capture_output=True,
        text=True,
    )


def prepare_normalized_source(root: Path) -> Path:
    source = root / "normalized-source"
    for endpoint in ENDPOINTS:
        for split in ("train", "validation", "test"):
            write_csv(
                source / endpoint / f"{split}.csv",
                ["sample_id", "smiles", "label"],
                [
                    {
                        "sample_id": f"{endpoint}_{split}_neg",
                        "smiles": "CC",
                        "label": 0,
                    },
                    {
                        "sample_id": f"{endpoint}_{split}_pos",
                        "smiles": "CCC",
                        "label": 1,
                    },
                ],
            )
    return source


def run_materializer(
    source: Path, public_root: Path, hidden_root: Path
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(MATERIALIZER),
            "--source-root",
            str(source),
            "--public-output-root",
            str(public_root),
            "--hidden-output-root",
            str(hidden_root),
            "--source-revision",
            "tdc-export-test-revision",
        ],
        capture_output=True,
        text=True,
    )


def test_materializer_physically_separates_public_test_and_hidden_labels(tmp_path: Path) -> None:
    source = prepare_normalized_source(tmp_path)
    public_root = tmp_path / "public"
    hidden_root = tmp_path / "host-private"

    proc = run_materializer(source, public_root, hidden_root)

    assert proc.returncode == 0, proc.stdout
    with (public_root / "test.csv").open("r", encoding="utf-8", newline="") as handle:
        public_reader = csv.DictReader(handle)
        public_rows = list(public_reader)
    with (hidden_root / "test_labels.csv").open("r", encoding="utf-8", newline="") as handle:
        hidden_reader = csv.DictReader(handle)
        hidden_rows = list(hidden_reader)
    assert public_reader.fieldnames == ["sample_id", "endpoint", "smiles"]
    assert hidden_reader.fieldnames == ["sample_id", "endpoint", "label"]
    assert len(public_rows) == len(hidden_rows) == 6
    assert not (public_root / "test_labels.csv").exists()

    public_manifest = json.loads(
        (public_root / "dataset_manifest.json").read_text(encoding="utf-8")
    )
    hidden_manifest = json.loads((hidden_root / "hidden_manifest.json").read_text(encoding="utf-8"))
    assert public_manifest["source_revision"] == "tdc-export-test-revision"
    assert set(public_manifest["files"]) == {"train.csv", "validation.csv", "test.csv"}
    assert all(set(row) == {"records"} for row in public_manifest["splits"]["test"].values())
    assert hidden_manifest["visibility"] == "host_only"
    assert hidden_manifest["test_labels"]["record_count"] == 6


def test_materializer_rejects_hidden_root_nested_under_public_root(tmp_path: Path) -> None:
    source = prepare_normalized_source(tmp_path)
    public_root = tmp_path / "public"

    proc = run_materializer(source, public_root, public_root / "private")

    assert proc.returncode != 0
    assert "public and hidden output roots must be physically separate" in proc.stdout


def test_official_exporter_constants_pin_dataverse_and_pytdc() -> None:
    module = load_exporter()

    assert module.DATAVERSE_DATASET_PID == "doi:10.7910/DVN/21LKWG"
    assert module.DATAVERSE_DATASET_VERSION == "V105"
    assert module.DATAVERSE_FILE_ID == 4426004
    assert (
        module.ARCHIVE_SHA256 == "bd0005246cb6f1672333c28ad202112a8bf071ab65d847848715030308faf1f1"
    )
    assert module.PYTDC_VERSION == "1.1.15"
    assert module.RDKIT_VERSION == "2023.09.5"
    assert module.SPLIT_SEED == 42
    assert module.SPLIT_FRACTIONS == (0.875, 0.125, 0.0)


def test_official_scaffold_split_is_deterministic_and_group_disjoint() -> None:
    module = load_exporter()
    rows = [
        {
            "sample_id": f"row_{index:02d}",
            "smiles": f"scaffold-{index // 2}-molecule-{index}",
            "label": index % 2,
        }
        for index in range(40)
    ]

    def scaffold_fn(smiles: str) -> str:
        return smiles.split("-molecule-", 1)[0]

    first_train, first_validation, first_omitted = module.split_rows_by_scaffold(
        rows, seed=42, scaffold_fn=scaffold_fn
    )
    second_train, second_validation, second_omitted = module.split_rows_by_scaffold(
        rows, seed=42, scaffold_fn=scaffold_fn
    )

    assert [row["sample_id"] for row in first_train] == [row["sample_id"] for row in second_train]
    assert [row["sample_id"] for row in first_validation] == [
        row["sample_id"] for row in second_validation
    ]
    assert not first_omitted
    assert not second_omitted
    assert len(first_train) + len(first_validation) == len(rows)
    train_scaffolds = {scaffold_fn(str(row["smiles"])) for row in first_train}
    validation_scaffolds = {scaffold_fn(str(row["smiles"])) for row in first_validation}
    assert train_scaffolds.isdisjoint(validation_scaffolds)


def test_reference_baseline_is_two_fixed_single_candidate_configurations() -> None:
    module = load_reference_baseline()

    assert len(module.CONFIGURATIONS) == 2
    assert {row["run_id"] for row in module.CONFIGURATIONS} == {"run_001", "run_002"}
    assert len({row["feature_strategy"] for row in module.CONFIGURATIONS}) == 2
    assert module.RESOURCE_BUDGET["gpu_count"] == 0
    assert module.RESOURCE_BUDGET["max_experiment_runtime_seconds"] == 3600


def test_host_scorer_computes_macro_auroc_and_secondary_metrics(tmp_path: Path) -> None:
    public_root, hidden_labels, predictions = prepare_scoring_inputs(tmp_path)
    output_score = tmp_path / "workspace" / "score.json"

    proc = run_scorer(public_root, hidden_labels, predictions, output_score)

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(output_score.read_text(encoding="utf-8"))
    assert payload["score_source"] == "host_hidden_test_labels"
    assert payload["primary_metric"] == "macro_average_auroc"
    assert payload["main_score"] == 1.0
    assert payload["macro_average_auroc"] == 1.0
    assert set(payload["per_endpoint"]) == set(ENDPOINTS)
    assert all(payload["per_endpoint"][endpoint]["auroc"] == 1.0 for endpoint in ENDPOINTS)
    assert payload["secondary_metrics"]["macro_average_auprc"] == 1.0
    assert set(payload["artifacts"]) == {"public_test", "predictions", "hidden_labels"}
    assert "path" not in payload["artifacts"]["hidden_labels"]


def test_visible_validation_scorer_accepts_optional_label_column(tmp_path: Path) -> None:
    validation = tmp_path / "validation.csv"
    predictions = tmp_path / "predictions.csv"
    metrics = tmp_path / "metrics.json"
    labeled_rows = []
    prediction_rows = []
    for endpoint in ENDPOINTS:
        for index, label in enumerate((0, 1)):
            sample_id = f"{endpoint}_{index}"
            labeled_rows.append(
                {
                    "sample_id": sample_id,
                    "endpoint": endpoint,
                    "smiles": "C" if index == 0 else "CC",
                    "label": label,
                }
            )
            prediction_rows.append(
                {
                    "sample_id": sample_id,
                    "endpoint": endpoint,
                    "probability": 0.1 if label == 0 else 0.9,
                    "label": label,
                }
            )
    write_csv(validation, ["sample_id", "endpoint", "smiles", "label"], labeled_rows)
    write_csv(
        predictions,
        ["sample_id", "endpoint", "probability", "label"],
        prediction_rows,
    )

    proc = subprocess.run(
        [
            sys.executable,
            str(VALIDATION_SCORER),
            "--validation",
            str(validation),
            "--predictions",
            str(predictions),
            "--output-metrics",
            str(metrics),
        ],
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(metrics.read_text(encoding="utf-8"))
    assert payload["split"] == "validation"
    assert payload["macro_average_auroc"] == 1.0
    assert set(payload["per_endpoint"]) == set(ENDPOINTS)


def test_host_scorer_rejects_hidden_labels_below_public_root(tmp_path: Path) -> None:
    public_root, hidden_labels, predictions = prepare_scoring_inputs(tmp_path)
    exposed_labels = public_root / "test_labels.csv"
    exposed_labels.write_text(hidden_labels.read_text(encoding="utf-8"), encoding="utf-8")

    proc = run_scorer(public_root, exposed_labels, predictions, tmp_path / "score.json")

    assert proc.returncode != 0
    assert "must not be located under the public dataset root" in proc.stderr


def test_host_scorer_rejects_prediction_label_column(tmp_path: Path) -> None:
    public_root, hidden_labels, predictions = prepare_scoring_inputs(tmp_path)
    _, prediction_rows, _ = test_rows()
    polluted_rows = [{**row, "label": 0} for row in prediction_rows]
    write_csv(
        predictions,
        ["sample_id", "endpoint", "probability", "label"],
        polluted_rows,
    )

    proc = run_scorer(public_root, hidden_labels, predictions, tmp_path / "score.json")

    assert proc.returncode != 0
    assert "invalid CSV schema" in proc.stderr


def metrics_payload(value: float) -> dict:
    return {
        "split": "validation",
        "macro_average_auroc": value,
        "per_endpoint": {
            endpoint: {
                "auroc": value,
                "auprc_average_precision": value - 0.05,
            }
            for endpoint in ENDPOINTS
        },
    }


def prepare_framework_workspace(tmp_path: Path) -> tuple[Path, Path, Path]:
    public_root, hidden_labels, predictions = prepare_scoring_inputs(tmp_path)
    workspace = predictions.parent
    (workspace / "logs").mkdir()
    (workspace / "logs" / "framework.log").write_text("framework complete\n", encoding="utf-8")
    (workspace / "train.py").write_text("print('reproduce')\n", encoding="utf-8")
    (workspace / "environment.json").write_text(
        json.dumps(
            {
                "python_version": "3.12",
                "platform": "test-container",
                "device": "cpu",
                "seeds": [7],
                "packages": {"example": "1.0"},
                "created_at": "2026-07-30T00:00:00+08:00",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    experiments = []
    for index, value in ((1, 0.7), (2, 0.8)):
        run_id = f"run_{index:03d}"
        run_dir = workspace / "runs" / run_id
        run_dir.mkdir(parents=True)
        config_file = run_dir / "config.json"
        prediction_file = run_dir / "validation_predictions.csv"
        metrics_file = run_dir / "metrics.json"
        log_file = run_dir / "train.log"
        config_file.write_text(json.dumps({"model": f"model-{index}"}) + "\n", encoding="utf-8")
        prediction_file.write_text("sample_id,endpoint,probability\nx,AMES,0.5\n", encoding="utf-8")
        metrics = metrics_payload(value)
        metrics_file.write_text(json.dumps(metrics) + "\n", encoding="utf-8")
        log_file.write_text(f"validation macro AUROC={value}\n", encoding="utf-8")
        experiments.append(
            {
                "run_id": run_id,
                "status": "complete",
                "hypothesis": f"Hypothesis {index}",
                "model_strategy": f"model-family-{index}",
                "feature_strategy": f"feature-family-{index}",
                "config_file": str(config_file.relative_to(workspace)),
                "prediction_file": str(prediction_file.relative_to(workspace)),
                "metrics_file": str(metrics_file.relative_to(workspace)),
                "log_file": str(log_file.relative_to(workspace)),
                "runtime_seconds": 10 + index,
                "seed": 7,
                "candidate_count": 1,
                "validation_metrics": {
                    "macro_average_auroc": metrics["macro_average_auroc"],
                    "per_endpoint": metrics["per_endpoint"],
                },
            }
        )

    selected = experiments[1]
    claim_id = "table1_macro_auroc_model_b"
    trace = {
        "task_id": "tdc_admet_tox",
        "framework_native_execution": True,
        "consumed_topic_input": True,
        "framework_internal_model": "gpt-5.4",
        "framework_internal_api_base_url": "http://tdc-gpt-relay:8787/v1",
        "experiments": experiments,
        "selected_experiment_id": selected["run_id"],
        "selection_metric": "validation_macro_average_auroc",
        "final_prediction_file": "predictions.csv",
        "reproduction": {
            "entrypoint": "train.py",
            "command": "python3 train.py",
            "seed": 7,
        },
        "environment_file": "environment.json",
        "resource_budget": {
            "cpu_cores": 4,
            "memory_gib": 16,
            "gpu_count": 0,
            "workspace_disk_gib": 10,
            "max_experiment_runtime_seconds": 3600,
            "max_total_wall_seconds": 7200,
            "network_policy": "injected_llm_relay_only",
        },
        "total_wall_seconds": 30,
        "claims": [
            {
                "claim_id": claim_id,
                "endpoint": "macro",
                "metric": "AUROC",
                "value": 0.8,
                "source_run_id": selected["run_id"],
                "prediction_file": selected["prediction_file"],
                "config_file": selected["config_file"],
                "log_file": selected["log_file"],
            }
        ],
    }
    (workspace / "experiment_trace.json").write_text(json.dumps(trace) + "\n", encoding="utf-8")
    (workspace / "paper.md").write_text(
        "# TDC-ADMET-Tox\n\n"
        "| Model | Validation macro AUROC |\n"
        "|---|---:|\n"
        f"| Model B | 0.8000 <!-- claim:{claim_id} --> |\n",
        encoding="utf-8",
    )
    return workspace, public_root, hidden_labels


def test_two_stage_audit_accepts_framework_then_host_score(tmp_path: Path) -> None:
    workspace, public_root, hidden_labels = prepare_framework_workspace(tmp_path)

    framework_audit = run_auditor(workspace, "framework")
    assert framework_audit.returncode == 0, framework_audit.stdout
    framework_payload = json.loads(framework_audit.stdout)
    assert framework_payload["experiment_count"] == 2
    assert framework_payload["checked_paper_table_numbers"] == 1
    assert framework_payload["main_score"] is None

    score_proc = run_scorer(
        public_root,
        hidden_labels,
        workspace / "predictions.csv",
        workspace / "score.json",
    )
    assert score_proc.returncode == 0, score_proc.stderr

    final_audit = run_auditor(workspace, "final")
    assert final_audit.returncode == 0, final_audit.stdout
    final_payload = json.loads(final_audit.stdout)
    assert final_payload["main_score"] == 1.0

    repeated_framework_audit = run_auditor(workspace, "framework")
    assert repeated_framework_audit.returncode != 0
    assert "framework stage must not contain score.json" in repeated_framework_audit.stdout


def test_audit_rejects_a_fifth_experiment(tmp_path: Path) -> None:
    workspace, _, _ = prepare_framework_workspace(tmp_path)
    trace_path = workspace / "experiment_trace.json"
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    trace["experiments"].extend([dict(trace["experiments"][0])] * 3)
    trace_path.write_text(json.dumps(trace) + "\n", encoding="utf-8")

    proc = run_auditor(workspace, "framework")

    assert proc.returncode != 0
    assert "exactly 2 to 4 complete experiments are required" in proc.stdout


def test_audit_rejects_untraceable_paper_table_number(tmp_path: Path) -> None:
    workspace, _, _ = prepare_framework_workspace(tmp_path)
    (workspace / "paper.md").write_text(
        "Selected method. <!-- claim:table1_macro_auroc_model_b -->\n\n"
        "| Model | Validation macro AUROC |\n|---|---:|\n| Model B | 0.8000 |\n",
        encoding="utf-8",
    )

    proc = run_auditor(workspace, "framework")

    assert proc.returncode != 0
    assert "numeric paper table cell has no claim marker" in proc.stdout


def test_audit_rejects_hidden_multi_candidate_search(tmp_path: Path) -> None:
    workspace, _, _ = prepare_framework_workspace(tmp_path)
    trace_path = workspace / "experiment_trace.json"
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    trace["experiments"][0]["candidate_count"] = 8
    trace_path.write_text(json.dumps(trace) + "\n", encoding="utf-8")

    proc = run_auditor(workspace, "framework")

    assert proc.returncode != 0
    assert "must contain one candidate" in proc.stdout
