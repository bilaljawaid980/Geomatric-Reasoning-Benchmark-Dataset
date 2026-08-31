import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));from flatten_nested_polygon_annotations import flatten
if __name__=="__main__":flatten(Path(__file__).resolve().parent/"annotations.jsonl")
