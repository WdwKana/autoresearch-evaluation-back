"""Reference code for the PsyDefConv corpus (the resource used at this venue).

It shows how to load the corpus, apply the fixed dialogue-level split, write
predictions in the official format and obtain the official score. It contains
no features, no models and no experiment design: those are yours to decide.
"""
import json
import subprocess
import sys

DATASET_ROOT = "/data/psydefdetect"
CORPUS_PATH = f"{DATASET_ROOT}/PsyDefConv.json"
SPLIT_MANIFEST = "/workspace/automation/psydefdetect_split.json"
OFFICIAL_SCORER = "/workspace/automation/scripts/run_psydefdetect_local_score.py"
LABELS = list(range(9))  # 0 = no defense mechanism, 1..8 = the eight defense categories


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


def write_predictions(path, id_to_label):
    """Write predictions in the format the official scorer reads: JSON Lines, one
    object per evaluation record with the keys id (str) and label (int)."""
    with open(path, "w", encoding="utf-8") as f:
        for record_id, label in id_to_label.items():
            f.write(json.dumps({"id": str(record_id), "label": int(label)}) + "\n")


def official_score(predictions_path, output_score_path):
    """Run the official scorer on a predictions file. Returns the psydefdetect_score
    (macro-F1 over labels 1..8 on the evaluation records). Raises if the scorer fails,
    printing its stdout/stderr so the failure is visible."""
    cmd = [
        sys.executable, OFFICIAL_SCORER,
        "--dataset-root", DATASET_ROOT,
        "--split-manifest", SPLIT_MANIFEST,
        "--predictions", str(predictions_path),
        "--output-score", str(output_score_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    print("official scorer stdout:", proc.stdout.strip())
    print("official scorer stderr:", proc.stderr.strip())
    if proc.returncode != 0:
        raise RuntimeError(f"official scorer failed with return code {proc.returncode}")
    with open(output_score_path, "r", encoding="utf-8") as f:
        return float(json.load(f)["psydefdetect_score"])


# Example of the full round trip (labels here are placeholders, not a method):
#   records = load_corpus()
#   train_ids, eval_ids = load_split()
#   train, evaluation = select_records(records, train_ids), select_records(records, eval_ids)
#   predictions = {r["id"]: 0 for r in evaluation}
#   write_predictions("predictions.jsonl", predictions)
#   score = official_score("predictions.jsonl", "score.json")
