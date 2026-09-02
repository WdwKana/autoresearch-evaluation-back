#!/usr/bin/env python3
"""Let the file browser display text files that are not mimetype text/*.

Root cause of the 261-reopen loop (run fullrun_arc_01_kimi_20260902_085415):
the idea agent's ONLY file-reading tool is the markdown file browser, whose
PlainTextConverter accepts a file only when mimetypes.guess_type says
"text/...". metadata.json guesses application/json, every converter declines,
and open_local_file renders "Download complete." instead of the content --
for a plain-text file the agent legitimately needed. The model asked for
that file 11 times over two paths, then fell back to question_answer (whose
prompt was assembled around the empty page and returned a counter-question)
and to re-reading the brief, forever. gpt-5.6-luna and deepseek shrug at the
dead end; kimi persists -- but no model can read a JSON file through this
toolset, which is a tool defect, not a model one.

Two changes, both model-agnostic:
  1. PlainTextConverter also accepts application/json and a small whitelist
     of known-text extensions (.json/.jsonl/.yaml/.yml/.toml/.csv/.tsv/.log),
     decoding as UTF-8 with errors="replace". Real binaries still fall
     through to the download path.
  2. The "Download complete." page says the truth about what it means:
     the file cannot be displayed in this text browser, continue with other
     materials instead of retrying.

Idempotent; fails loudly if anchors move. Run from the AI-Researcher root.
"""
from __future__ import annotations

from pathlib import Path

MDCONVERT = Path("research_agent/inno/environment/markdown_browser/mdconvert.py")
BROWSER = Path("research_agent/inno/environment/markdown_browser/requests_markdown_browser.py")

GATE_OLD = '''        # Only accept text files
        if content_type is None:
            return None
        elif "text/" not in content_type.lower():
            return None

        text_content = ""
        with open(local_path, "rt", encoding="utf-8") as fh:
            text_content = fh.read()'''

GATE_NEW = '''        # Accept text files. mimetypes labels several plain-text formats as
        # application/* (json most importantly), which previously fell through
        # to "Download complete." with the content never shown.
        _ext = str(kwargs.get("file_extension", "")).lower()
        _known_text_ext = {".json", ".jsonl", ".yaml", ".yml", ".toml", ".csv", ".tsv", ".log", ".txt", ".cfg", ".ini"}
        _is_text = False
        if content_type is not None and "text/" in content_type.lower():
            _is_text = True
        elif content_type is not None and content_type.lower() in ("application/json", "application/x-yaml", "application/toml"):
            _is_text = True
        elif _ext in _known_text_ext:
            _is_text = True
        if not _is_text:
            return None

        text_content = ""
        with open(local_path, "rt", encoding="utf-8", errors="replace") as fh:
            text_content = fh.read()'''

DL_OLD = """# Download complete\\n\\nSaved file to '{download_path}'"""
DL_NEW = """# Download complete\\n\\nThis file type cannot be displayed in the text browser: there is no way to view its content with your current tools, and opening it again will show this same notice. The raw file was saved to '{download_path}'. Continue the task using the other available materials."""


def main() -> None:
    if not MDCONVERT.is_file():
        raise SystemExit("file-browser-text: run from the AI-Researcher source root")

    text = MDCONVERT.read_text(encoding="utf-8")
    if "_known_text_ext" in text:
        print("[file-browser-text] converter already patched")
    else:
        if GATE_OLD not in text:
            raise SystemExit("file-browser-text: PlainTextConverter gate anchor not found")
        MDCONVERT.write_text(text.replace(GATE_OLD, GATE_NEW, 1), encoding="utf-8")
        print("[file-browser-text] PlainTextConverter now accepts json/yaml/toml/csv text")

    text = BROWSER.read_text(encoding="utf-8")
    if "cannot be displayed in the text browser" in text:
        print("[file-browser-text] download notice already patched")
    else:
        n = text.count(DL_OLD)
        if n == 0:
            raise SystemExit("file-browser-text: download notice anchor not found")
        BROWSER.write_text(text.replace(DL_OLD, DL_NEW), encoding="utf-8")
        print(f"[file-browser-text] download notice made honest at {n} site(s)")


if __name__ == "__main__":
    main()
