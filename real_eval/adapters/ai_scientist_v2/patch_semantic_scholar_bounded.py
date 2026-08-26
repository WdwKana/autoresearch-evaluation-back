#!/usr/bin/env python3
"""Bound Semantic Scholar retries so ideation degrades instead of hanging.

02-scoped runtime patch (applied inside the run workspace copy by topic
wrappers; upstream checkout untouched). Upstream
``ai_scientist/tools/semantic_scholar.py`` decorates ``search_for_papers``
with ``backoff.expo`` and NO ``max_tries``/``max_time``: without an
``S2_API_KEY`` a 429 storm makes the call sleep forever (observed 949-second
backoffs, run fullrun_arc_02_20260826_062148), eating the whole ideation
budget until the wrapper timeout kills the run.

Two anchored replacements:
1. bound the backoff (max_tries=3, max_time=60s), after which the exception
   propagates instead of sleeping;
2. catch that failure at the tool boundary (``use_tool``) and fall through to
   the tool's native "No papers found." response, logging the degradation so
   the run evidence records that ideation proceeded without literature.

With a valid S2 key the first request succeeds and this patch is inert.
Fail-loud if the upstream anchors are missing; idempotent on reapplication.
"""
from pathlib import Path

TARGET = Path("ai_scientist/tools/semantic_scholar.py")

OLD_DECORATOR = """    @backoff.on_exception(
        backoff.expo,
        (requests.exceptions.HTTPError, requests.exceptions.ConnectionError),
        on_backoff=on_backoff,
    )
    def search_for_papers(self, query: str) -> Optional[List[Dict]]:"""

NEW_DECORATOR = """    @backoff.on_exception(
        backoff.expo,
        (requests.exceptions.HTTPError, requests.exceptions.ConnectionError),
        on_backoff=on_backoff,
        max_tries=3,
        max_time=60,
    )
    def search_for_papers(self, query: str) -> Optional[List[Dict]]:"""

OLD_USE_TOOL = """    def use_tool(self, query: str) -> Optional[str]:
        papers = self.search_for_papers(query)"""

NEW_USE_TOOL = """    def use_tool(self, query: str) -> Optional[str]:
        try:
            papers = self.search_for_papers(query)
        except Exception:
            print("[arc-wrapper] semantic scholar unavailable; continuing without papers")
            papers = None"""


def main() -> None:
    text = TARGET.read_text(encoding="utf-8")
    if "max_tries=3" in text and "continuing without papers" in text:
        print("semantic scholar bounded-retry patch already applied")
        return
    if OLD_DECORATOR not in text or OLD_USE_TOOL not in text:
        raise SystemExit(
            "semantic_scholar.py anchors not found; upstream layout changed, refusing to patch"
        )
    text = text.replace(OLD_DECORATOR, NEW_DECORATOR, 1)
    text = text.replace(OLD_USE_TOOL, NEW_USE_TOOL, 1)
    TARGET.write_text(text, encoding="utf-8")
    print("semantic scholar bounded-retry patch applied")


if __name__ == "__main__":
    main()
