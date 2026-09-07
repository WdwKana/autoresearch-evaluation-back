#!/usr/bin/env python3
"""Layer 2 of the CPU story: make resources VISIBLE to the agent.

WHY (2026-09-07, user decision: layer 2 only -- no advice, no enforcement)
    Agents design experiments blind to concrete resources: prompts say "use
    the GPU" generically but never state how many cores/GPUs exist, and a
    command's true CPU cost is never reported back. Observed costs: DS babylm
    declared device='cuda' yet trained on CPU; DS TDC mis-scaled a 4-vCPU
    training; kimi's torch grabbed 190 cores by default (now capped by
    patch_nested_cpu_isolation).

WHAT
    1. Upfront declaration, prepended to ml_dev_query (same proven anchor the
       budget clock uses, inserted after it): CPU core count read from
       AI_RESEARCHER_EXEC_CPUS -- the SAME env the --cpus enforcement reads,
       so disclosure cannot drift from enforcement -- plus GPU visibility
       derived from CUDA_VISIBLE_DEVICES/GPUS.
    2. A usage line prefixed to a command's result when it ran long enough
       (default >= 30s wall, env AI_RESEARCHER_RESOURCE_LINE_MIN_SECONDS):
         [resources] avg ~3.9 cores (peak 8.0) over 47m
       Nested-container path: a daemon sampler thread polls `docker stats`
       every 15s while run_command blocks (docker CLI is present -- it is how
       the nested container was created). TDC local path: exact CPU seconds
       from os.times() children delta, no sampling.
       Short commands get no line (noise discipline, per the clock lesson).

    Wrapper pattern (rename body to _impl, public wrapper adds measurement in
    try/finally) -- same mechanics as patch_browser_tool_timeout, so the
    sampler always stops even on exceptions.

VARIANTS
    docker_env run_command: A = pristine socket loop; T = TDC topic patch's
    local subprocess version. Idempotent; loud when nothing matches.
"""
from __future__ import annotations

from pathlib import Path

DOCKER_ENV = Path("research_agent/inno/environment/docker_env.py")
ENTRY = Path("research_agent/run_infer_idea.py")
MARK = "resource-visibility"

HELPERS = '''# resource-visibility helpers (layer 2: measurement + formatting)
import os as _rv_os
import time as _rv_time
import threading as _rv_threading
import subprocess as _rv_subprocess


def _rv_min_seconds():
    return int(_rv_os.getenv("AI_RESEARCHER_RESOURCE_LINE_MIN_SECONDS", "30") or 0)


def _rv_format(avg_cores, peak_cores, wall_s):
    mins = int(wall_s // 60)
    secs = int(wall_s % 60)
    dur = (str(mins) + "m" + str(secs) + "s") if mins else (str(secs) + "s")
    return ("[resources] this command used ~" + format(avg_cores, ".1f")
            + " CPU cores on average (peak " + format(peak_cores, ".1f")
            + ") over " + dur + "\\n")


class _RvSampler:
    """Polls `docker stats` for a container while a command runs."""

    def __init__(self, container_name, interval=15):
        self.name = container_name
        self.interval = interval
        self.samples = []
        self._stop = _rv_threading.Event()
        self._t = None

    def __enter__(self):
        def _loop():
            while not self._stop.wait(self.interval):
                try:
                    out = _rv_subprocess.run(
                        ["docker", "stats", "--no-stream", "--format",
                         "{{.CPUPerc}}", self.name],
                        capture_output=True, text=True, timeout=10)
                    v = out.stdout.strip().rstrip("%")
                    if v:
                        self.samples.append(float(v))
                except Exception:
                    pass
        self._t = _rv_threading.Thread(target=_loop, daemon=True)
        self._t.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        return False

    def line(self, wall_s):
        if not self.samples or wall_s < _rv_min_seconds():
            return ""
        avg = sum(self.samples) / len(self.samples) / 100.0
        peak = max(self.samples) / 100.0
        return _rv_format(avg, peak, wall_s)
'''

# ---- variant A: pristine socket-loop run_command (nested container path) ----
A_OLD = '''    def run_command(self, command, stream_callback=None):
        """
        communicate with docker container and execute command, support stream output
'''
A_NEW = '''    def run_command(self, command, stream_callback=None):
        # resource-visibility: measure the nested container's CPU while the
        # command runs; prefix a usage line to long commands' results.
        _rv_t0 = _rv_time.time()
        with _RvSampler(self.container_name) as _rv_s:
            _rv_r = self._rv_run_command_impl(command, stream_callback)
        try:
            _rv_line = _rv_s.line(_rv_time.time() - _rv_t0)
            if _rv_line and isinstance(_rv_r, dict) and isinstance(_rv_r.get("result"), str):
                _rv_r["result"] = _rv_line + _rv_r["result"]
        except Exception:
            pass
        return _rv_r

    def _rv_run_command_impl(self, command, stream_callback=None):
        """
        communicate with docker container and execute command, support stream output
'''

# ---- variant T: TDC topic patch's local subprocess run_command ----
T_OLD = '''    def run_command(self, command, stream_callback=None):
        # Local execution path for TDC (no nested container / socket).
'''
T_NEW = '''    def run_command(self, command, stream_callback=None):
        # resource-visibility: exact CPU seconds via children rusage delta.
        _rv_t0 = _rv_time.time()
        _rv_c0 = _rv_os.times()
        _rv_r = self._rv_run_command_impl(command, stream_callback)
        try:
            _rv_wall = _rv_time.time() - _rv_t0
            _rv_c1 = _rv_os.times()
            _rv_cpu = (_rv_c1.children_user - _rv_c0.children_user) + (_rv_c1.children_system - _rv_c0.children_system)
            if _rv_wall >= _rv_min_seconds() and _rv_wall > 0 and isinstance(_rv_r, dict) and isinstance(_rv_r.get("result"), str):
                _rv_avg = _rv_cpu / _rv_wall
                _rv_r["result"] = _rv_format(_rv_avg, _rv_avg, _rv_wall) + _rv_r["result"]
        except Exception:
            pass
        return _rv_r

    def _rv_run_command_impl(self, command, stream_callback=None):
        # Local execution path for TDC (no nested container / socket).
'''

# ---- declaration in run_infer_idea (after budget clock's rules) ----
QUERY_ANCHOR = '        messages = [{"role": "user", "content": ml_dev_query}]'
QUERY_NEW = '''        _rv_cpus = int(__import__("os").getenv("AI_RESEARCHER_EXEC_CPUS", "8") or 0)
        _rv_cvd = (__import__("os").getenv("CUDA_VISIBLE_DEVICES", "") or "").strip()
        if _rv_cvd and _rv_cvd not in ("all", "-1"):
            _rv_gpu = str(len([x for x in _rv_cvd.split(",") if x and x != "-1"])) + " GPU(s)"
        elif __import__("os").getenv("GPUS"):
            _rv_gpu = "GPU available"
        else:
            _rv_gpu = "no GPU"
        if _rv_cpus > 0:
            ml_dev_query = ("[resources] Execution environment: " + str(_rv_cpus)
                            + " CPU cores (hard limit; numeric libraries default to "
                            + str(_rv_cpus) + " threads) and " + _rv_gpu
                            + ". Long commands report their measured CPU usage in a [resources] line. "
                            "Design experiments to fit these resources.\\n\\n") + ml_dev_query
        messages = [{"role": "user", "content": ml_dev_query}]'''


def patch(path: Path, pairs, required=True) -> bool:
    text = path.read_text(encoding="utf-8")
    changed = False
    for old, new in pairs:
        if new in text:
            continue
        if old not in text:
            if required:
                raise SystemExit(f"[{MARK}] anchor not found in {path}: {old[:60]!r}")
            return False
        text = text.replace(old, new, 1)
        changed = True
    if changed:
        path.write_text(text, encoding="utf-8")
    return True


def main() -> None:
    text = DOCKER_ENV.read_text(encoding="utf-8")
    if MARK in text:
        print(f"[{MARK}] docker_env already patched")
    else:
        if "import socket" not in text:
            raise SystemExit(f"[{MARK}] docker_env import anchor missing")
        text = text.replace("import socket", "import socket\n" + HELPERS, 1)
        if T_OLD in text:
            text = text.replace(T_OLD, T_NEW, 1)
            variant = "T/tdc-local"
        elif A_OLD in text:
            text = text.replace(A_OLD, A_NEW, 1)
            variant = "A/socket"
        else:
            raise SystemExit(f"[{MARK}] no run_command variant matched")
        DOCKER_ENV.write_text(text, encoding="utf-8")
        print(f"[{MARK}] docker_env patched ({variant})")
    patch(ENTRY, [(QUERY_ANCHOR, QUERY_NEW)])
    print(f"[{MARK}] applied: upfront declaration + [resources] usage line "
          "(AI_RESEARCHER_RESOURCE_LINE_MIN_SECONDS, default 30s)")


if __name__ == "__main__":
    main()
