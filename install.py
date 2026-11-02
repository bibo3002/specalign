#!/usr/bin/env python3
"""Install or verify SpecAlign.  `python install.py --project D:\\myproject`  ·  `python install.py --check`."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "tools"))

from specalign.installer import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
