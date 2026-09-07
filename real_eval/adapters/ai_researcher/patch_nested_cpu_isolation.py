#!/usr/bin/env python3
"""Confine the nested exec container to a CPU budget (cross-tenant isolation).

WHY (2026-09-07)
    The nested experiment container is created with NO cpu limit of any kind
    (verified empirically on an identically-created container: NanoCpus=0
    CpuQuota=0 CpusetCpus empty, nproc=384 inside, zero OMP/MKL/THREADS env,
    torch.get_num_threads()=192 by default). Observed live: kimi's ordinary
    torch training grabbed ~190 host cores (19151% CPU) for 2h on the shared
    384-core machine -- a cross-tenant CPU grab, usually slower than a bounded
    run due to thread thrash. Same hazard class as the nested GPU leak fixed
    in patch_nested_gpu_isolation.

FIX
    At the nested `docker run`:
      --cpus <N>   hard cgroup ceiling (kernel-enforced; kills nothing --
                   sandbox boundary, same pattern the TDC runner already uses
                   with --cpus 4)
      -e OMP_NUM_THREADS / MKL_NUM_THREADS / OPENBLAS_NUM_THREADS /
         NUMEXPR_NUM_THREADS / TORCH_NUM_THREADS = <N>
                   so numeric stacks default to N threads instead of spawning
                   192 and thrashing against the ceiling.
    N from AI_RESEARCHER_EXEC_CPUS (default 8; <=0 disables the layer). The
    same env will feed the visibility layer's declaration text, keeping
    enforcement and disclosure from drifting.

TWO ANCHOR VARIANTS
    A: pristine docker_env.py docker_command block (ARC/babylm/mcar flows).
    B: the block as rewritten by psydef's inline wrapper patch (--add-host
       variant). Apply order in wrappers: topic inline first, gpu_isolation,
       then this. Idempotent; loud when neither anchor matches.
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
'''

VAR_A_OLD = '''        docker_command = [
            "docker", "run", "-d", "--platform", PLATFORM, "--userns=host",] + gpu_cmd + ["--name", self.container_name, '''
VAR_A_NEW = COMPUTE + '''        docker_command = [
            "docker", "run", "-d", "--platform", PLATFORM, "--userns=host",] + gpu_cmd + _nci_cmd + ["--name", self.container_name, '''

VAR_B_OLD = '''        docker_command = [
            "docker", "run", "-d", "--platform", PLATFORM, "--userns=host",
            "--add-host", "host.docker.internal:host-gateway",
        ] + gpu_cmd + ['''
VAR_B_NEW = COMPUTE + '''        docker_command = [
            "docker", "run", "-d", "--platform", PLATFORM, "--userns=host",
            "--add-host", "host.docker.internal:host-gateway",
        ] + gpu_cmd + _nci_cmd + ['''


def main() -> None:
    text = DOCKER_ENV.read_text(encoding="utf-8")
    if MARK in text:
        print(f"[{MARK}] already applied")
        return
    if VAR_A_OLD in text:
        text = text.replace(VAR_A_OLD, VAR_A_NEW, 1)
        variant = "A/pristine"
    elif VAR_B_OLD in text:
        text = text.replace(VAR_B_OLD, VAR_B_NEW, 1)
        variant = "B/psydef-inline"
    else:
        raise SystemExit(f"[{MARK}] neither docker_command anchor variant found")
    DOCKER_ENV.write_text(text, encoding="utf-8")
    print(f"[{MARK}] applied ({variant}): --cpus via AI_RESEARCHER_EXEC_CPUS (default 8) + thread env defaults")


if __name__ == "__main__":
    main()
