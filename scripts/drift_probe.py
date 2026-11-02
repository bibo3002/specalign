#!/usr/bin/env python3
"""Compatibility wrapper: `drift_probe.py <repo> [drift] [F-ids...] [--json]` → `specalign drift`.

The probe now lives in tools/specalign/drift.py (brace/glob Sources, `<tag>..HEAD` range, dead-source report).
Exit codes: 0 no drift · 1 drift · 2 hard error · 3 unverifiable with --strict.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from specalign.cli import main  # noqa: E402


def translate(argv: list[str]) -> list[str]:
    # The old CLI took an optional literal `drift` after the repo path; the new one has no such word.
    if len(argv) >= 2 and argv[1] == "drift":
        argv = [argv[0], *argv[2:]]
    return ["drift", *argv]


if __name__ == "__main__":
    sys.exit(main(translate(sys.argv[1:])))
