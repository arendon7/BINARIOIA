from __future__ import annotations

"""Compatibility entrypoint for older R26 installers.

R27 has exactly one user-facing shell: hub.server. This module intentionally
no longer creates a second portal.
"""

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["BINARIO_IA_ROOT"] = str(root)
    env["BINARIO_FULL_ROOT"] = str(root)
    env["PYTHONPATH"] = str(root) + os.pathsep + str(root / "r26") + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    return subprocess.call([sys.executable, "-m", "hub.server", *sys.argv[1:]], cwd=str(root), env=env)


if __name__ == "__main__":
    raise SystemExit(main())
