#!/usr/bin/env python3
"""Compatibility wrapper: `rescan_check.py <repo> [--spec-dir P] [--json]` → `specalign registry check`.

The checks now live in tools/specalign/registry.py (exact tag per version, §0 Card ↔ INDEX equality,
real §0 id check, UTF-8). Exit codes: 0 ok · 1 findings · 2 hard error.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from specalign.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(["registry", "check", *sys.argv[1:]]))
