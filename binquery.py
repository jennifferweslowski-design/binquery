#!/usr/bin/env python3
"""binquery v0 — local CLIP shortlist CLI. Not a pass."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))

from cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
