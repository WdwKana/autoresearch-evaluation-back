"""Reference code for the BabyLM 2026 Strict-Small dataset (the resource used at this venue).

It shows how to load the corpus, how a deterministic train/validation split can be made,
how word-level validation perplexity is defined and reported, and how a trained model is
kept for submission. It contains no model, no tokenizer and no training recipe: those
are yours to decide.

Official validation goes through official_validation(name, total_nll_nats, validation_lines)
only: word-level perplexity = exp(total_nll_nats / n_words), where total_nll_nats is the
summed negative log-likelihood (natural log) that YOUR model assigns to the validation
lines under YOUR tokenization, and n_words counts whitespace-separated words of those
lines plus one end-of-line token per line. Normalising by words (not by your model's
tokens) is what makes results comparable across tokenizers. It writes
working/<name>.validation.json and prints one line
"official validation word-level perplexity (<name>): <value>". Call it once per
configuration you evaluate, with a distinct name each time. Keep the model of a
configuration with save_submission(name, path) so the selected configuration can be
handed in.
"""
import glob
import json
import math
import os
import random
import shutil

DATASET_ROOT = "/data/BabyLM-2026-Strict-Small"
WORKING_DIR = os.path.join(os.getcwd(), "working")


def load_corpus():
    """Return {domain: [line, ...]} for every *.train.txt file under DATASET_ROOT
    (about 336k non-empty lines, 9.4M words in total; one sentence or utterance per
    line, already whitespace-tokenised). There is no separate validation file."""
    corpus = {}
    for path in sorted(glob.glob(os.path.join(DATASET_ROOT, "*.train.txt"))):
        domain = os.path.basename(path)[: -len(".train.txt")]
        with open(path, "r", encoding="utf-8") as f:
            lines = [ln.rstrip("\n") for ln in f]
        corpus[domain] = [ln for ln in lines if ln.strip()]
    if not corpus:
        raise FileNotFoundError(f"no *.train.txt files under {DATASET_ROOT}")
    return corpus


def default_split(corpus, validation_fraction=0.1, seed=0):
    """A deterministic held-out split: within each domain a fixed random 10% of the
    lines are validation, the rest training. Returns (train_lines, validation_lines),
    each a list of lines (domain order preserved). You may define your own split, but
    the validation lines must never be used for fitting."""
    rng = random.Random(seed)
    train, validation = [], []
    for domain in sorted(corpus):
        lines = list(corpus[domain])
        idx = list(range(len(lines)))
        rng.shuffle(idx)
        n_val = max(1, int(len(lines) * validation_fraction))
        val_idx = set(idx[:n_val])
        for i, ln in enumerate(lines):
            (validation if i in val_idx else train).append(ln)
    return train, validation


def word_count(lines):
    """Number of whitespace-separated words plus one end-of-line token per line."""
    return sum(len(ln.split()) + 1 for ln in lines)


def official_validation(name, total_nll_nats, validation_lines, split_description="default_split(validation_fraction=0.1, seed=0)"):
    """Report one configuration's word-level validation perplexity.

    name: short identifier (letters, digits, - and _).
    total_nll_nats: the summed negative log-likelihood in nats of ALL validation lines
    under the model (over your own tokens, including your end-of-sequence token).
    validation_lines: the exact lines that NLL was summed over.
    Writes working/<name>.validation.json, prints the line and returns the perplexity."""
    os.makedirs(WORKING_DIR, exist_ok=True)
    safe = "".join(ch if (ch.isalnum() or ch in "-_") else "_" for ch in str(name)) or "config"
    n_words = word_count(validation_lines)
    total_nll_nats = float(total_nll_nats)
    if not math.isfinite(total_nll_nats) or total_nll_nats < 0 or n_words <= 0:
        raise ValueError(f"invalid total_nll_nats={total_nll_nats} or n_words={n_words}")
    ppl = math.exp(total_nll_nats / n_words)
    result = {"validation_perplexity": ppl, "metric": "word_level_validation_perplexity", "total_nll_nats": total_nll_nats,
              "n_words": n_words, "n_validation_lines": len(validation_lines), "split": str(split_description)}
    with open(os.path.join(WORKING_DIR, f"{safe}.validation.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"official validation word-level perplexity ({safe}): {ppl:.4f}  (n_words={n_words}, lines={len(validation_lines)})")
    return ppl


def save_submission(name, path):
    """Keep a configuration's trained model (a file or a directory) under
    working/<name>.submission/ so the selected configuration can be handed in."""
    os.makedirs(WORKING_DIR, exist_ok=True)
    safe = "".join(ch if (ch.isalnum() or ch in "-_") else "_" for ch in str(name)) or "config"
    dest = os.path.join(WORKING_DIR, f"{safe}.submission")
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    if os.path.isdir(path):
        shutil.copytree(path, dest)
    else:
        os.makedirs(dest, exist_ok=True)
        shutil.copy(path, dest)
    print(f"submission kept ({safe}): {dest}")
    return dest


# Example of the round trip (the model here is a unigram count, which is not a method):
#   corpus = load_corpus(); train, val = default_split(corpus)
#   ... fit your model on train, sum its NLL (nats) over val under your tokenization ...
#   official_validation("my_config", total_nll, val)
