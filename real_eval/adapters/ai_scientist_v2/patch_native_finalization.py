#!/usr/bin/env python3
"""Wire the ARC contract finalization into the native finalization slot.

Inserts a call to arc_contract_finalization.finalize(idea_dir) into
launch_scientist_bfts.py exactly where the upstream writeup phase would run
(we pass --skip_writeup, leaving the native synthesis slot idle). ARC-wrapper
scoped; applied to the run-workspace copy only. Anchored-replace, fail-loud,
idempotent -- same conventions as the other 02 adapters.

Rationale and boundary framing: see arc_contract_finalization.py's docstring
(delivery belongs to the post-search finalization phase, not to judged
research nodes -- replay run 112156 evidence).
"""
from pathlib import Path

TARGET = Path("launch_scientist_bfts.py")
MARK = "arc-contract-finalization"

OLD = """    save_token_tracker(idea_dir)

    if not args.skip_writeup:"""
NEW = """    save_token_tracker(idea_dir)

    # arc-contract-finalization: the native finalization slot (where writeup
    # would run) packages the run's own selected results as the ARC contract
    # deliverables. In-run, framework-model-driven, journal-grounded.
    import importlib.util as _arc_ilu
    _arc_spec = _arc_ilu.spec_from_file_location(
        "arc_contract_finalization",
        "real_eval/adapters/ai_scientist_v2/arc_contract_finalization.py",
    )
    _arc_mod = _arc_ilu.module_from_spec(_arc_spec)
    _arc_spec.loader.exec_module(_arc_mod)
    _arc_mod.finalize(idea_dir)

    if not args.skip_writeup:"""


def main() -> None:
    text = TARGET.read_text(encoding="utf-8")
    if MARK in text:
        print("[native-finalization] already applied")
        return
    if OLD not in text:
        raise SystemExit("[native-finalization] anchor not found in launch_scientist_bfts.py")
    TARGET.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print("[native-finalization] applied: contract delivery wired into the writeup slot")


if __name__ == "__main__":
    main()
