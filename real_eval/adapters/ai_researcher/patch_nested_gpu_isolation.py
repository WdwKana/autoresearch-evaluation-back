#!/usr/bin/env python3
"""Confine the nested exec container to the allowed GPUs.

WHY (2026-09-07)
    docker_env.init_container creates the nested experiment container with
    `--gpus GPUS` where GPUS defaults to "all" (babylm wrapper sets GPUS=all).
    The outer container's CUDA_VISIBLE_DEVICES (=REAL_EVAL_ALLOWED_GPUS, e.g.
    "4") applies ONLY to the outer framework process -- it is NOT propagated
    into the nested container. Result: the agent's training code sees ALL 8
    GPUs and can land on cards other tenants are using. This is a real
    cross-tenant hazard, not just untidiness.

FIX
    Physical isolation at the nested `docker run`: if CUDA_VISIBLE_DEVICES is
    set on the outer process, request exactly those devices via
    `--gpus "device=<ids>"`, so the NVIDIA runtime mounts only those cards
    into the nested container (the agent cannot reach any other GPU no matter
    what device string its code uses). Falls back to the old `--gpus GPUS`
    only when CUDA_VISIBLE_DEVICES is unset, and to no-GPU when GPUS is empty
    (unchanged for ARC/psydef which pass GPUS=). Note: with device= the nested
    container renumbers the mounted cards from 0, so we deliberately do NOT
    also inject CUDA_VISIBLE_DEVICES into it (that would point at a
    now-nonexistent host index).

Idempotent; loud on anchor drift. Run from the AI-Researcher source root.
Applies to docker_env.py. Compatible with exec_env_provision (different site).
"""
from __future__ import annotations

from pathlib import Path

DOCKER_ENV = Path("research_agent/inno/environment/docker_env.py")
MARK = "nested-gpu-isolation"

OLD = '        gpu_cmd = ["--gpus", GPUS] if GPUS else []'
NEW = '''        # nested-gpu-isolation: confine the nested container to the outer
        # process's allowed GPUs so it cannot land on another tenant's card.
        import os as _ngi_os
        _ngi_cvd = (_ngi_os.getenv("CUDA_VISIBLE_DEVICES", "") or "").strip()
        if _ngi_cvd and _ngi_cvd not in ("all", "-1"):
            gpu_cmd = ["--gpus", "device=" + _ngi_cvd]
        elif GPUS:
            gpu_cmd = ["--gpus", GPUS]
        else:
            gpu_cmd = []'''


def main() -> None:
    text = DOCKER_ENV.read_text(encoding="utf-8")
    if MARK in text:
        print(f"[{MARK}] already applied")
        return
    if OLD not in text:
        raise SystemExit(f"[{MARK}] anchor not found: {OLD!r}")
    DOCKER_ENV.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print(f"[{MARK}] applied: nested container confined to CUDA_VISIBLE_DEVICES via --gpus device=")


if __name__ == "__main__":
    main()
