#!/usr/bin/env python3
"""Tell the survey chain the truth when its inputs are empty.

Custom topics ship no source papers, so paper_list is empty, nothing is
downloaded, and /workplace/papers/ has no files -- yet three prompts keep
asserting the opposite ("I have carefully gone through these papers' github
repositories and found download some of them", "Make sure you have read these
papers thoroughly"). Models arbitrate that contradiction differently:
gpt-5.6-luna and deepseek-v4-flash shrug and write the survey from the task
brief; kimi-k2.6 obeys the letter, guessed filenames under /workplace/papers/
for 536 messages (probe archive request_probe_kimi_surveyloop_20260902.jsonl)
and had to be killed. An appended "you may skip" hint would leave the
contradiction in place for the model to arbitrate -- the exact operation the
failing model is worst at -- so instead, when an input is actually empty, the
false premise is REPLACED by a truthful statement plus a satisfiable path.

Three sites, all runtime-conditional (unchanged behavior whenever real
inputs exist, e.g. upstream's own benchmark):
  1. idea_query: papers/codebases paragraph becomes a computed variable.
  2. code_survey_query: same treatment.
  3. Paper Survey Agent instructions: rendered per-turn; check whether the
     papers directory has files and emit the truthful variant when it doesn't.
Plus one tool-layer legibility fix (unconditional, applies to all models):
  4. an empty command output is rendered as an explicit "[no output]" notice
     instead of a blank viewport, so a model can tell "produced nothing"
     from "output invisible". (The blank-viewport rendering amplified both
     kimi loops.)

Gated by AI_RESEARCHER_EMPTY_INPUT_TRUTH=1 at apply time in the wrapper.
Idempotent; fails loudly if an upstream anchor moves. Run from the
AI-Researcher source root.
"""
from __future__ import annotations

from pathlib import Path

ENTRYPOINT = Path("research_agent/run_infer_idea.py")
SURVEY_AGENT = Path("research_agent/inno/agents/inno_agent/survey_agent.py")
TERMINAL_TOOLS = Path("research_agent/inno/tools/terminal_tools.py")

IDEA_OLD = '''        idea_query = f"""\\
I have a task related to machine learning:
{data_module.TASK}
And a list of papers for your reference:
{references}

I have carefully gone through these papers' github repositories and found download some of them in my local machine, with the following information:
{prepare_res}
And I have also downloaded the corresponding paper in the Tex format, with the following information:
{download_res}
'''

IDEA_NEW = '''        if str(references).strip() or str(download_res).strip():
            _paper_context = f"""\\
And a list of papers for your reference:
{references}

I have carefully gone through these papers' github repositories and found download some of them in my local machine, with the following information:
{prepare_res}
And I have also downloaded the corresponding paper in the Tex format, with the following information:
{download_res}"""
        else:
            _paper_context = """\\
There are NO reference papers or reference codebases for this task: nothing has been downloaded, and the papers directory is empty. Do NOT try to open files under the papers directory. Ground your survey in the task description above, the dataset materials in the working directory, and your own knowledge of the relevant literature."""
        idea_query = f"""\\
I have a task related to machine learning:
{data_module.TASK}
{_paper_context}
'''

CODE_OLD = '''I have carefully gone through these papers' github repositories and found download some of them in my local machine, in the directory `/workplace`, use the `list_files` tool to navigate the directory.
And I have also downloaded the corresponding paper in the Tex format, with the following information:
{download_res}
'''

CODE_NEW = '''{_code_context}
'''

CODE_DEF = '''        if str(download_res).strip():
            _code_context = f"""\\
I have carefully gone through these papers' github repositories and found download some of them in my local machine, in the directory `/workplace`, use the `list_files` tool to navigate the directory.
And I have also downloaded the corresponding paper in the Tex format, with the following information:
{download_res}"""
        else:
            _code_context = """\\
There are NO downloaded reference papers or codebases: the papers directory is empty. The `/workplace` directory contains only the project skeleton and the task dataset -- you may use `list_files` to inspect those. Generate the implementation report from the innovative idea and your own knowledge; do NOT search for reference papers or repositories."""
        code_survey_query = f"""\\'''

CODE_QUERY_ANCHOR = '''        code_survey_query = f"""\\'''

SURVEY_OLD = '''    def instructions(context_variables):
        return f"""\\
You are a `Paper Survey Agent` specialized in analyzing academic papers. Your task is to extract and analyze specific academic concepts from research papers located in `{file_env.docker_workplace}/papers/`.'''

SURVEY_NEW = '''    def instructions(context_variables):
        import glob as _glob
        import os as _os
        _papers_local = _os.path.join(getattr(file_env, "local_workplace", "") or "", "papers")
        _has_papers = bool(_glob.glob(_os.path.join(_papers_local, "**", "*"), recursive=True)) if _os.path.isdir(_papers_local) else False
        if not _has_papers:
            return f"""\\
You are a `Paper Survey Agent`. NOTE: the papers directory `{file_env.docker_workplace}/papers/` is EMPTY -- no papers were downloaded for this task. Do NOT attempt to open, list, or guess paper files; every such attempt will fail.

Instead: write comprehensive theoretical notes for the given academic concepts from your own knowledge -- formal definitions, mathematical formulas, and key theoretical components -- and immediately transfer your notes to the `Code Survey Agent` using the `transfer_to_code_survey_agent` function.
"""
        return f"""\\
You are a `Paper Survey Agent` specialized in analyzing academic papers. Your task is to extract and analyze specific academic concepts from research papers located in `{file_env.docker_workplace}/papers/`.'''


IDEA_AGENT = Path("research_agent/inno/agents/inno_agent/idea_agent.py")

# The agent registered as name="Paper Survey Agent" in the flow is
# get_idea_agent, whose instructions hard-code the same false premise AND
# whose toolset has no directory-listing tool -- so "see what's available"
# can only be attempted by guessing file paths one at a time. When the
# papers directory is empty, emit a truthful variant that embeds a real
# listing of the files that DO exist, so nothing needs to be guessed.
IDEA_AGENT_OLD = '''    def instructions(context_variables):
        return f"""\\
You are an `Idea Generation Agent` specialized in analyzing academic papers located in `{file_env.docker_workplace}/papers/` and generating innovative ideas. Your task is to either:'''

IDEA_AGENT_NEW = '''    def instructions(context_variables):
        import glob as _glob
        import os as _os
        _lw = getattr(file_env, "local_workplace", "") or ""
        _papers_local = _os.path.join(_lw, "papers")
        _has_papers = bool(_glob.glob(_os.path.join(_papers_local, "**", "*"), recursive=True)) if _os.path.isdir(_papers_local) else False
        if not _has_papers:
            _listing = []
            for _root, _dirs, _files in _os.walk(_lw):
                _dirs[:] = [d for d in _dirs if not d.startswith(".") and d not in ("papers", "downloads", "__pycache__")]
                for _f in _files:
                    _rel = _os.path.relpath(_os.path.join(_root, _f), _lw)
                    _listing.append(f"{file_env.docker_workplace}/{_rel}")
                    if len(_listing) >= 40:
                        break
                if len(_listing) >= 40:
                    break
            _listing_text = "\\n".join(_listing) if _listing else "(the working directory has no readable files)"
            return f"""\\
You are an `Idea Generation Agent`. NOTE: there are NO research papers for this task -- the papers directory is empty, nothing was downloaded, and you have NO directory-listing tool. The following is the COMPLETE list of files that exist in your working directory; do NOT call `open_local_file` on any path that is not in this list, and do NOT guess filenames -- every guess will fail:

{_listing_text}

Your task is to either:
1. Generate comprehensive, innovative and feasible ideas for the given task, grounded in the task description, the files listed above, and your own knowledge of the relevant literature, or
2. If given multiple ideas: analyze them, select the most novel one, and enhance it into a comprehensive proposal (technical innovation, impact, feasibility, completeness).

Provide detailed technical solutions, mathematical formulations, architectural design, algorithm specifications, evaluation metrics, and expected outcomes. When your proposal is ready, use `transfer_to_code_survey_agent` for implementation research.

Remember: Your output will guide the implementation phase. Be thorough, innovative, and practical in your approach.
"""
        return f"""\\
You are an `Idea Generation Agent` specialized in analyzing academic papers located in `{file_env.docker_workplace}/papers/` and generating innovative ideas. Your task is to either:'''

TERM_OLD = '''                if res_output == "": res_output = " "'''
TERM_NEW = '''                if res_output.strip() == "": res_output = "[no output] The command completed but produced no output on stdout/stderr (this is not an error message -- there was simply nothing printed)."'''


def _apply(path: Path, old: str, new: str, label: str, text: str) -> str:
    if old not in text:
        raise SystemExit(f"empty-input-truth: anchor '{label}' not found in {path}")
    return text.replace(old, new, 1)


def main() -> None:
    if not ENTRYPOINT.is_file():
        raise SystemExit("empty-input-truth: run from the AI-Researcher source root")

    text = ENTRYPOINT.read_text(encoding="utf-8")
    if "_paper_context" in text:
        print("[empty-input-truth] entrypoint already patched")
    else:
        text = _apply(ENTRYPOINT, IDEA_OLD, IDEA_NEW, "idea_query", text)
        text = _apply(ENTRYPOINT, CODE_OLD, CODE_NEW, "code_survey_query premise", text)
        text = _apply(ENTRYPOINT, CODE_QUERY_ANCHOR, CODE_DEF, "code_survey_query header", text)
        ENTRYPOINT.write_text(text, encoding="utf-8")
        print("[empty-input-truth] entrypoint: idea_query + code_survey_query conditionalised")

    text = SURVEY_AGENT.read_text(encoding="utf-8")
    if "_has_papers" in text:
        print("[empty-input-truth] survey agent already patched")
    else:
        text = _apply(SURVEY_AGENT, SURVEY_OLD, SURVEY_NEW, "paper survey instructions", text)
        SURVEY_AGENT.write_text(text, encoding="utf-8")
        print("[empty-input-truth] survey agent: truthful empty-directory instructions")

    text = IDEA_AGENT.read_text(encoding="utf-8")
    if "_has_papers" in text:
        print("[empty-input-truth] idea agent already patched")
    else:
        text = _apply(IDEA_AGENT, IDEA_AGENT_OLD, IDEA_AGENT_NEW, "idea agent instructions", text)
        IDEA_AGENT.write_text(text, encoding="utf-8")
        print("[empty-input-truth] idea agent: truthful no-papers instructions with real file listing")

    text = TERMINAL_TOOLS.read_text(encoding="utf-8")
    if "[no output]" in text:
        print("[empty-input-truth] terminal tools already patched")
    else:
        text = _apply(TERMINAL_TOOLS, TERM_OLD, TERM_NEW, "empty terminal output", text)
        TERMINAL_TOOLS.write_text(text, encoding="utf-8")
        print("[empty-input-truth] terminal tools: empty output labelled explicitly")


if __name__ == "__main__":
    main()
