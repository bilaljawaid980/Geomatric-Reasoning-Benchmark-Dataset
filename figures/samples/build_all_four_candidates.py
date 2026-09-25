"""Collect images evaluated by all ten hosted models in all four GRIP tests."""

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
MODELS = {
    "claude_opus_5",
    "claude_sonnet_5",
    "deepseek_v4_1_flash",
    "gemini_3_8_flash",
    "gpt_5_6_luna",
    "gpt_5_6_sol",
    "grok_4_6",
    "inking",
    "muse_glimmer_30b",
    "perplexity_sonar_pro",
}


def stems_seen_by_all(frame: pd.DataFrame) -> set[str]:
    frame = frame[frame["model"].isin(MODELS)]
    counts = frame.groupby("stem")["model"].nunique()
    return set(counts[counts == len(MODELS)].index)


def main() -> None:
    t1 = pd.read_csv(
        ROOT / "analysis/typed_comparator/test1_row_scores.csv",
        usecols=["model", "domain", "stem", "image_path"],
    )
    t2_paths = [
        ROOT / "tests/test_2_grain_robustness/analysis/per_question.csv",
        ROOT / "tests/test_2_grain_robustness/analysis/gpt_5_6_sol/per_question.csv",
        ROOT / "tests/test_2_grain_robustness/analysis/deepseek_v4_1_flash/per_question.csv",
        ROOT / "tests/test_2_grain_robustness/analysis/perplexity_sonar_pro/per_question.csv",
    ]
    t2 = pd.concat(
        [pd.read_csv(path, usecols=["model", "domain", "stem", "image_path"]) for path in t2_paths],
        ignore_index=True,
    )
    t3 = pd.read_csv(
        ROOT / "analysis/typed_comparator/test3_row_scores.csv",
        usecols=["model", "domain", "stem"],
    )
    t4_paths = [
        ROOT / "tests/test_4_crossexam/plan/crossexam_manifest.csv",
        ROOT / "tests/test_4_crossexam/plan/gpt_5_6_sol/crossexam_manifest_with_gpt_5_6_sol.csv",
        ROOT / "tests/test_4_crossexam/plan/deepseek_v4_1_flash/crossexam_manifest.csv",
        ROOT / "tests/test_4_crossexam/plan/perplexity_sonar_pro/crossexam_manifest.csv",
    ]
    t4 = pd.concat(
        [pd.read_csv(path, usecols=["model", "domain", "stem", "image_path"]) for path in t4_paths],
        ignore_index=True,
    )

    eligible = {
        "test1": stems_seen_by_all(t1),
        "test2": stems_seen_by_all(t2),
        "test3": stems_seen_by_all(t3),
        "test4": stems_seen_by_all(t4),
    }
    common = set.intersection(*eligible.values())
    metadata = (
        t4[t4["stem"].isin(common)][["domain", "stem", "image_path"]]
        .drop_duplicates("stem")
        .sort_values(["domain", "stem"])
    )

    print("Images used by all ten hosted models:")
    for test, stems in eligible.items():
        print(f"  {test}: {len(stems):,}")
    print(f"All-four intersection: {len(common):,}")
    print(metadata.to_string(index=False))


if __name__ == "__main__":
    main()
