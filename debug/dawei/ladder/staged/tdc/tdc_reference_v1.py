"""Reference code for the TDC ADMET toxicity benchmark (the resource used at this venue).

It shows how to load the three splits, how to obtain the official validation score of a
configuration, and how to write the probabilities for the held-back evaluation split.
It contains no features, no models and no experiment design: those are yours to decide.

Official validation goes through validation_score(name, id_to_probability) only. It writes
    working/<name>.validation_predictions.csv
    working/<name>.validation_metrics.json
and prints one line "official validation macro_average_auroc (<name>): <value>". Call it once
per configuration you evaluate, with a distinct name each time, and write the same
configuration's held-back-split probabilities with test_predictions(name, id_to_probability)
so that the configuration can be submitted.
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


def validation_score(name, id_to_probability):
    """Official validation of one configuration.

    name: a short identifier for this configuration (letters, digits, - and _).
    id_to_probability: {sample_id (str): probability of the positive class} for EVERY row of
    the validation split (all three endpoints).
    Writes working/<name>.validation_predictions.csv and working/<name>.validation_metrics.json,
    prints the score line and returns the macro_average_auroc (mean AUROC over the three
    endpoints). Raises if the scorer fails; its output is printed so the failure is visible."""
    os.makedirs(WORKING_DIR, exist_ok=True)
    safe = _safe(name)
    rows = load_split("validation")
    pred_path = os.path.join(WORKING_DIR, f"{safe}.validation_predictions.csv")
    metrics_path = os.path.join(WORKING_DIR, f"{safe}.validation_metrics.json")
    _write_predictions(pred_path, rows, id_to_probability)
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
        metrics = json.load(f)
    value = float(metrics["macro_average_auroc"])
    print(f"official validation macro_average_auroc ({safe}): {value:.6f}")
    return value


def test_predictions(name, id_to_probability):
    """Write working/<name>.test_predictions.csv: the positive-class probability for EVERY row
    of the held-back evaluation split (all three endpoints). Its labels are not available;
    the organisers score this file. Use the same name as in validation_score."""
    os.makedirs(WORKING_DIR, exist_ok=True)
    path = os.path.join(WORKING_DIR, f"{_safe(name)}.test_predictions.csv")
    _write_predictions(path, load_split("test"), id_to_probability)
    print(f"test predictions written ({_safe(name)}): {path}")
    return path


# Example of the round trip (the probabilities here are a placeholder, not a method):
#   train, val, test = load_split("train"), load_split("validation"), load_split("test")
#   validation_score("constant", {r["sample_id"]: 0.5 for r in val})
#   test_predictions("constant", {r["sample_id"]: 0.5 for r in test})
