"""Compatibility entry point for the suite-wide open-question validator."""
from pathlib import Path
import sys
DATASET_ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(DATASET_ROOT))
from validate_remaining_open_questions import validate  # noqa: E402
if __name__=="__main__":
    metrics=validate("hex_pathfinding_dataset_3000")
    print(metrics["status"])
    raise SystemExit(0 if metrics["status"]=="PASS" else 1)
