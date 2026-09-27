"""Reference code for the TDC ADMET toxicity benchmark (the resource used at this venue).

It shows how to load the three splits and how a configuration is evaluated and handed
in. It contains no features, no models and no experiment design: those are yours.

Results of this task are defined on the provided splits only: a number obtained on
synthetic, toy, or self-generated molecules is not a result of this task and cannot be
selected or submitted. This module is importable from your script as it is (`from
hf_dataset_reference import official_evaluation`): import it rather than pasting or
re-implementing it; only the files written by this module's official_evaluation are
official records.

Official evaluation goes through official_evaluation(name, predict_fn) only. You hand
over a function predict_fn(rows) -> list of positive-class probabilities (same order
as rows; each row is a dict with sample_id, endpoint, smiles). The module calls it on
the validation split, runs the official validation scorer (macro AUROC over the three
endpoints) and writes
    working/<name>.validation_predictions.csv
    working/<name>.validation_metrics.json
then calls it on the held-back evaluation split (test.csv, no labels) and writes
    working/<name>.test_predictions.csv
so the configuration can be submitted. It prints one line
"official validation macro_average_auroc (<name>): <value>". Call it once per
configuration you evaluate, with a distinct name each time; a configuration without
this call has no result and cannot be submitted.
"""
import csv
import json
import os
import subprocess
import sys

DATASET_ROOT = "/data/tdc_admet_tox"
OFFICIAL_VALIDATION_SCORER = "/workspace/automation/scripts/run_tdc_admet_tox_validation_score.py"
ENDPOINTS = ("AMES", "hERG", "DILI")
WORKING_DIR = os.path.join(os.getcwd(), "working")


def load_split(split):
    """Return the rows of train, validation or test as a list of dicts with the keys
    sample_id (str), endpoint (str, one of AMES/hERG/DILI), smiles (str) and, for train and
    validation only, label (int 0/1). Rows of all three endpoints are in the same file."""
    path = os.path.join(DATASET_ROOT, f"{split}.csv")
    with open(path, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        if "label" in r:
            r["label"] = int(r["label"])
    return rows


def rows_of(rows, endpoint):
    """The rows of one endpoint, in file order."""
    return [r for r in rows if r["endpoint"] == endpoint]


def _safe(name):
    return "".join(ch if (ch.isalnum() or ch in "-_") else "_" for ch in str(name)) or "config"


def _write_predictions(path, rows, id_to_probability):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sample_id", "endpoint", "probability"])
        for r in rows:
            p = float(id_to_probability[r["sample_id"]])
            w.writerow([r["sample_id"], r["endpoint"], f"{min(max(p, 0.0), 1.0):.6f}"])


def _score_validation(safe, rows, probs):
    pred_path = os.path.join(WORKING_DIR, f"{safe}.validation_predictions.csv")
    metrics_path = os.path.join(WORKING_DIR, f"{safe}.validation_metrics.json")
    _write_predictions(pred_path, rows, probs)
    cmd = [sys.executable, OFFICIAL_VALIDATION_SCORER, "--validation", os.path.join(DATASET_ROOT, "validation.csv"),
           "--predictions", pred_path, "--output-metrics", metrics_path]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.stdout.strip():
        print(f"official validation scorer stdout ({safe}):", proc.stdout.strip())
    if proc.stderr.strip():
        print(f"official validation scorer stderr ({safe}):", proc.stderr.strip())
    if proc.returncode != 0:
        raise RuntimeError(f"official validation scorer failed for {safe} (exit {proc.returncode})")
    with open(metrics_path, "r", encoding="utf-8") as f:
        return float(json.load(f)["macro_average_auroc"])


def _probabilities(predict_fn, rows, split):
    probs = list(predict_fn(rows))
    if len(probs) != len(rows):
        raise ValueError(f"predict_fn returned {len(probs)} probabilities for {len(rows)} {split} rows")
    return {r["sample_id"]: float(p) for r, p in zip(rows, probs)}


def official_evaluation(name, predict_fn):
    """Evaluate one configuration officially and keep its submission.

    name: a short identifier for this configuration (letters, digits, - and _).
    predict_fn: callable, predict_fn(rows) -> positive-class probabilities, one per row,
    in the same order (rows: list of dicts with sample_id, endpoint, smiles).
    Calls predict_fn on the validation rows (official validation score) and on the
    evaluation rows (test predictions for submission), writes the three working files,
    prints the score line and returns the validation macro_average_auroc."""
    os.makedirs(WORKING_DIR, exist_ok=True)
    safe = _safe(name)
    val_rows = load_split("validation")
    value = _score_validation(safe, val_rows, _probabilities(predict_fn, val_rows, "validation"))
    test_rows = load_split("test")
    test_path = os.path.join(WORKING_DIR, f"{safe}.test_predictions.csv")
    _write_predictions(test_path, test_rows, _probabilities(predict_fn, test_rows, "evaluation"))
    print(f"official validation macro_average_auroc ({safe}): {value:.6f}  (test predictions written: {test_path})")
    return value


# Example of the round trip (the probabilities here are a constant, which is not a method):
#   train = load_split("train")
#   ... fit your model on train ...
#   official_evaluation("my_config", lambda rows: [0.5 for _ in rows])
