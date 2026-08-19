#!/usr/bin/env python3
"""Patch AutoResearchClaw literature screen: when model rejects all candidates,
fall back to keyword-based filtering instead of pausing the pipeline."""
import json
from pathlib import Path

lit_path = Path("/workspace/researchclaw/pipeline/stage_impls/_literature.py")
if not lit_path.is_file():
    print("[patch] _literature.py not found, skipping")
    raise SystemExit(0)

text = lit_path.read_text(encoding="utf-8")

# Find the exact boundaries by looking for unique markers
old_start = "    if model_rejected_all:"

# The end marker: the closing paren of the StageResult return
# We search for the decision="rejected_all" line and its closing paren
end_marker_line = '            decision="rejected_all",'
close_paren_line = "        )"

start_idx = text.find(old_start)
if start_idx < 0:
    print("[patch] model_rejected_all block not found")
    raise SystemExit(0)

# Find the end of the block - look for the close paren after the end_marker_line
end_marker_idx = text.find(end_marker_line, start_idx)
if end_marker_idx < 0:
    print("[patch] end of model_rejected_all block not found")
    raise SystemExit(0)

# Find the closing paren after the end_marker_line
close_paren_idx = text.find(close_paren_line, end_marker_idx)
if close_paren_idx < 0:
    print("[patch] closing paren of model_rejected_all block not found")
    raise SystemExit(0)

end_idx = close_paren_idx + len(close_paren_line)

new_code = """    if model_rejected_all:
        logger.warning(
            "Stage 5: model rejected all %d candidates - falling back to keyword shortlist",
            len(filtered_rows),
        )
        shortlist = [row for row in filtered_rows if isinstance(row, dict)][:15]
        if not shortlist:
            logger.warning("Keyword fallback also empty - continuing with empty shortlist")
            shortlist = []
        (stage_dir / "screen_meta.json").write_text(
            json.dumps(
                {
                    "outcome": "model_rejected_all_fallback_keyword",
                    "candidates_screened": len(filtered_rows),
                    "shortlist_size": len(shortlist),
                    "note": "Model rejected all; fell back to keyword-based shortlist.",
                },
                indent=2,
            ),
            encoding="utf-8",
        )"""

text = text[:start_idx] + new_code + text[end_idx:]
lit_path.write_text(text, encoding="utf-8")
print("[patch] literature screen patched: model_rejected_all -> keyword fallback")
