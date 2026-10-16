#!/usr/bin/env python3
"""01 x BabyLM: resolve the writeup's hard-coded agent cache file list against what the research phase wrote (host-side).

compose_section() hardcodes a list of agent cache files, but the research phase writes
paper_survey_agent.json / code_survey_agent.json -- there is no survey_agent.json -- so paper composition
dies with FileNotFoundError after the research is finished (fullrun_babylm_01_20260828_051721, _144108).
Resolve the list once where it is built; absent files are skipped with a warning.

argv: <paper_agent/methodology_composing_using_template.py>
"""
from pathlib import Path
import sys

# compose_section() hardcodes a list of agent cache files, but the research phase
# writes paper_survey_agent.json / code_survey_agent.json -- there is no
# survey_agent.json -- so paper composition dies with FileNotFoundError after the
# research work is finished. Two separate loops consume this list (runs
# fullrun_babylm_01_20260828_051721 and _144108 died at one each), so resolve the
# list once where it is built instead of guarding each consumer in turn.
path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
old = """        agent_files = [
            'prepare_agent.json',
            'survey_agent.json',
            'coding_plan_agent.json',
            'machine_learning_agent.json',
            'judge_agent.json',
            'machine_learning_agent_iter_submit.json',
            'experiment_analysis_agent_iter_refine_1.json',
            'machine_learning_agent_iter_refine_1.json',
        ]"""
new = """        _requested_agent_files = [
            'prepare_agent.json',
            'survey_agent.json',
            'coding_plan_agent.json',
            'machine_learning_agent.json',
            'judge_agent.json',
            'machine_learning_agent_iter_submit.json',
            'experiment_analysis_agent_iter_refine_1.json',
            'machine_learning_agent_iter_refine_1.json',
        ]
        _agent_aliases = {
            'survey_agent.json': ['survey_agent.json', 'paper_survey_agent.json', 'code_survey_agent.json'],
        }
        agent_files = []
        for _requested in _requested_agent_files:
            _resolved = next(
                (c for c in _agent_aliases.get(_requested, [_requested])
                 if os.path.isfile(os.path.join(agent_dir, c))),
                None,
            )
            if _resolved is None:
                logging.warning(f"skipping absent agent cache file: {_requested}")
                continue
            agent_files.append(_resolved)"""
if old in text:
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
elif "_requested_agent_files" not in text:
    print("SKIP: agent_files definition not found")
