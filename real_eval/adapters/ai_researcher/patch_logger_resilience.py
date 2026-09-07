#!/usr/bin/env python3
"""Stop a log-formatting failure from crashing the whole run.

WHY (2026-09-07)
    logger._warp_args does `json.loads(args_dict)` on a tool call's raw
    arguments string purely to pretty-print it in the log. When a model emits
    a large or specially-escaped argument (observed: kimi ARC run 120826, a
    ~5.6KB idea proposal packed into a `question` field, JSONDecodeError at
    char 5645), this uncaught exception propagates all the way up through
    judge_agent -> forward -> asyncio.run and kills the entire native run
    (exit 1). A cosmetic logging step must never abort the experiment.

FIX
    Wrap the parse/format in try/except: on any failure, fall back to
    printing the raw string (truncated). Pure resilience -- the success path
    is byte-identical, only the crash path changes (from "abort run" to "log
    the raw args"). No agent logic touched.

Idempotent; loud on anchor drift. Run from the AI-Researcher source root.
"""
from __future__ import annotations

from pathlib import Path

LOGGER = Path("research_agent/inno/logger.py")
MARK = "logger-resilience"

OLD = '''    def _warp_args(self, args_dict: str):
        args_dict = json.loads(args_dict)
        args_str = ''
        for k, v in args_dict.items():
            args_str += f"{repr(k)}={repr(v)}, "
        return args_str[:-2]'''

NEW = '''    def _warp_args(self, args_dict: str):
        # logger-resilience: a cosmetic log format must never crash the run.
        try:
            parsed = json.loads(args_dict)
            args_str = ''
            for k, v in parsed.items():
                args_str += f"{repr(k)}={repr(v)}, "
            return args_str[:-2]
        except Exception:
            raw = args_dict if isinstance(args_dict, str) else repr(args_dict)
            if len(raw) > 2000:
                raw = raw[:2000] + "...<truncated>"
            return raw'''


def main() -> None:
    text = LOGGER.read_text(encoding="utf-8")
    if MARK in text:
        print(f"[{MARK}] already applied")
        return
    if OLD not in text:
        raise SystemExit(f"[{MARK}] anchor not found (logger._warp_args)")
    LOGGER.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print(f"[{MARK}] applied: _warp_args parse failure now logs raw args instead of crashing the run")


if __name__ == "__main__":
    main()
