"""Rebuild the standard private and public flat files from annotations.jsonl."""
import runpy
from pathlib import Path
if __name__ == "__main__":
    script = Path(__file__).resolve().parents[1] / "standardize_dataset_outputs.py"
    runpy.run_path(str(script), run_name="__main__")
