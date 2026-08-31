"""Rebuild the 22-dataset, five-level spot-check bundle without reshuffling images."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from rebuild_spot_check_level5 import main


if __name__ == "__main__":
    main()
