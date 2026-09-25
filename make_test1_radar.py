"""Build Test-1 typed-accuracy radar charts from frozen aggregate outputs."""

from __future__ import annotations

from pathlib import Path
import math

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, to_hex
import numpy as np
import pandas as pd


# Change this one line if the typed-comparator aggregate file moves.
DATA_PATH = Path("analysis/typed_comparator/aggregates.csv")
OUTPUT_DIR = Path("figures")

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


def load_data() -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    frame = pd.read_csv(DATA_PATH)
    selector = (
        frame["scope"].eq("family")
        & frame["method"].eq("POOLED")
        & frame["include_small_n"].eq(True)
    )
    family = frame.loc[selector].copy()
    family["family_plot"] = family["family"].map(FAMILY_NAMES)
    if family["family_plot"].isna().any():
        unknown = sorted(family.loc[family["family_plot"].isna(), "family"].unique())
        raise ValueError(f"Unmapped family names: {unknown}")

    matrix = (
        family.pivot(index="model", columns="family_plot", values="raw_accuracy_all_cells_typed")
        .mul(100)
        .loc[list(DISPLAY_NAMES)]
    )
    if matrix.shape != (10, 9) or matrix.isna().any().any():
        raise ValueError(f"Expected a complete 10 x 9 matrix, found {matrix.shape}")

    overall_selector = (
        frame["scope"].eq("overall")
        & frame["method"].eq("POOLED")
        & frame["include_small_n"].eq(True)
    )
    overall = (
        frame.loc[overall_selector]
        .drop_duplicates("model")
        .set_index("model")["raw_accuracy_all_cells_typed"]
        .mul(100)
        .loc[matrix.index]
    )

    weights = pd.Series(DOMAIN_COUNTS, dtype=float)
    weighted = matrix.mul(weights, axis=1).sum(axis=1) / weights.sum()
    verification = pd.DataFrame(
        {
            "weighted_mean": weighted,
            "reported_overall": overall,
            "difference": weighted - overall,
        }
    )
    if verification["difference"].abs().max() > 0.1:
        print("Verification failed; no chart was produced.")
        print(verification.to_string(float_format=lambda value: f"{value:.4f}"))
        raise SystemExit(2)

    order = overall.sort_values(ascending=False).index
    return matrix.loc[order], overall.loc[order], verification.loc[order]


def ranked_colors(count: int) -> list[str]:
    # One-hue burgundy ramp. The highest-ranked model receives the darkest shade.
    ramp = LinearSegmentedColormap.from_list("grip_burgundy", ["#f4c7c3", "#67000d"])
    return [to_hex(ramp(value)) for value in np.linspace(1.0, 0.08, count)]


def draw_radar(
    matrix: pd.DataFrame,
    overall: pd.Series,
    family_order: list[str],
    output_stem: str,
    width: float,
    height: float,
    half_width: bool,
    radial_min: float,
    radial_max: float,
) -> None:
    values = matrix[family_order]
    count = len(family_order)
    angles = np.linspace(0, 2 * np.pi, count, endpoint=False)
    closed_angles = np.r_[angles, angles[0]]
    colors = ranked_colors(len(values))

    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })
    fig = plt.figure(figsize=(width, height), facecolor="white")
    if half_width:
        # A genuinely separate half-width layout: a 1.43-inch radar leaves
        # enough horizontal room for the outside labels at the native width.
        ax = fig.add_axes([0.22, 0.38, 0.56, 0.44], projection="polar")
        family_font, radial_font, legend_font = 5.0, 5.0, 5.0
    else:
        ax = fig.add_axes([0.10, 0.16, 0.50, 0.684], projection="polar")
        family_font, radial_font, legend_font = 7.4, 6.4, 6.0

    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_ylim(radial_min, radial_max)
    ax.set_xticks(angles)
    ax.set_xticklabels([])

    step = 10
    tick_start = math.ceil(radial_min / step) * step
    radial_ticks = np.arange(tick_start, radial_max + 0.1, step)
    ax.set_yticks(radial_ticks)
    ax.set_yticklabels([f"{int(t)}" for t in radial_ticks], fontsize=radial_font, color="#555555")
    # Halfway between the first and second spokes.
    ax.set_rlabel_position(np.degrees((angles[0] + angles[1]) / 2))
    ax.grid(color="#c7c7c7", linewidth=0.55, alpha=0.85)
    ax.spines["polar"].set_color("#333333")
    ax.spines["polar"].set_linewidth(0.8)
    ax.set_facecolor("white")

    label_radius = radial_max + (radial_max - radial_min) * (0.13 if half_width else 0.10)
    for angle, label in zip(angles, family_order):
        # With theta zero at north and clockwise rotation, screen-space x/y are
        # sin(theta)/cos(theta), not the default polar cos(theta)/sin(theta).
        screen_x = np.sin(angle)
        screen_y = np.cos(angle)
        if screen_x > 0.20:
            horizontal = "left"
        elif screen_x < -0.20:
            horizontal = "right"
        else:
            horizontal = "center"
        vertical = "bottom" if screen_y > 0.35 else "top" if screen_y < -0.35 else "center"
        ax.text(
            angle,
            label_radius,
            label,
            ha=horizontal,
            va=vertical,
            fontsize=family_font,
            color="#222222",
            clip_on=False,
        )

    handles = []
    for (model, row), color in zip(values.iterrows(), colors):
        closed_values = np.r_[row.to_numpy(float), row.iloc[0]]
        line, = ax.plot(closed_angles, closed_values, color=color, linewidth=1.45, alpha=0.96)
        ax.fill(closed_angles, closed_values, color=color, alpha=0.028)
        handles.append(line)

    labels = [f"{DISPLAY_NAMES[m]} ({overall[m]:.1f})" for m in values.index]
    if half_width:
        fig.legend(
            handles,
            labels,
            loc="lower center",
            bbox_to_anchor=(0.5, 0.015),
            ncol=2,
            frameon=False,
            fontsize=legend_font,
            handlelength=1.45,
            handletextpad=0.45,
            columnspacing=0.75,
            labelspacing=0.35,
        )
    else:
        fig.legend(
            handles,
            labels,
            loc="center left",
            bbox_to_anchor=(0.68, 0.5),
            frameon=False,
            fontsize=legend_font,
            handlelength=1.7,
            handletextpad=0.55,
            labelspacing=0.55,
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_DIR / f"{output_stem}.pdf", facecolor="white")
    fig.savefig(OUTPUT_DIR / f"{output_stem}.png", dpi=260, facecolor="white")
    plt.close(fig)


def main() -> None:
    matrix, overall, verification = load_data()
    fleet_means = matrix.mean(axis=0).sort_values(ascending=False)
    family_order = fleet_means.index.tolist()

    smallest = float(matrix.min().min())
    largest = float(matrix.max().max())
    radial_min = max(0.0, 5.0 * math.floor((smallest - 3.0) / 5.0))
    radial_max = min(100.0, 5.0 * math.ceil((largest + 3.0) / 5.0))
    colors = ranked_colors(len(matrix))

    print(f"Source: {DATA_PATH}")
    print("Comparator: frozen typed comparator described in analysis/typed_comparator/COMPARATOR_SPEC.md")
    print("\nVerification (percentage points):")
    printable_verification = verification.copy()
    printable_verification.index = [DISPLAY_NAMES[m] for m in printable_verification.index]
    print(printable_verification.to_string(float_format=lambda value: f"{value:.4f}"))

    print("\n10 x 9 plot matrix (raw typed accuracy, %):")
    printable_matrix = matrix[family_order].copy()
    printable_matrix.index = [DISPLAY_NAMES[m] for m in printable_matrix.index]
    print(printable_matrix.to_string(float_format=lambda value: f"{value:.2f}"))

    print("\nSpoke order (fleet mean, strongest first):")
    print(", ".join(f"{family} ({fleet_means[family]:.2f})" for family in family_order))
    print("\nRanked colours (best to worst):")
    for model, color in zip(matrix.index, colors):
        print(f"{DISPLAY_NAMES[model]}: {color}")
    print(f"\nRadial limits: {radial_min:.0f}% to {radial_max:.0f}%")

    draw_radar(
        matrix, overall, family_order,
        "GRIP_test1_radar_full", 5.2, 3.8, False, radial_min, radial_max,
    )
    draw_radar(
        matrix, overall, family_order,
        "GRIP_test1_radar_half", 2.55, 3.25, True, radial_min, radial_max,
    )
    print("\nFiles written:")
    for suffix in ("full.pdf", "full.png", "half.pdf", "half.png"):
        print(OUTPUT_DIR / f"GRIP_test1_radar_{suffix}")
    print("Network calls: 0")


if __name__ == "__main__":
    main()
