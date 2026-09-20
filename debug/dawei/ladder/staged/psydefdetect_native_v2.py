"""Reference code for the PsyDefConv corpus (the resource used at this venue).

It shows how to load the corpus, apply the fixed dialogue-level split and obtain
the official score. It contains no features, no models and no experiment design:
those are yours to decide.

Official evaluation goes through official_score(name, id_to_label) only. It writes
the prediction file and the scorer's output under the working directory:
    working/<name>.predictions.jsonl
    working/<name>.official_score.json
and prints one line "official psydefdetect_score (<name>): <value>". Call it once
per configuration you evaluate, with a distinct name each time.
"""
import json
import os
import subprocess
import sys

DATASET_ROOT = "/data/psydefdetect"
CORPUS_PATH = f"{DATASET_ROOT}/PsyDefConv.json"
SPLIT_MANIFEST = "/workspace/automation/psydefdetect_split.json"
OFFICIAL_SCORER = "/workspace/automation/scripts/run_psydefdetect_local_score.py"
LABELS = list(range(9))  # 0 = no defense mechanism, 1..8 = the eight defense categories
WORKING_DIR = os.path.join(os.getcwd(), "working")


def load_corpus():
    """Return the list of records. Each record is a dict with the keys
    id (str), dialogue_id (str), dialogue (list of turns, each a dict with the
    keys speaker and text), current_text (str, the target utterance) and
    label (int in 0..8)."""
    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_split():
    """Return (train_ids, eval_ids): the fixed dialogue-level split as two lists of record ids."""
    with open(SPLIT_MANIFEST, "r", encoding="utf-8") as f:
        split = json.load(f)
    return list(split["train_record_ids"]), list(split["eval_record_ids"])


def select_records(records, ids):
    """Records whose id is in ids, in the order of ids."""
    by_id = {r["id"]: r for r in records}
    return [by_id[i] for i in ids if i in by_id]


def preceding_turns(record):
    """The dialogue turns as (speaker, text) pairs, in conversation order."""
    return [(turn["speaker"], turn["text"]) for turn in record["dialogue"]]


def official_score(name, id_to_label):
    """Official evaluation of one configuration.

    name: a short identifier for this configuration (letters, digits, - and _).
    id_to_label: {record id (str): predicted label (int 0..8)} for the evaluation records.
    Writes working/<name>.predictions.jsonl and working/<name>.official_score.json,
    prints the score line and returns the psydefdetect_score (macro-F1 over labels 1..8).
    Raises if the scorer fails; its stdout/stderr are printed so the failure is visible."""
    os.makedirs(WORKING_DIR, exist_ok=True)
    safe = "".join(ch if (ch.isalnum() or ch in "-_") else "_" for ch in str(name)) or "config"
    predictions_path = os.path.join(WORKING_DIR, f"{safe}.predictions.jsonl")
    score_path = os.path.join(WORKING_DIR, f"{safe}.official_score.json")
    with open(predictions_path, "w", encoding="utf-8") as f:
        for record_id, label in id_to_label.items():
            f.write(json.dumps({"id": str(record_id), "label": int(label)}) + "\n")
    cmd = [
        sys.executable, OFFICIAL_SCORER,
        "--dataset-root", DATASET_ROOT,
        "--split-manifest", SPLIT_MANIFEST,
        "--predictions", predictions_path,
        "--output-score", score_path,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.stdout.strip():
        print(f"official scorer stdout ({safe}):", proc.stdout.strip())
    if proc.stderr.strip():
        print(f"official scorer stderr ({safe}):", proc.stderr.strip())
    if proc.returncode != 0:
        raise RuntimeError(f"official scorer failed for {safe} with return code {proc.returncode}")
    with open(score_path, "r", encoding="utf-8") as f:
        score = float(json.load(f)["psydefdetect_score"])
    print(f"official psydefdetect_score ({safe}): {score:.6f}")
    return score


# Example of the full round trip (labels here are placeholders, not a method):
#   records = load_corpus()
#   train_ids, eval_ids = load_split()
#   train, evaluation = select_records(records, train_ids), select_records(records, eval_ids)
#   score = official_score("baseline", {r["id"]: 0 for r in evaluation})
