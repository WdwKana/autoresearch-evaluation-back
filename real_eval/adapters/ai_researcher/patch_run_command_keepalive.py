#!/usr/bin/env python3
"""Revive a dead inner-sandbox channel by restarting the framework's own container.

WHY (2026-09-28; port of the ARC wrapper's inline keepalive to the other topics)
    The inner sandbox's tcp server can die mid-run; the client is a bare socket
    with no recovery, so every later command returns "[Errno 111] Connection
    refused" until the run ends with nothing (fullrun_babylm_01_g6luna_20260928_061209:
    23 consecutive refusals, workspace lost, scorer failed closed). The ARC
    wrapper has carried this recovery inline since 2026-08-28 and it fired
    successfully in both ARC runs on 2026-09-28. Infrastructure-level only:
    restart the framework's own container exactly as its init created it and
    retry the command. No research content is touched.

Idempotent (skips when the ARC inline version or this patch is already present);
loud on anchor drift. Run from the AI-Researcher source root.
"""
from __future__ import annotations

from pathlib import Path

TARGET = Path("research_agent/inno/environment/docker_env.py")
MARK = "_arc_raw_run_command"

OLD = "    def run_command(self, command, stream_callback=None):"
NEW = '''    def run_command(self, command, stream_callback=None):
        import subprocess as _arc_sp
        import time as _arc_time
        for _arc_attempt in range(3):
            try:
                return self._arc_raw_run_command(command, stream_callback)
            except (ConnectionRefusedError, ConnectionResetError, BrokenPipeError) as exc:
                if _arc_attempt == 2:
                    raise
                print(f"[arc-keepalive] inner channel dead ({exc}); restarting sandbox container")
                _arc_sp.run(["docker", "restart", self.container_name], capture_output=True)
                _arc_time.sleep(10)
                self.wait_for_container_ready()

    def _arc_raw_run_command(self, command, stream_callback=None):'''


def main() -> None:
    text = TARGET.read_text(encoding="utf-8")
    if MARK in text:
        print(f"[run-command-keepalive] already applied (or the ARC inline version is present)")
        return
    if text.count(OLD) != 1:
        raise SystemExit("[run-command-keepalive] run_command anchor not found or not unique")
    TARGET.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print("[run-command-keepalive] applied: dead inner channel now restarts the sandbox and retries (x3)")


if __name__ == "__main__":
    main()
