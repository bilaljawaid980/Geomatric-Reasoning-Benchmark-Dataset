"""Capture protected-content hashes before the remaining open-question release."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXCLUDED = {"route_dataset_3000", "hex_pathfinding_dataset_3000"}
PROTECTED = ("question_set.csv", "answer_key.csv", "dataset_final.csv", "dataset_final.jsonl")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    output = {}
    for folder in sorted(ROOT.glob("*_dataset_*")):
        if folder.name in EXCLUDED or not (folder / "build_manifest.json").is_file():
            continue
        output[folder.name] = {
            name: sha256(folder / name) for name in PROTECTED if (folder / name).is_file()
        }
        relative_images = (Path("Dataset") / folder.name / "images").as_posix()
        tracked = subprocess.check_output(
            ["git", "ls-files", "-s", "--", relative_images], cwd=ROOT.parent, text=True
        )
        output[folder.name]["image_count"] = len(tracked.splitlines())
        output[folder.name]["images_git_index_sha256"] = hashlib.sha256(tracked.encode()).hexdigest()
    (ROOT / "remaining_open_prechange_hashes.json").write_text(
        json.dumps(output, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Captured {len(output)} datasets")


if __name__ == "__main__":
    main()
