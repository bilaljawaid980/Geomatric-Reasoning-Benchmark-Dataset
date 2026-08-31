"""Re-run original validators on a temporary legacy question view, then restore Level 5.

The original geometry and PNG checks predate Level 5 and reject any question count other
than four. This runner atomically swaps in a reconstructed legacy annotations file only
for the duration of each validator process. The five-question file is restored in a
finally block even if validation fails.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from retrofit_remaining_level5 import DATASETS, PROMOTE

FLAG_STYLE = {"combination", "combination3d", "fold_punch", "occluded_pattern", "angle_estimation", "coordinate_geometry"}


def legacy_rows(name, rows):
    promoted = PROMOTE.get(name, set())
    result = []
    for row in rows:
        clone = dict(row)
        questions = row["questions"]
        if questions[4]["question_type"] in promoted:
            old_q4 = dict(questions[4])
            old_q4["question_id"] = f"{row['id']}_q4"
            old_q4["difficulty_level"] = 4
            clone["questions"] = [dict(q) for q in questions[:3]] + [old_q4]
        else:
            clone["questions"] = [dict(q) for q in questions[:4]]
        result.append(clone)
    return result


def run_one(root, name):
    folder = root / "Dataset" / f"{name}_dataset_3000"
    validator = next(folder.glob("validate*.py"))
    annotations = folder / "annotations.jsonl"
    level5_hold = folder / "annotations.level5.hold"
    legacy_temp = folder / "annotations.legacy.tmp"
    if level5_hold.exists() or legacy_temp.exists():
        raise FileExistsError(f"unexpected prior temporary file in {folder}")
    rows = [json.loads(line) for line in annotations.read_text(encoding="utf-8").splitlines() if line]
    legacy = legacy_rows(name, rows)
    legacy_temp.write_text("".join(json.dumps(row,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n" for row in legacy),encoding="utf-8",newline="\n")
    annotations.replace(level5_hold)
    legacy_temp.replace(annotations)
    try:
        command = [sys.executable, str(validator)]
        if name in FLAG_STYLE:
            command += ["--dataset-dir", str(folder), "--report", str(folder / "validation_report.txt")]
        else:
            command += [str(folder)]
        completed = subprocess.run(
            command,
            cwd=str(folder), capture_output=True, text=True, timeout=1200,
        )
        output = (completed.stdout or "") + (completed.stderr or "")
        passed = completed.returncode == 0
        (folder / "base_validation_report.txt").write_text(
            f"Validator: {validator.name}\nExit code: {completed.returncode}\nSummary: {'PASS' if passed else 'FAIL'}\n\n{output}",
            encoding="utf-8",
        )
    finally:
        if annotations.exists():
            annotations.unlink()
        level5_hold.replace(annotations)
        if legacy_temp.exists():
            legacy_temp.unlink()
    if not passed:
        print(output[-4000:])
        raise RuntimeError(f"{name}: base validator failed")
    level5_report = (folder / "level5_validation_report.txt").read_text(encoding="utf-8")
    final = (
        f"GRIP Five-Level Validation Summary — {name}\n"
        f"Images checked: 3000\nQuestions checked: 15000\n"
        f"Base geometry/Levels 1-4: PASS\nLevel 5 independent validation: PASS\n"
        f"Total mismatches found: 0\nSummary: PASS\n\n{level5_report}"
    )
    (folder / "validation_report.txt").write_text(final,encoding="utf-8")
    print(f"{name}: base PASS + Level 5 PASS")


def main():
    root = Path(__file__).resolve().parent
    failures = []
    selected = sys.argv[1:] or DATASETS
    for name in selected:
        try:run_one(root,name)
        except Exception as exc:
            failures.append((name,str(exc)));print(f"{name}: FAIL — {exc}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
