"""Reference code for the ARC White-Box Estimation suite (the resource used at this venue).

It shows how to load the provided records, how to build the MLP object an estimator
receives, how to read the ground-truth activation means of the training records, and
how to run the local validation that defines a result of this task. It contains no
estimation method: that is yours to decide.

Results of this task are defined on the provided records only: the accuracy of an
estimator is its local validation on the held-out public records (below), and the
official score is computed on hidden records of the same suite. Numbers measured on
networks you generate yourself are not results of this task.

Local validation goes through local_validation(name, estimator) only. `estimator` is an
object (or class) with predict(mlp), defined in your script. It is evaluated in this
process on the 20 held-out records, and its class source is packaged into
working/<name>.estimator.py so the configuration can be submitted; the packaged file is
self-tested and working/<name>.validation.json records final_layer_mse, all_layer_mse,
wall time and whether the packaged file is submittable. One line is printed:
"official validation (<name>): final_layer_mse=<v> all_layer_mse=<v> submittable=<bool>".
Call it once per configuration you evaluate, with a distinct name each time.

Official scoring runs the packaged file alone with numpy and the standard library only
(no scipy, no torch), and hands predict() weight matrices as numpy-compatible arrays
whose operations are counted as FLOPs: plain numpy arithmetic, matmul (@), exp, sqrt,
maximum, where, sums and reductions all work; np.vectorize, object-dtype arrays and
third-party libraries do not. float32 arithmetic is billed at half the cost of float64.
"""
import ast
import glob
import inspect
import json
import os
import shutil
import time

import numpy as np
import pyarrow.parquet as pq

DATA_GLOB = "/data/arc_wbe_2026/data/*.parquet"
DEPTH, WIDTH = 32, 256
N_VALIDATION = 20  # the last N records by mlp_id are held out for local validation
WORKING_DIR = os.path.join(os.getcwd(), "working")
_VALIDATION_CACHE = []


class MLP:
    """The object an estimator's predict() receives: weights is a list of depth
    float32 arrays of shape (width, width); depth, width and seed are ints."""

    def __init__(self, weights, seed=0):
        self.weights = [np.asarray(w, dtype=np.float32) for w in weights]
        self.depth = len(self.weights)
        self.width = int(self.weights[0].shape[0])
        self.seed = int(seed)


def _row_to_record(row):
    return {
        "mlp_id": int(row["mlp_id"]), "mlp_seed": int(row["mlp_seed"]),
        "weights": np.asarray(row["weights"], dtype=np.float32),
        "all_layer_means": np.asarray(row["all_layer_means"], dtype=np.float64),
        "final_means": np.asarray(row["final_means"], dtype=np.float64),
    }


def _read(paths, want):
    """Records whose mlp_id passes want(mlp_id), reading as few files as possible."""
    records = []
    for path in paths:
        ids = pq.read_table(path, columns=["mlp_id"]).column("mlp_id").to_pylist()
        keep = [i for i, mlp_id in enumerate(ids) if want(int(mlp_id))]
        if not keep:
            continue
        table = pq.read_table(path, columns=["mlp_id", "mlp_seed", "weights", "all_layer_means", "final_means"])
        for i in keep:
            records.append(_row_to_record(table.slice(i, 1).to_pylist()[0]))
    records.sort(key=lambda r: r["mlp_id"])
    return records


def _all_ids():
    ids = []
    for path in sorted(glob.glob(DATA_GLOB)):
        ids += [int(x) for x in pq.read_table(path, columns=["mlp_id"]).column("mlp_id").to_pylist()]
    return sorted(ids)


def load_records(max_records=20):
    """Training records, sorted by mlp_id: the first max_records of the training part
    (about 80 records exist; pass None for all of them). Each record is a dict with
    mlp_id (int), mlp_seed (int), weights (float32 array of shape (32, 256, 256)),
    all_layer_means (float64 array of shape (32, 256): the ground-truth target) and
    final_means (float64 array of shape (256,): its last row). A record is about 8 MB
    of weights; the default 20 records load in a few seconds."""
    ids = _all_ids()
    train_ids = ids[:-N_VALIDATION]
    if max_records is not None:
        train_ids = train_ids[:int(max_records)]
    wanted = set(train_ids)
    return _read(sorted(glob.glob(DATA_GLOB)), lambda i: i in wanted)


def validation_records():
    """The 20 held-out records (the last 20 by mlp_id). Their targets are used only by
    local_validation; do not fit anything on them."""
    if not _VALIDATION_CACHE:
        ids = _all_ids()
        wanted = set(ids[-N_VALIDATION:])
        _VALIDATION_CACHE.extend(_read(sorted(glob.glob(DATA_GLOB)), lambda i: i in wanted))
    return list(_VALIDATION_CACHE)


def make_mlp(record):
    return MLP(record["weights"], seed=record["mlp_seed"])


def ground_truth(record):
    """The (32, 256) target matrix of a training record."""
    return record["all_layer_means"]


# ---- packaging of an in-script estimator into a self-contained file ----

def _class_source_file(estimator_cls):
    """The script file that defines the class: the code object of any of its functions
    carries the file name the interpreter compiled (runfile.py in the working directory)."""
    for value in vars(estimator_cls).values():
        code = getattr(value, "__code__", None)
        if code is not None and os.path.exists(code.co_filename):
            return code.co_filename
    src = inspect.getsourcefile(estimator_cls)
    if src and os.path.exists(src):
        return src
    raise ValueError("cannot locate the script that defines the estimator class")


def _package_source(estimator_cls):
    """The class source plus whatever top-level code of the defining script it refers to
    (functions, classes, assignments, and the imports that bind the names they use),
    resolved transitively, so the file runs on its own."""
    src_file = _class_source_file(estimator_cls)
    module_src = open(src_file, "r", encoding="utf-8").read()
    tree = ast.parse(module_src)
    lines = module_src.splitlines(keepends=True)
    seg = lambda node: "".join(lines[node.lineno - 1:node.end_lineno])
    imports, defs, class_src = {}, {}, None       # name -> (order, source)
    for order, node in enumerate(tree.body):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            mods = [a.name for a in node.names] + ([node.module] if isinstance(node, ast.ImportFrom) else [])
            if any(str(m).startswith("hf_dataset_reference") for m in mods):
                continue                              # the packaged file must run without this module
            for a in node.names:
                bound = a.asname or (a.name.split(".")[0] if isinstance(node, ast.Import) else a.name)
                imports[bound] = (order, seg(node))
        elif isinstance(node, ast.ClassDef) and node.name == estimator_cls.__name__:
            class_src = seg(node)
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            defs[node.name] = (order, seg(node))
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                for n in ast.walk(t):
                    if isinstance(n, ast.Name):
                        defs[n.id] = (order, seg(node))
    if class_src is None:
        raise ValueError(f"class {estimator_cls.__name__} is not defined at the top level of {src_file}")
    needed, queue = {}, [class_src]
    while queue:
        names = {n.id for n in ast.walk(ast.parse(queue.pop())) if isinstance(n, ast.Name)}
        for name in sorted(names):
            for table in (defs, imports):
                if name in table and table[name][1] not in needed.values():
                    needed[(table is imports, table[name][0])] = table[name][1]
                    if table is defs:
                        queue.append(table[name][1])
    ordered = [needed[k] for k in sorted(needed, key=lambda k: (not k[0], k[1]))]   # imports first, then in file order
    parts = ["# packaged by the reference module from the experiment script\n"] + ordered + ["\n", class_src]
    if estimator_cls.__name__ != "Estimator":
        parts.append(f"\n\nEstimator = {estimator_cls.__name__}\n")
    return "".join(parts)


_SELFTEST_DRIVER = r'''
import builtins, importlib.util, json, sys
import numpy as np
est_path, rec_path = sys.argv[1:3]
_allowed = set(sys.stdlib_module_names) | {"numpy", "estimator"}
_real_import = builtins.__import__
def _guarded_import(name, *args, **kwargs):
    top = name.split(".")[0]
    if top not in _allowed and not top.startswith("_"):
        raise ImportError(f"{top} is not available at official scoring: an estimator may use only numpy and the standard library")
    return _real_import(name, *args, **kwargs)
builtins.__import__ = _guarded_import
spec = importlib.util.spec_from_file_location("estimator", est_path); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
data = np.load(rec_path)
class MLP:
    def __init__(self, w, seed):
        self.weights = [np.asarray(x, dtype=np.float32) for x in w]; self.depth = len(self.weights); self.width = int(self.weights[0].shape[0]); self.seed = int(seed)
pred = np.asarray(mod.Estimator().predict(MLP(data["weights"], int(data["seed"]))), dtype=np.float64)
if pred.shape != tuple(data["shape"]): raise SystemExit(f"prediction shape {pred.shape} != {tuple(data['shape'])}")
if not np.isfinite(pred).all(): raise SystemExit("non-finite predictions")
print("ok")
'''


def _self_test(packaged_path, record):
    """Run the packaged file alone in a temporary directory (a fresh interpreter, only that
    file present, imports limited to numpy and the standard library, as the official
    scorer does) and predict one record."""
    import subprocess, sys, tempfile
    with tempfile.TemporaryDirectory() as td:
        est_tmp = os.path.join(td, "estimator.py")
        shutil.copy(packaged_path, est_tmp)
        rec_path = os.path.join(td, "record.npz")
        np.savez(rec_path, weights=record["weights"], seed=record["mlp_seed"], shape=np.array([DEPTH, WIDTH]))
        proc = subprocess.run([sys.executable, "-c", _SELFTEST_DRIVER, est_tmp, rec_path], capture_output=True, text=True, cwd=td, timeout=600)
        if proc.returncode != 0:
            raise ValueError((proc.stderr or proc.stdout).strip().splitlines()[-1][:300] if (proc.stderr or proc.stdout).strip() else f"exit {proc.returncode}")


def local_validation(name, estimator, records=None):
    """Validate one configuration on the held-out records. Returns the final-layer MSE
    (lower is better). `estimator` is an object or class with predict(mlp), or the path
    of a self-contained estimator file. Writes working/<name>.estimator.py and
    working/<name>.validation.json and prints the validation line."""
    os.makedirs(WORKING_DIR, exist_ok=True)
    safe = "".join(ch if (ch.isalnum() or ch in "-_") else "_" for ch in str(name)) or "config"
    records = records if records is not None else validation_records()
    packaged = os.path.join(WORKING_DIR, f"{safe}.estimator.py")
    package_note = ""
    if isinstance(estimator, str):
        if os.path.abspath(estimator) != os.path.abspath(packaged):   # a script may already have written the packaged path itself
            shutil.copy(estimator, packaged)
        ns = {"__name__": "estimator_file"}
        exec(compile(open(packaged, encoding="utf-8").read(), packaged, "exec"), ns)
        est = ns["Estimator"]()
    else:
        est = estimator() if inspect.isclass(estimator) else estimator
        try:
            with open(packaged, "w", encoding="utf-8") as f:
                f.write(_package_source(type(est)))
        except Exception as exc:  # packaging is best effort; validation still runs
            package_note = f"packaging failed: {exc}"
            if os.path.exists(packaged):
                os.remove(packaged)
    fl, al, t0 = [], [], time.time()
    for r in records:
        pred = np.asarray(est.predict(make_mlp(r)), dtype=np.float64)
        truth = r["all_layer_means"]
        if pred.shape != truth.shape:
            raise ValueError(f"prediction shape {pred.shape} != {truth.shape}")
        if not np.isfinite(pred).all():
            raise ValueError("non-finite predictions")
        fl.append(float(np.mean((pred[-1] - truth[-1]) ** 2)))
        al.append(float(np.mean((pred - truth) ** 2)))
    seconds = round(time.time() - t0, 3)
    submittable, reason = False, package_note
    if os.path.exists(packaged):
        try:
            _self_test(packaged, records[0])
            submittable = True
        except Exception as exc:
            reason = f"packaged file failed its self-test: {exc}"
    result = {"final_layer_mse": float(np.mean(fl)), "all_layer_mse": float(np.mean(al)), "n_validation": len(records),
              "seconds": seconds, "estimator_file": packaged if os.path.exists(packaged) else None,
              "submittable": submittable, "note": reason}
    with open(os.path.join(WORKING_DIR, f"{safe}.validation.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"official validation ({safe}): final_layer_mse={result['final_layer_mse']:.6f} all_layer_mse={result['all_layer_mse']:.6f} submittable={submittable}"
          + (f" ({reason})" if reason else ""))
    return result["final_layer_mse"]


# Example of the round trip (the estimator here returns zeros, which is not a method):
#   train = load_records()                      # 20 training records
#   class Estimator:
#       def predict(self, mlp):
#           return np.zeros((mlp.depth, mlp.width))
#   local_validation("zeros", Estimator)
