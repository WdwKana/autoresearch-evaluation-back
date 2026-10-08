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
        had been executed (same __file__, argv[0], sys.path[0], exit code)
    shared_layer_overlay.py materialize <framework> <shared .sh>
        first apply every patch of that framework (so a stale patch stops the
        launch before the runner has created a run directory or started a
        relay), then write the patched runner under
        real_eval/run_checks/shared_layer_overlay/ (content-addressed, an
        existing copy is never rewritten) and print its path; the caller
        exports RESEARCHCLAWEVAL_ROOT and execs it
    shared_layer_overlay.py show        <framework> <shared file>
        print the patched text
    shared_layer_overlay.py check
        apply every patch of every framework, syntax-check the result, and
        confirm every overlay call site in the 01_/02_ wrappers and the 02
        ladder launchers names a patch that exists

STRICTNESS
    Every hunk is located in the pristine shared text: its old side (context +
    removed lines) must occur there exactly once, hunks must not overlap, line
    numbers are ignored and nothing is fuzzed. When upstream changes a patched
    region the launch stops here, loudly, instead of running something
    half-patched.

ROOT
    The checkout this file lives in, spelled the way the caller invoked it (no
    symlink resolution: docker bind mounts must keep the caller's prefix). A
    RESEARCHCLAWEVAL_ROOT that names a different checkout is an error.
"""
from __future__ import annotations

import builtins
import glob
import hashlib
import linecache
import os
import re
import subprocess
import sys
import types
from pathlib import Path

HERE = Path(os.path.abspath(__file__)).parent  # real_eval/adapters
ROOT = HERE.parents[1]
PATCH_DIR = "shared_layer_patches"
MATERIALIZE_ROOT = Path("real_eval/run_checks/shared_layer_overlay")
CALL_SITE_GLOBS = ("real_eval/scripts/0[12]_*.sh", "debug/dawei/ladder/**/*.sh")
HUNK_HEADER = re.compile(r"^@@ -\d+(?:,(\d+))? \+\d+(?:,(\d+))? @@")
OVERLAY_CALL = re.compile(r"shared_layer_overlay\.py\"?\s+(generate|materialize)\s+(\S+)\s+\"?([^\s\"\\)]+)")
ADAPTER_CALL = re.compile(r"mountaincar_continuous/generate_native_inputs\.py\"?\s+(\S+)")
TAG = "[shared-layer-overlay]"


def fail(message: str):
    raise SystemExit(f"{TAG} {message}")


def check_root_env() -> None:
    env = os.environ.get("RESEARCHCLAWEVAL_ROOT")
    if env and not (os.path.isdir(env) and os.path.samefile(env, ROOT)):
        fail(f"RESEARCHCLAWEVAL_ROOT={env} is not the checkout this overlay lives in ({ROOT})")


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def parse_hunks(patch_text: str, label: str, rel: str | None = None) -> list[tuple[list[str], list[str]]]:
    """Return [(old side lines, new side lines)] of a one-file unified diff."""
    lines = patch_text.splitlines(keepends=True)
    index = 0
    while index < len(lines) and not HUNK_HEADER.match(lines[index]):
        line = lines[index]
        if rel is not None and line.startswith("+++ "):
            named = line[4:].split("\t")[0].strip()
            if named.startswith("b/"):
                named = named[2:]
            if named != rel:
                fail(f"{label}: patch header names {named!r}, not the target {rel!r}")
        index += 1  # leading commentary and the ---/+++ file header
    hunks: list[tuple[list[str], list[str]]] = []
    while index < len(lines):
        header = HUNK_HEADER.match(lines[index])
        if not header:
            if all(not l.strip() for l in lines[index:]):
                break  # trailing blank lines at end of file
            fail(f"{label}: unexpected text after hunk {len(hunks)}: {lines[index]!r}")
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


def apply_patch(upstream: str, patch_text: str, label: str, rel: str | None = None) -> str:
    lines = upstream.splitlines(keepends=True)
    located: list[tuple[int, int, list[str], list[str]]] = []
    for number, (old, new) in enumerate(parse_hunks(patch_text, label, rel), 1):
        if not old:
            fail(f"{label}: hunk {number} has no context or removed lines and cannot be located")
        hits = [i for i in range(len(lines) - len(old) + 1) if lines[i : i + len(old)] == old]
        if len(hits) != 1:
            fail(
                f"{label}: hunk {number} matches {len(hits)} places in the shared file (need exactly 1) "
                "-- the shared file changed under the patch; re-roll the patch against it"
            )
        located.append((hits[0], number, old, new))
    located.sort(key=lambda item: item[0])
    for (start, number, old, _), (next_start, next_number, _, _) in zip(located, located[1:]):
        if start + len(old) > next_start:
            fail(f"{label}: hunks {number} and {next_number} overlap in the shared file")
    for start, _, old, new in reversed(located):  # from the end: earlier offsets stay valid
        lines[start : start + len(old)] = new
    return "".join(lines)


def patch_path(framework: str, rel: str) -> Path:
    return HERE / framework / PATCH_DIR / f"{rel}.patch"


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
        source.read_text(encoding="utf-8"), patch.read_text(encoding="utf-8"), f"{framework}:{rel}", rel
    )


def provenance(framework: str, rel: str, text: str, extra: str = "") -> None:
    shared = (ROOT / rel).read_text(encoding="utf-8")
    patch = patch_path(framework, rel).read_text(encoding="utf-8")
    print(f"{TAG} {framework} {rel}: shared {digest(shared)} + patch {digest(patch)} -> {digest(text)}{extra}", file=sys.stderr)


def run_generator(framework: str, rel: str, argv: list[str]) -> None:
    source = ROOT / rel
    text = patched_text(framework, rel)
    provenance(framework, rel, text)
    # dont_inherit: the generator must not pick up this module's own __future__ imports
    code = compile(text, str(source), "exec", dont_inherit=True)
    module = types.ModuleType("__main__")
    module.__file__ = str(source)
    module.__builtins__ = builtins
    # tracebacks of the patched text must show the patched lines, not the shared file's
    linecache.cache[str(source)] = (len(text), None, text.splitlines(keepends=True), str(source))
    sys.modules["__main__"] = module
    sys.argv = [str(source), *argv]
    if sys.path and sys.path[0] == str(HERE):
        del sys.path[0]
    sys.path.insert(0, str(source.resolve().parent))
    exec(code, module.__dict__)


def framework_patches(framework: str) -> list[str]:
    base = HERE / framework / PATCH_DIR
    return sorted(str(p.relative_to(base))[: -len(".patch")] for p in base.rglob("*.patch"))


def verify_patch(framework: str, rel: str) -> str:
    """Apply one patch and syntax-check the result; raises SystemExit on any problem."""
    text = patched_text(framework, rel)
    if rel.endswith(".py"):
        try:
            compile(text, rel, "exec", dont_inherit=True)
        except SyntaxError as error:
            fail(f"{framework}:{rel}: patched text is not valid Python: {error}")
    elif rel.endswith(".sh"):
        result = subprocess.run(["bash", "-n"], input=text, text=True, capture_output=True)
        if result.returncode != 0:
            fail(f"{framework}:{rel}: patched text is not valid bash: {result.stderr.strip()}")
    return text


def materialize(framework: str, rel: str) -> Path:
    for other in framework_patches(framework):  # pre-flight: every patch of this framework still applies
        verify_patch(framework, other)
    text = patched_text(framework, rel)
    target = ROOT / MATERIALIZE_ROOT / framework / digest(text) / Path(rel).name
    if not (target.is_file() and target.read_text(encoding="utf-8") == text):
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
        temporary.write_text(text, encoding="utf-8")
        temporary.chmod(0o755)
        os.replace(temporary, target)
    provenance(framework, rel, text, f" -> {target}")
    return target


def check() -> int:
    failures = 0
    frameworks = sorted(p.parent.name for p in HERE.glob(f"*/{PATCH_DIR}"))
    for framework in frameworks:
        for rel in framework_patches(framework):
            try:
                verify_patch(framework, rel)
                print(f"OK    {framework:<16} {rel}")
            except SystemExit as error:
                failures += 1
                print(f"FAIL  {error}")
    sites = 0
    for pattern in CALL_SITE_GLOBS:
        for path in sorted(glob.glob(str(ROOT / pattern), recursive=True)):
            text = Path(path).read_text(encoding="utf-8", errors="replace")
            for _, framework, rel in OVERLAY_CALL.findall(text):
                sites += 1
                if not patch_path(framework, rel).is_file():
                    failures += 1
                    print(f"FAIL  call site {os.path.relpath(path, ROOT)} names a missing patch: {framework} {rel}")
            for framework in ADAPTER_CALL.findall(text):
                sites += 1
                if framework not in frameworks:
                    failures += 1
                    print(f"FAIL  call site {os.path.relpath(path, ROOT)} passes an unknown framework to the mcar adapter: {framework}")
    print(f"call sites checked: {sites}; failures: {failures}")
    return 1 if failures else 0


def main(argv: list[str]) -> int:
    check_root_env()
    if argv == ["check"]:
        return check()
    if len(argv) >= 3 and argv[0] == "generate":
        run_generator(argv[1], argv[2], argv[3:])
        return 0
    if len(argv) == 3 and argv[0] == "materialize":
        print(materialize(argv[1], argv[2]))
        return 0
    if len(argv) == 3 and argv[0] == "show":
        sys.stdout.buffer.write(patched_text(argv[1], argv[2]).encode("utf-8"))
        return 0
    fail("usage: generate|materialize|show <framework> <shared path> [generator args...]  |  check")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
