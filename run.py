"""Convenience root launcher for BeamNG Mod Fixer."""
import sys
from pathlib import Path

# Ensure src/ is on sys.path
src_path = Path(__file__).resolve().parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from beamng_mod_fixer.cli import main

if __name__ == "__main__":
    sys.exit(main())
