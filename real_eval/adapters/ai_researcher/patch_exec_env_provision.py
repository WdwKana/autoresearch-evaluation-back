#!/usr/bin/env python3
"""Provision the sandbox container with the dataset's own reader libraries.

The topics ship parquet datasets, but the ai-researcher-exec runtime image
has numpy/torch and NO pyarrow/pandas -- the ML agent's very first data probe
dies with ModuleNotFoundError. Historically masked by accident: the Prepare
Agent's exploration used to run `pip install pandas pyarrow` inside the
container as a side effect, and the ML phase inherited it. The (correct)
prepare bypass removed that accidental provisioning and exposed the gap:
in fullrun_arc_01_dsv_20260902_101926 deepseek probed the parquet, hit
ModuleNotFoundError, and submitted an empty case_resolved on the next turn.

Install the readers once, right after the sandbox container is created --
infrastructure provisioning only, no research content. Package list
overridable via AI_RESEARCHER_EXEC_PIP; empty string disables. Non-fatal on
failure (the agent can still pip install by itself). Idempotent; loud on
anchor drift. Run from the AI-Researcher source root.
"""
from __future__ import annotations

from pathlib import Path

DOCKER_ENV = Path("research_agent/inno/environment/docker_env.py")

OLD = '''        if self.wait_for_container_ready(timeout=60):
            print(f"Container '{self.container_name}' has been created and started.")'''

NEW = '''        if self.wait_for_container_ready(timeout=60):
            print(f"Container '{self.container_name}' has been created and started.")
        # The task datasets ship as parquet; the runtime image lacks the
        # readers (numpy/torch only). Provision once at container creation.
        try:
            _prov = os.getenv("AI_RESEARCHER_EXEC_PIP", "pyarrow pandas")
            if _prov.strip():
                _cmd = ["docker", "exec", self.container_name, "pip", "install", "--quiet"] + _prov.split()
                _res = subprocess.run(_cmd, capture_output=True, text=True, timeout=600)
                print(f"[exec-env-provision] pip install {_prov}: rc={_res.returncode}"
                      + ("" if _res.returncode == 0 else f" err={_res.stderr[-200:]}"))
        except Exception as _exc:
            print(f"[exec-env-provision] non-fatal: {_exc}")'''


def main() -> None:
    if not DOCKER_ENV.is_file():
        raise SystemExit("exec-env-provision: run from the AI-Researcher source root")
    text = DOCKER_ENV.read_text(encoding="utf-8")
    if "exec-env-provision" in text:
        print("[exec-env-provision] already applied")
        return
    if OLD not in text:
        raise SystemExit("exec-env-provision: init_container anchor not found")
    DOCKER_ENV.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print("[exec-env-provision] sandbox will get: " + "pyarrow pandas (override via AI_RESEARCHER_EXEC_PIP)")


if __name__ == "__main__":
    main()
