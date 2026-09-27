"""Reference code for the BabyLM 2026 Strict-Small dataset (the resource used at this venue).

It shows how to load the corpus, gives the fixed validation split that results are
reported on, defines word-level validation perplexity, and keeps a trained model for
submission. It contains no model, no tokenizer and no training recipe: those are yours.

Results of this task are defined on the provided corpus and its fixed validation lines
only: a perplexity obtained on synthetic, toy, or self-generated text is not a result of
this task and cannot be selected or submitted. This module is importable from your
script as it is (`from hf_dataset_reference import official_validation`): import it
rather than pasting or re-implementing it; only the files written by this module's
official_validation are official records.

Official validation goes through official_validation(name, nll_fn) only. You hand over a
function nll_fn(lines) -> float that returns the summed negative log-likelihood in nats
that YOUR model assigns to a list of lines under YOUR tokenization (including your
end-of-sequence token per line). The reference module calls it on the fixed validation
lines (validation_lines(): a deterministic 10% of every domain, about 33k lines; the
same for every configuration and every participant) and reports
    word-level perplexity = exp(total_nll_nats / n_words),
n_words = whitespace-separated words of those lines plus one end-of-line token per line.
Normalising by words rather than by your tokens is what makes results comparable across
tokenizers. It writes working/<name>.validation.json and prints one line
"official validation word-level perplexity (<name>): <value>". Call it once per
configuration you evaluate, with a distinct name each time.

Training data is your choice: training_lines() is the rest of the corpus (about 302k
lines); use all of it or any subset you like. The validation lines must never be used
for fitting, and a result is only defined on the fixed validation lines above. Keep the
model of a configuration with save_submission(name, path) so the selected configuration
can be handed in.
"""
import glob
import json
import math
import os
import random
import shutil

DATASET_ROOT = "/data/BabyLM-2026-Strict-Small"
WORKING_DIR = os.path.join(os.getcwd(), "working")
_SPLIT_CACHE = {}


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


def _split():
    if not _SPLIT_CACHE:
        corpus = load_corpus()
        rng = random.Random(0)
        train, validation = [], []
        for domain in sorted(corpus):
            lines = list(corpus[domain])
            idx = list(range(len(lines)))
            rng.shuffle(idx)
            val_idx = set(idx[:max(1, int(len(lines) * 0.1))])
            for i, ln in enumerate(lines):
                (validation if i in val_idx else train).append(ln)
        _SPLIT_CACHE["train"], _SPLIT_CACHE["validation"] = train, validation
    return _SPLIT_CACHE


def training_lines():
    """The training part of the fixed split (about 302k lines, domain order preserved).
    Use all of it or any subset you like."""
    return list(_split()["train"])


def validation_lines():
    """The fixed validation lines (a deterministic 10% of every domain, about 33k lines).
    Results are defined on exactly these lines; never fit anything on them."""
    return list(_split()["validation"])


def default_split(corpus=None, validation_fraction=0.1, seed=0):
    """(training_lines(), validation_lines()) of the fixed split; kept for convenience."""
    return training_lines(), validation_lines()


def word_count(lines):
    """Number of whitespace-separated words plus one end-of-line token per line."""
    return sum(len(ln.split()) + 1 for ln in lines)


def official_validation(name, nll_fn):
    """Report one configuration's word-level perplexity on the fixed validation lines.

    name: short identifier (letters, digits, - and _).
    nll_fn: callable, nll_fn(lines) -> total negative log-likelihood in nats of those
    lines under your model and tokenization (including your end-of-sequence token).
    The module calls nll_fn(validation_lines()) itself, writes working/<name>.validation.json,
    prints the line and returns the perplexity."""
    os.makedirs(WORKING_DIR, exist_ok=True)
    safe = "".join(ch if (ch.isalnum() or ch in "-_") else "_" for ch in str(name)) or "config"
    lines = validation_lines()
    total_nll_nats = float(nll_fn(lines))
    n_words = word_count(lines)
    if not math.isfinite(total_nll_nats) or total_nll_nats < 0:
        raise ValueError(f"nll_fn returned an invalid total NLL: {total_nll_nats}")
    ppl = math.exp(total_nll_nats / n_words)
    result = {"validation_perplexity": ppl, "metric": "word_level_validation_perplexity", "total_nll_nats": total_nll_nats,
              "n_words": n_words, "n_validation_lines": len(lines), "split": "fixed reference split: 10% of every domain, seed 0",
              "official": True}
    with open(os.path.join(WORKING_DIR, f"{safe}.validation.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"official validation word-level perplexity ({safe}): {ppl:.4f}  (n_words={n_words}, lines={len(lines)})")
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
#   train = training_lines()
#   ... fit your model on train (or a subset) ...
#   def nll_fn(lines):            # total NLL in nats of these lines under your model
#       return sum(-model_logprob(ln) for ln in lines)
#   official_validation("my_config", nll_fn)
