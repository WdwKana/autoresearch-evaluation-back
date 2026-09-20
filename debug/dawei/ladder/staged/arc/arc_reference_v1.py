"""Reference code for the ARC White-Box Estimation suite (the resource used at this venue).

It shows how to load the MLP records, build the MLP object an estimator receives,
read the ground-truth activation means of the training records, and validate an
estimator file locally. It contains no estimation method: that is yours to decide.

Local validation goes through local_validation(name, estimator_path) only. It copies
the estimator file to working/<name>.estimator.py, evaluates it in a clean subprocess
(only that file is available there, so it must be self-contained), and writes
working/<name>.validation.json with final_layer_mse, all_layer_mse and wall time,
printing one line "local validation (<name>): final_layer_mse=<v> all_layer_mse=<v>".
The official score on hidden MLPs is final-layer MSE times a compute factor; local
validation reports MSE and wall time only, not FLOPs.
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

import numpy as np
import pyarrow.parquet as pq

DATA_GLOB = "/data/arc_wbe_2026/data/*.parquet"
DEPTH, WIDTH = 32, 256
N_VALIDATION = 20  # the last N records by mlp_id are held out for local validation
WORKING_DIR = os.path.join(os.getcwd(), "working")


class MLP:
    """The object an estimator's predict() receives: weights is a list of depth
    float32 arrays of shape (width, width); depth, width and seed are ints."""

    def __init__(self, weights, seed=0):
        self.weights = [np.asarray(w, dtype=np.float32) for w in weights]
        self.depth = len(self.weights)
        self.width = int(self.weights[0].shape[0])
        self.seed = int(seed)


def load_records(max_records=None):
    """Return the list of records sorted by mlp_id. Each record is a dict with
    mlp_id (int), mlp_seed (int), weights (float32 array of shape (32, 256, 256)),
    all_layer_means (float64 array of shape (32, 256): the ground-truth target) and
    final_means (float64 array of shape (256,): its last row). About 100 records,
    roughly 0.9 GB of float32 weights in total."""
    records = []
    for path in sorted(glob.glob(DATA_GLOB)):
        table = pq.read_table(path, columns=["mlp_id", "mlp_seed", "weights", "all_layer_means", "final_means"])
        for row in table.to_pylist():
            records.append({
                "mlp_id": int(row["mlp_id"]), "mlp_seed": int(row["mlp_seed"]),
                "weights": np.asarray(row["weights"], dtype=np.float32),
                "all_layer_means": np.asarray(row["all_layer_means"], dtype=np.float64),
                "final_means": np.asarray(row["final_means"], dtype=np.float64),
            })
            if max_records and len(records) >= max_records:
                break
        if max_records and len(records) >= max_records:
            break
    records.sort(key=lambda r: r["mlp_id"])
    return records


def split_records(records):
    """(training_records, validation_records): the last N_VALIDATION by mlp_id are validation."""
    return records[:-N_VALIDATION], records[-N_VALIDATION:]


def make_mlp(record):
    return MLP(record["weights"], seed=record["mlp_seed"])


def ground_truth(record):
    """The (32, 256) target matrix of a training record."""
    return record["all_layer_means"]


_DRIVER = r'''
import importlib.util, inspect, json, sys, time
import numpy as np
est_path, records_path, out_path = sys.argv[1:4]
spec = importlib.util.spec_from_file_location("estimator", est_path); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
est = mod.Estimator()
data = np.load(records_path)
weights, truth = data["weights"], data["truth"]
class MLP:
    def __init__(self, w, seed):
        self.weights = [np.asarray(x, dtype=np.float32) for x in w]; self.depth = len(self.weights); self.width = int(self.weights[0].shape[0]); self.seed = int(seed)
takes_budget = "budget" in inspect.signature(est.predict).parameters
fl, al, t0 = [], [], time.time()
for i in range(weights.shape[0]):
    mlp = MLP(weights[i], int(data["seeds"][i]))
    pred = est.predict(mlp, budget=None) if takes_budget else est.predict(mlp)
    pred = np.asarray(pred, dtype=np.float64)
    if pred.shape != truth[i].shape: raise SystemExit(f"prediction shape {pred.shape} != {truth[i].shape}")
    if not np.isfinite(pred).all(): raise SystemExit("non-finite predictions")
    fl.append(float(np.mean((pred[-1] - truth[i][-1]) ** 2))); al.append(float(np.mean((pred - truth[i]) ** 2)))
json.dump({"final_layer_mse": float(np.mean(fl)), "all_layer_mse": float(np.mean(al)), "n_validation": int(weights.shape[0]), "seconds": round(time.time() - t0, 3)}, open(out_path, "w"))
'''


def local_validation(name, estimator_path, validation_records=None):
    """Validate an estimator file on the held-out records. Returns the final-layer MSE
    (lower is better). The estimator file is evaluated alone in a temporary directory:
    anything it needs must be inside that file."""
    os.makedirs(WORKING_DIR, exist_ok=True)
    safe = "".join(ch if (ch.isalnum() or ch in "-_") else "_" for ch in str(name)) or "config"
    if validation_records is None:
        validation_records = split_records(load_records())[1]
    est_copy = os.path.join(WORKING_DIR, f"{safe}.estimator.py")
    shutil.copy(estimator_path, est_copy)
    with tempfile.TemporaryDirectory() as td:
        est_tmp = os.path.join(td, "estimator.py")
        shutil.copy(estimator_path, est_tmp)
        rec_path = os.path.join(td, "validation.npz")
        np.savez(rec_path, weights=np.stack([r["weights"] for r in validation_records]),
                 truth=np.stack([r["all_layer_means"] for r in validation_records]),
                 seeds=np.array([r["mlp_seed"] for r in validation_records]))
        out_path = os.path.join(td, "result.json")
        proc = subprocess.run([sys.executable, "-c", _DRIVER, est_tmp, rec_path, out_path],
                              capture_output=True, text=True, cwd=td, timeout=1800)
        if proc.returncode != 0 or not os.path.exists(out_path):
            print(f"local validation ({safe}) FAILED:", (proc.stderr or proc.stdout).strip()[-1500:])
            raise RuntimeError(f"local validation failed for {safe}")
        result = json.load(open(out_path))
    result["estimator_file"] = est_copy
    with open(os.path.join(WORKING_DIR, f"{safe}.validation.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"local validation ({safe}): final_layer_mse={result['final_layer_mse']:.6f} all_layer_mse={result['all_layer_mse']:.6f} seconds={result['seconds']}")
    return result["final_layer_mse"]


# Example of the round trip (the estimator here is a placeholder, not a method):
#   records = load_records(); train, val = split_records(records)
#   with open("my_estimator.py", "w") as f:
#       f.write("import numpy as np\nclass Estimator:\n    def predict(self, mlp):\n        return np.zeros((mlp.depth, mlp.width))\n")
#   local_validation("zeros", "my_estimator.py", val)
