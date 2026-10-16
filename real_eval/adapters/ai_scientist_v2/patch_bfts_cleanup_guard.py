#!/usr/bin/env python3
"""AI-Scientist-v2: two end-of-run cleanup defects in launch_scientist_bfts.py (02 ARC formal wrapper).

Upstream copies experiment_results only "if os.path.exists(...)" but then removes it unconditionally,
so a run whose stages produced no aggregated results directory crashes at the very end, after all BFTS
work is done (fullrun_arc_02_bounded_20260827_{081051,082742_b,084434}); and the orphan-process cleanup
could SIGTERM its own process. argv: <launch_scientist_bfts.py>
"""
from pathlib import Path
import sys

# Upstream copies experiment_results only "if os.path.exists(...)" but then
# removes it unconditionally, so a run whose stages produced no aggregated
# results directory crashes at the very end -- after all BFTS work is done
# (observed in runs fullrun_arc_02_bounded_20260827_{081051,082742_b,084434}).
path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
old = '    shutil.rmtree(osp.join(idea_dir, "experiment_results"))'
new = (
    '    _arc_results_dir = osp.join(idea_dir, "experiment_results")\n'
    '    if osp.exists(_arc_results_dir):\n'
    '        shutil.rmtree(_arc_results_dir)'
)
if old in text:
    text = text.replace(old, new, 1)
else:
    print("SKIP: experiment_results cleanup insertion point not found")
old_kw = 'keywords = ["python", "torch", "mp", "bfts", "experiment"]'
new_kw = ('keywords = ["python", "torch", "mp", "bfts", "experiment"]\n'
          '    _arc_self_pids = {current_process.pid, current_process.ppid()}')
if old_kw in text and "_arc_self_pids" not in text:
    text = text.replace(old_kw, new_kw, 1)
old_sig = """            if any(keyword in cmdline for keyword in keywords):
                proc.send_signal(signal.SIGTERM)"""
new_sig = """            if any(keyword in cmdline for keyword in keywords) and proc.pid not in _arc_self_pids:
                proc.send_signal(signal.SIGTERM)"""
if old_sig in text:
    text = text.replace(old_sig, new_sig, 1)
else:
    print("SKIP: orphan-cleanup insertion point not found")
path.write_text(text, encoding="utf-8")
