"""GRIP Figure: per-question adjusted accuracy, ten frontier models.

Slope chart. Colour encodes the direction of the Q4 -> Q5 step, which is the
finding: the three models that improve there are the three strongest overall.
Identity is carried by direct labels, never by colour alone.

Palette: slots 1 and 2 of the validated categorical set.
  node scripts/validate_palette.js "#2a78d6,#eb6834" --mode light  -> ALL PASS

Outputs figures/GRIP_levels.pdf (vector, for LaTeX) and .png (for preview).
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# adjusted score (accuracy above the constant-answer baseline), typed comparator
DATA = [
    ("Gemini 3.8 Flash",     [.763, .494, .539, .341, .404]),
    ("Claude Opus 5",        [.714, .514, .491, .287, .374]),
    ("Grok 4.6",             [.520, .426, .371, .165, .203]),
    ("Claude Sonnet 5",      [.543, .397, .346, .146, .044]),
    ("GPT-5.6 Sol",          [.573, .326, .342, .133, .015]),
    ("Muse Glimmer 30B",     [.587, .135, .116, .021, -.218]),
    ("GPT-5.6 Luna",         [.489, .027, .188, .017, -.204]),
    ("DeepSeek V4.1 Flash",  [.531, -.006, .191, -.054, -.243]),
    ("Perplexity Sonar Pro", [.486, .017, .138, -.142, -.216]),
    ("Inkling",              [.390, .049, .106, -.019, -.297]),
]

UP, DOWN = "#2a78d6", "#eb6834"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#d8d8d4"

def declutter(ys, gap):
    """Push labels apart while preserving order."""
    order = sorted(range(len(ys)), key=lambda i: ys[i])
    out = list(ys)
    for k in range(1, len(order)):
        a, b = order[k - 1], order[k]
        if out[b] - out[a] < gap:
            out[b] = out[a] + gap
    return out

fig, ax = plt.subplots(figsize=(5.4, 3.5))
fig.patch.set_facecolor("white"); ax.set_facecolor("white")
x = [1, 2, 3, 4, 5]

rows = [(n, v, UP if v[4] > v[3] else DOWN) for n, v in DATA]
lab_y = declutter([v[4] for _, v, _ in rows], 0.052)

for (name, v, colour), y in zip(rows, lab_y):
    ax.plot(x, v, color=colour, lw=1.4, zorder=3,
            solid_capstyle="round", alpha=0.95)
    ax.plot(x, v, "o", color=colour, ms=3.4, zorder=4,
            markeredgecolor="white", markeredgewidth=0.7)
    ax.plot([5, 5.13], [v[4], y], color=colour, lw=0.5, alpha=0.5, zorder=2)
    ax.text(5.18, y, name, color=INK, fontsize=6.2, va="center", ha="left")

ax.axhline(0, color=MUTED, lw=0.8, ls=(0, (4, 3)), zorder=1)
ax.text(0.92, -0.018, "constant answering", fontsize=6.0, color=MUTED,
        ha="left", va="top")

ax.set_xlim(0.88, 7.25); ax.set_ylim(-0.36, 0.83)
ax.set_xticks(x)
ax.set_xticklabels(["Q1", "Q2", "Q3", "Q4", "Q5"], fontsize=7.6, color=INK)
ax.set_yticks([-0.2, 0, 0.2, 0.4, 0.6, 0.8])
ax.tick_params(axis="y", labelsize=7.0, colors=MUTED, length=0)
ax.tick_params(axis="x", length=0)
ax.set_ylabel("accuracy above baseline", fontsize=7.4, color=MUTED, labelpad=4)
ax.set_xlabel("question position", fontsize=7.4, color=MUTED, labelpad=3)
ax.grid(axis="y", color=GRID, lw=0.5, zorder=0)
ax.set_axisbelow(True)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.spines["bottom"].set_color(GRID); ax.spines["bottom"].set_linewidth(0.6)

ax.legend(handles=[Line2D([], [], color=UP, lw=1.6,
                          label="improves at Q5 (3 models)"),
                   Line2D([], [], color=DOWN, lw=1.6,
                          label="declines at Q5 (7 models)")],
          loc="upper right", bbox_to_anchor=(1.0, 1.04), frameon=False,
          fontsize=6.4, handlelength=1.5, labelcolor=INK, borderpad=0.2)

fig.tight_layout(pad=0.4)
fig.savefig("figures/GRIP_levels.pdf", bbox_inches="tight")
fig.savefig("figures/GRIP_levels.png", dpi=220, bbox_inches="tight")
print("Q4->Q5 improves:", [n for n, v, c in rows if c == UP])
print("wrote figures/GRIP_levels.pdf and .png")
