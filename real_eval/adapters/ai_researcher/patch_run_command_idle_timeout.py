#!/usr/bin/env python3
"""Bound run_command with an idle timeout and recover the serial terminal channel.

WHY (2026-09-27; pilot: 01 x ARC)
    DockerEnv.run_command loops on socket recv() with no timeout. The in-container
    command server (tcp_server.py) is strictly serial: listen(1), one connection
    served until the client closes, and a command that goes silent leaves the
    server blocked in stdout.readline() forever -- every later run_command then
    queues behind it. fullrun_arc_01_kimi_20260907_151115 wedged 36 minutes in
    exactly this state and had to be killed by hand.

DESIGN (user-approved draft)
    - Idle semantics, no command classification: every received chunk resets the
      window, so a training run that streams progress is safe at any duration.
      Only total silence for AI_RESEARCHER_RUN_COMMAND_IDLE_TIMEOUT seconds
      (default 1800; <=0 disables the whole mechanism) triggers.
    - Because the server is serial, "leave it running" would wedge the channel:
      on expiry the patch kills the stuck command's process tree inside the
      sandbox (docker exec; descendants of tcp_server.py, never the server
      itself), then keeps reading for AI_RESEARCHER_RUN_COMMAND_KILL_GRACE
      seconds (default 45) so the server's own final response -- with any
      partial output -- comes back and the channel returns to accepting
      commands.
    - If no final arrives, a synthetic final (status -124) tells the agent what
      happened and how to run long silent jobs (nohup + log file + polling).
    - Every trigger prints a [run-command-idle-timeout] line with the command
      for forensics. No behavior change while commands produce output.

Idempotent; loud on anchor drift. Run from the AI-Researcher source root.
"""
from __future__ import annotations

from pathlib import Path

TARGET = Path("research_agent/inno/environment/docker_env.py")
MARK = "run-command-idle-timeout"

ANCHOR_CONNECT = """        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((hostname, port))
            s.sendall(command.encode())
"""
ADD_CONNECT = """        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((hostname, port))
            # run-command-idle-timeout: bound total silence, not total runtime.
            _idle_s = float(os.environ.get("AI_RESEARCHER_RUN_COMMAND_IDLE_TIMEOUT", "1800"))
            if _idle_s > 0:
                s.settimeout(_idle_s)
            s.sendall(command.encode())
"""

ANCHOR_RECV = """            while True:
                chunk = s.recv(buffer_size)
                if not chunk:
                    break
"""
ADD_RECV = """            while True:
                try:
                    chunk = s.recv(buffer_size)
                except socket.timeout:
                    return _idle_timeout_recover(self, s, command, _idle_s, buffer_size)
                if not chunk:
                    break
"""

HELPER = '''

def _idle_timeout_recover(env, sock, command, idle_s, buffer_size):
    """run-command-idle-timeout: the command went silent for idle_s seconds.

    The command server is serial, so a stuck command blocks every later
    run_command. Kill its process tree inside the sandbox (descendants of
    tcp_server.py, never the server), then wait a grace period for the server's
    own final response so partial output and the channel are recovered.
    """
    grace_s = float(os.environ.get("AI_RESEARCHER_RUN_COMMAND_KILL_GRACE", "45"))
    note = (
        f"\\n[run-command-idle-timeout] no output for {int(idle_s)}s; the harness killed the "
        "stuck command inside the sandbox. Partial output (if any) is above. For long jobs "
        "that print nothing, use: nohup <cmd> > job.log 2>&1 & and poll job.log."
    )
    print(f"[run-command-idle-timeout] triggered after {int(idle_s)}s of silence; command: {command[:400]!r}", flush=True)
    container = getattr(env, "container_name", "") or ""
    killer = (
        "SRV=$(pgrep -f tcp_server.py | head -n 1); [ -n \\"$SRV\\" ] || exit 0; "
        "LVL=\\"$SRV\\"; ALL=\\"\\"; "
        "while [ -n \\"$LVL\\" ]; do NXT=\\"\\"; for p in $LVL; do NXT=\\"$NXT $(ps -o pid= --ppid $p 2>/dev/null)\\"; done; "
        "NXT=$(echo $NXT); ALL=\\"$ALL $NXT\\"; LVL=\\"$NXT\\"; done; "
        "for p in $ALL; do kill -9 $p 2>/dev/null; done; true"
    )
    if container:
        try:
            proc = subprocess.run(
                ["docker", "exec", container, "sh", "-c", killer],
                capture_output=True, text=True, timeout=60,
            )
            print(f"[run-command-idle-timeout] sandbox kill exit={proc.returncode}", flush=True)
        except Exception as exc:  # docker missing, container gone, exec timeout
            print(f"[run-command-idle-timeout] sandbox kill unavailable: {exc}", flush=True)
    # Grace window: the server should now see EOF from the killed pipe and send
    # its own final response, which frees the channel for the next command.
    try:
        sock.settimeout(max(grace_s, 1.0))
        partial_line = ""
        collected = []
        import time as _t
        deadline = _t.time() + max(grace_s, 1.0)
        while _t.time() < deadline:
            try:
                chunk = sock.recv(buffer_size)
            except socket.timeout:
                break
            if not chunk:
                break
            data = partial_line + chunk.decode("utf-8", errors="replace")
            lines = data.split("\\n")
            for line in lines[:-1]:
                if not line:
                    continue
                try:
                    response = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if response.get("type") == "chunk":
                    collected.append(str(response.get("data", "")))
                elif response.get("type") == "final":
                    return {
                        "status": response.get("status"),
                        "result": str(response.get("result", "")) + "".join(collected) + note,
                    }
            partial_line = lines[-1]
    except Exception as exc:
        print(f"[run-command-idle-timeout] grace read failed: {exc}", flush=True)
    return {"status": -124, "result": "".join([]) + note}
'''


def main() -> None:
    text = TARGET.read_text(encoding="utf-8")
    if MARK in text:
        print(f"[{MARK}] already applied")
        return
    for name, anchor in (("connect", ANCHOR_CONNECT), ("recv", ANCHOR_RECV)):
        if text.count(anchor) != 1:
            raise SystemExit(f"[{MARK}] {name} anchor not found or not unique")
    text = text.replace(ANCHOR_CONNECT, ADD_CONNECT, 1).replace(ANCHOR_RECV, ADD_RECV, 1)
    text += HELPER
    TARGET.write_text(text, encoding="utf-8")
    print(f"[{MARK}] applied: idle timeout (default 1800s) + serial-channel recovery on run_command")


if __name__ == "__main__":
    main()
