"""Build a grouped bar chart of Test-1 typed accuracy by reasoning family."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, to_hex
import numpy as np
import pandas as pd


# Change this one line if the typed-comparator aggregate file moves.
DATA_PATH = Path("analysis/typed_comparator/aggregates.csv")
OUTPUT_PDF = Path("figures/GRIP_test1_family_bars.pdf")
OUTPUT_PNG = Path("figures/GRIP_test1_family_bars.png")

FAMILY_NAMES = {
    "Plane Geometry": "Plane",
    "Solid Geometry": "Solid",
    "Transformational": "Transformational",
    "Physical & Mechanical": "Physical",
    "Topological": "Topological",
    "Projective": "Projective",
    "Analytic": "Analytic",
    "Optical": "Optical",
    "Inductive": "Inductive",
}

DOMAIN_COUNTS = {
    "Physical": 7,
    "Solid": 6,
    "Transformational": 6,
    "Plane": 5,
    "Topological": 3,
    "Analytic": 2,
    "Projective": 2,
    "Optical": 2,
    "Inductive": 1,
}

DISPLAY_NAMES = {
    "gemini_3_8_flash": "Gemini 3.8 Flash",
    "claude_opus_5": "Claude Opus 5",
    "grok_4_6": "Grok 4.6",
    "gpt_5_6_sol": "GPT-5.6 Sol",
    "claude_sonnet_5": "Claude Sonnet 5",
    "muse_glimmer_30b": "Muse Glimmer 30B",
    "deepseek_v4_1_flash": "DeepSeek V4.1 Flash",
    "gpt_5_6_luna": "GPT-5.6 Luna",
    "perplexity_sonar_pro": "Perplexity Sonar Pro",
    "inking": "Inkling",
}


def load_verified_data() -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    frame = pd.read_csv(DATA_PATH)
    family = frame.loc[
        frame["scope"].eq("family")
        & frame["method"].eq("POOLED")
        & frame["include_small_n"].eq(True)
    ].copy()
    family["plot_family"] = family["family"].map(FAMILY_NAMES)
    matrix = (
        family.pivot(
            index="model",
            columns="plot_family",
            values="raw_accuracy_all_cells_typed",
        )
        .mul(100)
        .loc[list(DISPLAY_NAMES)]
    )
    if matrix.shape != (10, 9) or matrix.isna().any().any():
        raise ValueError(f"Expected a complete 10 x 9 matrix, found {matrix.shape}")

    overall = (
        frame.loc[
            frame["scope"].eq("overall")
            & frame["method"].eq("POOLED")
            & frame["include_small_n"].eq(True)
        ]
        .drop_duplicates("model")
        .set_index("model")["raw_accuracy_all_cells_typed"]
        .mul(100)
        .loc[matrix.index]
    )
    weights = pd.Series(DOMAIN_COUNTS, dtype=float)
    weighted = matrix.mul(weights, axis=1).sum(axis=1) / weights.sum()
    verification = pd.DataFrame({
        "weighted_mean": weighted,
        "reported_overall": overall,
        "difference": weighted - overall,
    })
    if verification["difference"].abs().max() > 0.1:
        print("Verification failed; no chart was produced.")
        print(verification.to_string(float_format=lambda value: f"{value:.4f}"))
        raise SystemExit(2)

    ranking = overall.sort_values(ascending=False).index
    return matrix.loc[ranking], overall.loc[ranking], verification.loc[ranking]


def main() -> None:
    matrix, overall, verification = load_verified_data()
    family_order = matrix.mean(axis=0).sort_values(ascending=False).index.tolist()
    matrix = matrix[family_order]

    ramp = LinearSegmentedColormap.from_list("grip_burgundy", ["#f4c7c3", "#67000d"])
    colors = [to_hex(ramp(value)) for value in np.linspace(1.0, 0.08, len(matrix))]

    print(f"Source: {DATA_PATH}")
    print("Verification (percentage points):")
    check = verification.copy()
    check.index = [DISPLAY_NAMES[model] for model in check.index]
    print(check.to_string(float_format=lambda value: f"{value:.4f}"))
    print("\n10 x 9 plotted matrix (raw typed accuracy, %):")
    printable = matrix.copy()
    printable.index = [DISPLAY_NAMES[model] for model in printable.index]
    print(printable.to_string(float_format=lambda value: f"{value:.2f}"))

    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })
    fig, ax = plt.subplots(figsize=(7.2, 4.7), facecolor="white")
    fig.subplots_adjust(left=0.085, right=0.985, top=0.78, bottom=0.18)
    ax.set_facecolor("white")

    centers = np.arange(len(family_order), dtype=float)
    group_width = 0.82
    bar_width = group_width / len(matrix)
    start = -(group_width / 2) + bar_width / 2

    for index, ((model, row), color) in enumerate(zip(matrix.iterrows(), colors)):
        positions = centers + start + index * bar_width
        ax.bar(
            positions,
            row.to_numpy(float),
            width=bar_width * 0.92,
            color=color,
            edgecolor="#252525",
            linewidth=0.38,
            label=f"{DISPLAY_NAMES[model]} ({overall[model]:.1f})",
            zorder=3,
        )

    ax.set_xlim(-0.55, len(family_order) - 0.45)
    ax.set_ylim(0, 90)
    ax.set_ylabel("Raw Test-1 accuracy (%)", fontsize=8.5)
    ax.set_xticks(centers)
    ax.set_xticklabels(family_order, rotation=28, ha="right", fontsize=7.2)
    ax.tick_params(axis="y", labelsize=7.2, width=0.6)
    ax.tick_params(axis="x", width=0.6)
    ax.yaxis.grid(True, color="#c9c9c9", linewidth=0.55, alpha=0.85, zorder=0)
    ax.xaxis.grid(False)
    for spine in ax.spines.values():
        spine.set_color("#303030")
        spine.set_linewidth(0.75)

    ax.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, 1.025),
        ncol=5,
        frameon=False,
        fontsize=6.35,
        handlelength=1.45,
        handletextpad=0.42,
        columnspacing=0.9,
        labelspacing=0.45,
    )

    OUTPUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_PDF, facecolor="white")
    fig.savefig(OUTPUT_PNG, dpi=260, facecolor="white")
    plt.close(fig)

    print("\nRanked colours (best to worst):")
    for model, color in zip(matrix.index, colors):
        print(f"{DISPLAY_NAMES[model]}: {color}")
    print(f"\nWritten: {OUTPUT_PDF}")
    print(f"Written: {OUTPUT_PNG}")
    print("Network calls: 0")


if __name__ == "__main__":
    main()
