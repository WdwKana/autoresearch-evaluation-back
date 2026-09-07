#!/usr/bin/env python3
"""Confine the nested exec container to a CPU budget (cross-tenant isolation).

WHY (2026-09-07)
    The nested experiment container is created with NO cpu limit of any kind
    (verified: NanoCpus=0 CpuQuota=0 CpusetCpus empty, nproc=384 inside, zero
    OMP/MKL/THREADS env, torch.get_num_threads()=192 by default). Observed
    live: kimi's ordinary torch training grabbed ~190 host cores (19151% CPU)
    for 2h on the shared machine -- cross-tenant CPU grab plus thread-thrash,
    same hazard class as the nested GPU leak (cf7229d).

FIX
    At the nested `docker run`: --cpus N (AI_RESEARCHER_EXEC_CPUS, default 8,
    <=0 disables) + OMP/MKL/OPENBLAS/NUMEXPR/TORCH thread env = N. Kernel
    cgroup boundary; kills nothing, same pattern the TDC runner already uses.

ANCHORS (whitespace-robust)
    Two edits, both keyed on substrings that carry NO trailing whitespace and
    are identical across source variants (the docker_command block differs by
    a trailing space and by psydef's --add-host rewrite between checkouts):
      1. insert the _nci_cmd computation right before `docker_command = [`
      2. splice `_nci_cmd` into the arg list at `] + gpu_cmd + [`
    Both `] + gpu_cmd + [` (pristine and psydef-inline share it) are matched.
    Idempotent; loud when either anchor is missing.
"""
from __future__ import annotations

from pathlib import Path

DOCKER_ENV = Path("research_agent/inno/environment/docker_env.py")
MARK = "nested-cpu-isolation"

COMPUTE = '''        # nested-cpu-isolation: hard CPU ceiling + sane thread defaults so a
        # single experiment cannot grab the whole shared host (observed: torch
        # defaulted to 192 threads / ~190 cores here).
        import os as _nci_os
        _nci_n = int(_nci_os.getenv("AI_RESEARCHER_EXEC_CPUS", "8") or 0)
        _nci_cmd = []
        if _nci_n > 0:
            _nci_cmd = ["--cpus", str(_nci_n)]
            for _nci_var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS",
                             "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS",
                             "TORCH_NUM_THREADS"):
                _nci_cmd += ["-e", _nci_var + "=" + str(_nci_n)]
        docker_command = ['''

INSERT_ANCHOR = "        docker_command = ["
SPLICE_OLD = "] + gpu_cmd + ["
SPLICE_NEW = "] + gpu_cmd + _nci_cmd + ["


def main() -> None:
    text = DOCKER_ENV.read_text(encoding="utf-8")
    if MARK in text:
        print(f"[{MARK}] already applied")
        return
    if INSERT_ANCHOR not in text:
        raise SystemExit(f"[{MARK}] insert anchor 'docker_command = [' not found")
    if SPLICE_OLD not in text:
        raise SystemExit(f"[{MARK}] splice anchor '] + gpu_cmd + [' not found")
    # order matters: splice first (INSERT_ANCHOR is a prefix of COMPUTE's tail),
    # then prepend the computation before the (first) docker_command assembly.
    text = text.replace(SPLICE_OLD, SPLICE_NEW, 1)
    text = text.replace(INSERT_ANCHOR, COMPUTE, 1)
    DOCKER_ENV.write_text(text, encoding="utf-8")
    print(f"[{MARK}] applied: --cpus via AI_RESEARCHER_EXEC_CPUS (default 8) + thread env defaults")


if __name__ == "__main__":
    main()
