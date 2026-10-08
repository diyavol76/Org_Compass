#!/usr/bin/env python3
"""Copy this skill's OpenCode agents and commands into a project's .opencode/ directory.
Usage: install_opencode.py <project-root> [--force]
"""
import shutil
import sys
from pathlib import Path

src = Path(__file__).resolve().parent.parent / "assets" / "opencode"
if len(sys.argv) < 2:
    sys.exit(__doc__)
dst = Path(sys.argv[1]) / ".opencode"
force = "--force" in sys.argv
for sub in ("agents", "commands"):
    (dst / sub).mkdir(parents=True, exist_ok=True)
    for f in sorted((src / sub).glob("*.md")):
        t = dst / sub / f.name
        if t.exists() and not force:
            print(f"skip (exists) {t}")
            continue
        shutil.copy2(f, t)
        print(f"installed {t}")
