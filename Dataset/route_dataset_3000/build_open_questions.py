"""Compatibility entry point for the suite-wide open-question builder."""
from pathlib import Path
import sys
DATASET_ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(DATASET_ROOT))
from build_remaining_open_questions import build_domain  # noqa: E402
if __name__=="__main__":
    count,fields=build_domain(Path(__file__).resolve().parent)
    print(f"route_dataset_3000: {count} rows; {len(fields)} sub-facts")
