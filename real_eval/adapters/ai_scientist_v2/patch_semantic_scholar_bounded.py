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


# 2. Both ``requests.get(...)`` calls to the S2 API carry no ``timeout``: a
#    connection that is accepted but never answered blocks the ideation process
#    forever (run fullrun_tdc_02_luna_20260918_070527 sat in a single S2 read
#    from 07:06 with an ESTABLISHED socket and no further log line; the retry
#    bound cannot help because the first attempt never returns). Add a socket
#    timeout so the bounded retry/give-up path is actually reachable.
S2_REQUEST_TIMEOUT_SECONDS = 30
OLD_GET = 'requests.get(\n        "https://api.semanticscholar.org/graph/v1/paper/search",\n'
NEW_GET = (
    'requests.get(\n        "https://api.semanticscholar.org/graph/v1/paper/search",\n'
    f"        timeout={S2_REQUEST_TIMEOUT_SECONDS},\n"
)
OLD_GET_METHOD = OLD_GET.replace("\n        ", "\n            ")
NEW_GET_METHOD = NEW_GET.replace("\n        ", "\n            ")


def _apply_request_timeout(text: str) -> str:
    if f"timeout={S2_REQUEST_TIMEOUT_SECONDS}," in text:
        print("semantic scholar request-timeout patch already applied")
        return text
    n = text.count(OLD_GET) + text.count(OLD_GET_METHOD)
    if n != 2:
        raise SystemExit(f"expected 2 semantic scholar requests.get anchors, found {n}")
    text = text.replace(OLD_GET_METHOD, NEW_GET_METHOD).replace(OLD_GET, NEW_GET)
    print("semantic scholar request-timeout patch applied")
    return text


def main() -> None:
    text = TARGET.read_text(encoding="utf-8")
    if "max_tries=3" in text and "continuing without papers" in text:
        print("semantic scholar bounded-retry patch already applied")
    else:
        if OLD_DECORATOR not in text or OLD_USE_TOOL not in text:
            raise SystemExit(
                "semantic_scholar.py anchors not found; upstream layout changed, refusing to patch"
            )
        text = text.replace(OLD_DECORATOR, NEW_DECORATOR, 1)
        text = text.replace(OLD_USE_TOOL, NEW_USE_TOOL, 1)
        print("semantic scholar bounded-retry patch applied")
    text = _apply_request_timeout(text)
    TARGET.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
