"""Reference code for the MountainCarContinuous-v0 task (the resource used at this venue).

It shows where the frozen starter code and the frozen evaluator are, how to run the
starter trainer, how a configuration is evaluated officially, and how a configuration
is kept for submission. It contains no algorithmic changes: those are yours to decide
(you may modify src/train.py, src/policy.py, src/networks.py, src/helpers.py and
src/config.yaml, and add code under src/; keep the class name `Model` in networks.py).

Results of this task are defined in the provided MountainCarContinuous-v0 environment with
the provided starter code and the frozen evaluator only: a reward obtained in a different
or simplified environment, or from any evaluator other than the frozen evaluate.py, is not
a result of this task and cannot be selected or submitted. This module is importable from your script as it is (`from hf_dataset_reference import
official_evaluation`): import it rather than pasting or re-implementing it; only the files
written by this module's official_evaluation are official records.

Official evaluation goes through official_evaluation(name, src_dir, checkpoints_dir)
only. It copies your src/ (with its config.yaml) and exactly five checkpoints named
config-42-0.pkl .. config-42-4.pkl (any five files matching config*.pkl) into a clean
directory next to a byte-exact copy of the frozen evaluate.py, runs it there
(256 environments x 5 seeds x 200 frames, Reward Mean higher is better), writes
    working/<name>.evaluation.json    (reward_mean, reward_std)
    working/<name>.submission/        (src/, config.yaml, checkpoints/: what gets handed in)
and prints one line "official evaluation (<name>): reward_mean=<v> reward_std=<v>".
Call it once per configuration you evaluate, with a distinct name each time; a
configuration without this call has no result and cannot be submitted.
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys

STARTER_ROOT = "/data/mountaincar_continuous"          # read-only: src/ (starter code) and protected/evaluate.py
FROZEN_EVALUATOR = os.path.join(STARTER_ROOT, "protected", "evaluate.py")
WORKING_DIR = os.path.join(os.getcwd(), "working")


def starter_src():
    """Path of the frozen starter code directory (train.py, policy.py, networks.py,
    helpers.py, config.yaml, __init__.py). Copy it with copy_starter() before editing."""
    return os.path.join(STARTER_ROOT, "src")


def copy_starter(dest_src):
    """Copy the starter src/ to dest_src (overwriting) and return dest_src. Edit the copy."""
    if os.path.isdir(dest_src):
        shutil.rmtree(dest_src)
    shutil.copytree(starter_src(), dest_src)
    return dest_src


def run_starter_training(src_dir, timeout_seconds=1800):
    """Run `python train.py -config ./config.yaml` inside src_dir (the starter CLI: seed 42,
    writes five checkpoints to src_dir/checkpoints/config-42-{0..4}.pkl, one per initial
    network). Facts about cost on this CPU runtime: the starter config asks for
    20,000,000 training steps, which takes hours; 20,000 steps take about one minute on
    16 cores. Returns the checkpoints directory. Raises if training fails or exceeds
    timeout_seconds (the contract's per-training-command cap is 1800 s)."""
    proc = subprocess.run([sys.executable, "train.py", "-config", "./config.yaml"], cwd=src_dir,
                          capture_output=True, text=True, timeout=timeout_seconds)
    tail = (proc.stdout + "\n" + proc.stderr)[-3000:]
    print(f"starter training in {src_dir}: rc={proc.returncode}\n{tail}")
    if proc.returncode != 0:
        raise RuntimeError(f"starter training failed (rc={proc.returncode})")
    return os.path.join(src_dir, "checkpoints")


def _safe(name):
    return "".join(ch if (ch.isalnum() or ch in "-_") else "_" for ch in str(name)) or "config"


def official_evaluation(name, src_dir, checkpoints_dir):
    """Evaluate one configuration with the frozen evaluator and keep it for submission.

    name: short identifier (letters, digits, - and _).
    src_dir: your (possibly modified) src/ directory containing config.yaml, networks.py, helpers.py.
    checkpoints_dir: directory holding exactly five checkpoints matching config*.pkl.
    Writes working/<name>.evaluation.json and working/<name>.submission/, prints the result
    line and returns reward_mean."""
    os.makedirs(WORKING_DIR, exist_ok=True)
    safe = _safe(name)
    ckpts = sorted(glob.glob(os.path.join(checkpoints_dir, "config*.pkl")))
    if len(ckpts) != 5:
        raise ValueError(f"official evaluation needs exactly 5 checkpoints matching config*.pkl in {checkpoints_dir}, found {len(ckpts)}")
    if not os.path.isfile(os.path.join(src_dir, "config.yaml")):
        raise ValueError(f"{src_dir} has no config.yaml")
    sub = os.path.join(WORKING_DIR, f"{safe}.submission")
    if os.path.isdir(sub):
        shutil.rmtree(sub)
    shutil.copytree(src_dir, os.path.join(sub, "src"), ignore=shutil.ignore_patterns("checkpoints", "__pycache__"))
    os.makedirs(os.path.join(sub, "checkpoints"))
    for c in ckpts:
        shutil.copy(c, os.path.join(sub, "checkpoints", os.path.basename(c)))
    shutil.copy(FROZEN_EVALUATOR, os.path.join(sub, "evaluate.py"))
    proc = subprocess.run([sys.executable, "evaluate.py", "--config_fname", "./src/config.yaml"], cwd=sub,
                          capture_output=True, text=True, timeout=1800)
    m = re.search(r'\{\s*"Reward Mean"\s*:\s*(-?[0-9.]+(?:[eE][+-]?[0-9]+)?)\s*,\s*"Reward Std"\s*:\s*(-?[0-9.]+(?:[eE][+-]?[0-9]+)?)\s*\}', proc.stdout)
    if proc.returncode != 0 or not m:
        print(f"frozen evaluator output ({safe}):", (proc.stdout + "\n" + proc.stderr)[-2000:])
        raise RuntimeError(f"frozen evaluator failed for {safe} (rc={proc.returncode})")
    result = {"reward_mean": float(m.group(1)), "reward_std": float(m.group(2)), "metric": "Reward Mean (frozen evaluate.py, 256 envs x 5 seeds x 200 frames)",
              "checkpoints": [os.path.basename(c) for c in ckpts], "submission_dir": sub, "official": True}
    with open(os.path.join(WORKING_DIR, f"{safe}.evaluation.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"official evaluation ({safe}): reward_mean={result['reward_mean']:.4f} reward_std={result['reward_std']:.4f}")
    return result["reward_mean"]


# Example of the round trip (the starter trainer as-is, which is the baseline, not a method):
#   src = copy_starter("my_src")            # edit my_src/config.yaml, policy.py, ... as you like
#   ckpts = run_starter_training(src)       # or your own training entry point writing config-42-{0..4}.pkl
#   official_evaluation("baseline", src, ckpts)
