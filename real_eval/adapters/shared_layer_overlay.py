#!/usr/bin/env python3
"""Framework-scoped overlay for shared-layer files.

WHY (2026-10-04)
    The shared layer -- automation/ (contracts, native-input generators) and the
    real_eval/scripts/*_framework_*.sh runners -- is used by all seven frameworks
    and stays byte-identical to upstream: an edit there changes other people's
    frameworks and turns upstream merges into conflicts. What 01 (ai_researcher)
    and 02 (ai_scientist_v2) need changed in those files is kept as unified diffs
    under
        real_eval/adapters/<framework>/shared_layer_patches/<shared path>.patch
    and applied here, at run time, to a copy. The shared file is never written.

USAGE
    shared_layer_overlay.py generate    <framework> <shared .py> [args...]
        run the patched generator in this process as if the shared path itself
        had been executed (same __file__, argv[0] and sys.path[0])
    shared_layer_overlay.py materialize <framework> <shared .sh>
        write the patched runner under real_eval/runs/_shared_layer_overlay/
        (content-addressed, an existing copy is never rewritten) and print its
        path; the caller exports RESEARCHCLAWEVAL_ROOT and execs it
    shared_layer_overlay.py show        <framework> <shared file>
        print the patched text
    shared_layer_overlay.py check
        apply every patch of every framework and syntax-check the result

STRICTNESS
    A hunk applies only if its old side (context + removed lines) occurs exactly
    once in the upstream text; line numbers are ignored and nothing is fuzzed.
    When upstream changes a patched region the launch stops here, loudly,
    instead of running something half-patched.
"""
from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
import types
from pathlib import Path

# abspath, not resolve(): the repo is reached through a symlinked prefix and the
# paths handed to docker must keep the prefix the caller used.
HERE = Path(os.path.abspath(__file__)).parent
ROOT = Path(os.environ.get("RESEARCHCLAWEVAL_ROOT") or HERE.parents[1])
ADAPTERS = ROOT / "real_eval" / "adapters"
PATCH_DIR = "shared_layer_patches"
MATERIALIZE_ROOT = Path("real_eval/runs/_shared_layer_overlay")
HUNK_HEADER = re.compile(r"^@@ -\d+(?:,(\d+))? \+\d+(?:,(\d+))? @@")
TAG = "[shared-layer-overlay]"


def fail(message: str):
    raise SystemExit(f"{TAG} {message}")


def parse_hunks(patch_text: str, label: str) -> list[tuple[list[str], list[str]]]:
    """Return [(old side lines, new side lines)] of a one-file unified diff."""
    lines = patch_text.splitlines(keepends=True)
    index = 0
    while index < len(lines) and not HUNK_HEADER.match(lines[index]):
        index += 1  # leading commentary and the ---/+++ file header
    hunks: list[tuple[list[str], list[str]]] = []
    while index < len(lines):
        header = HUNK_HEADER.match(lines[index])
        if not header:
            if lines[index].strip():
                fail(f"{label}: unexpected text between hunks: {lines[index]!r}")
            index += 1
            continue
        want_old = int(header.group(1) or 1)
        want_new = int(header.group(2) or 1)
        index += 1
        old: list[str] = []
        new: list[str] = []
        last: list[list[str]] = []

        def no_newline_marker() -> None:
            for side in last:
                side[-1] = side[-1].rstrip("\r\n")

        while len(old) < want_old or len(new) < want_new:
            if index >= len(lines):
                fail(f"{label}: hunk {len(hunks) + 1} is truncated")
            line = lines[index]
            index += 1
            tag, body = line[:1], line[1:]
            if tag == " " or line in ("\n", "\r\n"):  # blank context lines may lose their space
                body = body if tag == " " else line
                old.append(body)
                new.append(body)
                last = [old, new]
            elif tag == "-":
                old.append(body)
                last = [old]
            elif tag == "+":
                new.append(body)
                last = [new]
            elif tag == "\\":
                no_newline_marker()
            else:
                fail(f"{label}: hunk {len(hunks) + 1} has an unexpected line: {line!r}")
        if index < len(lines) and lines[index].startswith("\\"):
            no_newline_marker()
            index += 1
        hunks.append((old, new))
    if not hunks:
        fail(f"{label}: patch contains no hunks")
    return hunks


def apply_patch(upstream: str, patch_text: str, label: str) -> str:
    lines = upstream.splitlines(keepends=True)
    for number, (old, new) in enumerate(parse_hunks(patch_text, label), 1):
        hits = [i for i in range(len(lines) - len(old) + 1) if lines[i : i + len(old)] == old]
        if len(hits) != 1:
            fail(
                f"{label}: hunk {number} matches {len(hits)} places in the shared file (need exactly 1) "
                "-- the shared file changed under the patch; re-roll the patch against it"
            )
        lines[hits[0] : hits[0] + len(old)] = new
    return "".join(lines)


def patch_path(framework: str, rel: str) -> Path:
    return ADAPTERS / framework / PATCH_DIR / f"{rel}.patch"


def patched_text(framework: str, rel: str) -> str:
    if Path(rel).is_absolute() or ".." in Path(rel).parts:
        fail(f"shared path must be repo-relative: {rel}")
    source = ROOT / rel
    patch = patch_path(framework, rel)
    if not patch.is_file():
        fail(f"no {framework} patch for {rel} (expected {patch})")
    if not source.is_file():
        fail(f"shared file is missing: {source}")
    return apply_patch(
        source.read_text(encoding="utf-8"), patch.read_text(encoding="utf-8"), f"{framework}:{rel}"
    )


def run_generator(framework: str, rel: str, argv: list[str]) -> None:
    source = ROOT / rel
    code = compile(patched_text(framework, rel), str(source), "exec")
    module = types.ModuleType("__main__")
    module.__file__ = str(source)
    sys.modules["__main__"] = module
    sys.argv = [str(source), *argv]
    if sys.path and sys.path[0] == str(HERE):
        del sys.path[0]
    sys.path.insert(0, str(source.resolve().parent))
    exec(code, module.__dict__)


def materialize(framework: str, rel: str) -> Path:
    text = patched_text(framework, rel)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    target = ROOT / MATERIALIZE_ROOT / framework / digest / Path(rel).name
    if not (target.is_file() and target.read_text(encoding="utf-8") == text):
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
        temporary.write_text(text, encoding="utf-8")
        temporary.chmod(0o755)
        os.replace(temporary, target)
    return target


def check() -> int:
    failures = 0
    for patch in sorted(ADAPTERS.glob(f"*/{PATCH_DIR}/**/*.patch")):
        framework = patch.relative_to(ADAPTERS).parts[0]
        rel = str(patch.relative_to(ADAPTERS / framework / PATCH_DIR))[: -len(".patch")]
        try:
            text = patched_text(framework, rel)
            if rel.endswith(".py"):
                compile(text, rel, "exec")
            elif rel.endswith(".sh"):
                subprocess.run(["bash", "-n"], input=text, text=True, check=True, capture_output=True)
            print(f"OK    {framework:<16} {rel}")
        except (SystemExit, SyntaxError, subprocess.CalledProcessError) as error:
            failures += 1
            print(f"FAIL  {framework:<16} {rel}: {error}")
    return 1 if failures else 0


def main(argv: list[str]) -> int:
    if argv == ["check"]:
        return check()
    if len(argv) >= 3 and argv[0] == "generate":
        run_generator(argv[1], argv[2], argv[3:])
        return 0
    if len(argv) == 3 and argv[0] == "materialize":
        print(materialize(argv[1], argv[2]))
        return 0
    if len(argv) == 3 and argv[0] == "show":
        sys.stdout.write(patched_text(argv[1], argv[2]))
        return 0
    fail("usage: generate|materialize|show <framework> <shared path> [generator args...]  |  check")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
