"""Build separate and unified Markdown reports for closed-loop accuracy."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


TEST_ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = TEST_ROOT / "analysis"
DISPLAY = {
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
FAMILIES = {
    "Plane Geometry": ["nested_squares", "nested_triangles", "nested_hexagons", "line_intersection", "angle_estimation"],
    "Solid Geometry": ["cube_net", "cube_structure", "combination3d", "orthographic", "polyhedron", "depth_height"],
    "Transformational": ["rotation_matching", "symmetry_pattern", "fold_punch", "combination", "embedded_figures", "overlap_circles"],
    "Physical & Mechanical": ["physical_stability", "gear_train", "fbd", "projectile_motion", "laser_mirror", "clock_reading", "gauge_reading"],
    "Topological": ["surface_topology", "route", "hex_pathfinding"],
    "Projective": ["occluded_pattern", "shadow_inference"],
    "Analytic": ["coordinate_geometry", "compass_bearing"],
    "Optical": ["optical_illusion", "impossible_object"],
    "Inductive": ["rpm"],
}


def source(model: str, name: str) -> pd.DataFrame:
    preferred = [
        ANALYSIS / model / f"{name}.csv",
        ANALYSIS / "models" / model / f"{name}.csv",
        ANALYSIS / f"{name}.csv",
    ]
    candidates = preferred + [
        path for path in ANALYSIS.rglob(f"{name}.csv") if path not in preferred
    ]
    for path in candidates:
        if not path.is_file():
            continue
        frame = pd.read_csv(path)
        if "model" not in frame.columns:
            continue
        selected = frame.loc[frame["model"] == model].copy()
        if not selected.empty:
            return selected
    raise FileNotFoundError(f"No {name}.csv rows found for {model}")


def pct(value: object) -> str:
    return f"{100 * float(value):.2f}%"


def family_rows(per_domain: pd.DataFrame) -> list[tuple[str, int, int, float]]:
    rows = []
    for family, domains in FAMILIES.items():
        selected = per_domain.loc[per_domain["domain"].isin(domains)]
        total = int(selected["absolute_rows"].sum())
        correct = int(round((selected["absolute_accuracy"] * selected["absolute_rows"]).sum()))
        rows.append((family, total, correct, correct / total))
    return rows


def model_report(model: str) -> str:
    summary = source(model, "summary").iloc[0]
    levels = source(model, "per_level").sort_values("level")
    domains = source(model, "per_domain").sort_values("absolute_accuracy", ascending=False)
    lines = [
        f"# Test 1 Closed-Loop Accuracy: {DISPLAY[model]}", "",
        "## Overall result", "",
        "| Questions | Correct | Strict accuracy | Bootstrap 95% CI | Constant baseline |",
        "|---:|---:|---:|---:|---:|",
        f"| {int(summary['absolute_rows']):,} | "
        f"{int(round(summary['absolute_accuracy'] * summary['absolute_rows'])):,} | "
        f"**{pct(summary['absolute_accuracy'])}** | {pct(summary['absolute_accuracy_ci_low'])}-"
        f"{pct(summary['absolute_accuracy_ci_high'])} | {pct(summary['absolute_baseline'])} |",
        "", "## Accuracy by level", "",
        "| Level | Correct | Accuracy | Bootstrap 95% CI |", "|---:|---:|---:|---:|",
    ]
    for row in levels.itertuples(index=False):
        correct = int(round(row.absolute_accuracy * row.absolute_rows))
        lines.append(
            f"| L{int(row.level)} | {correct:,}/{int(row.absolute_rows):,} | "
            f"{pct(row.absolute_accuracy)} | {pct(row.absolute_accuracy_ci_low)}-"
            f"{pct(row.absolute_accuracy_ci_high)} |"
        )
    lines.extend(["", "## Accuracy by reasoning family", "", "| Family | Questions | Correct | Accuracy |", "|---|---:|---:|---:|"])
    for family, total, correct, accuracy in family_rows(domains):
        lines.append(f"| {family} | {total:,} | {correct:,} | {pct(accuracy)} |")
    lines.extend(["", "## Accuracy by domain", "", "| Rank | Domain | Correct | Accuracy |", "|---:|---|---:|---:|"])
    for rank, row in enumerate(domains.itertuples(index=False), 1):
        correct = int(round(row.absolute_accuracy * row.absolute_rows))
        lines.append(f"| {rank} | `{row.domain}` | {correct:,}/{int(row.absolute_rows):,} | {pct(row.absolute_accuracy)} |")
    lines.extend([
        "", "## Scoring audit", "",
        "Numeric answers use exact equality, categorical answers use normalized exact equality, and acceptance-set answers use exact membership. The previously approved wording pairs `smaller than`/`smaller` and `none`/`neither` are treated as equivalent. The reviewed wrong-answer set contained no further meaning-preserving equivalences, so no additional answers were promoted.", "",
    ])
    return "\n".join(lines)


def main() -> None:
    combined = []
    family_data: dict[str, dict[str, float]] = {}
    for model in DISPLAY:
        summary = source(model, "summary").iloc[0]
        levels = source(model, "per_level").sort_values("level")
        domains = source(model, "per_domain")
        combined.append((model, summary, levels))
        family_data[model] = {family: accuracy for family, _, _, accuracy in family_rows(domains)}
        output = ANALYSIS / "models" / model / "ACCURACY_REPORT.md"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(model_report(model), encoding="utf-8")

    combined.sort(key=lambda item: float(item[1]["absolute_accuracy"]), reverse=True)
    lines = [
        "# Test 1: Unified Closed-Loop Accuracy Report", "", "## Scope", "",
        "Ten models were evaluated on the same 8,500-question closed-loop sample: 50 images per domain, 34 domains, and five difficulty levels. All values use the strict scoring policy described in the separate reports.", "",
        "The reproducible sampling procedure, exact model-facing instruction, five-level design, "
        "and strict comparison rules are documented in [Test 1 methodology](../METHODOLOGY.md).", "",
        "## Model accuracy by level", "",
        "| Rank | Model | Mean accuracy | L1 | L2 | L3 | L4 | L5 |", "|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for rank, (model, summary, levels) in enumerate(combined, 1):
        values = {int(row.level): row.absolute_accuracy for row in levels.itertuples(index=False)}
        lines.append(
            f"| {rank} | {DISPLAY[model]} | **{pct(summary['absolute_accuracy'])}** | "
            + " | ".join(pct(values[level]) for level in range(1, 6)) + " |"
        )
    lines.extend(["", "## Family-wise accuracy", "", "| Model | " + " | ".join(FAMILIES) + " |", "|---|" + "---:|" * len(FAMILIES)])
    for model, _, _ in combined:
        lines.append(f"| {DISPLAY[model]} | " + " | ".join(pct(family_data[model][family]) for family in FAMILIES) + " |")
    lines.extend(["", "Separate per-model reports are stored under `analysis/models/<model>/ACCURACY_REPORT.md`.", ""])
    (ANALYSIS / "TEST_1_UNIFIED_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {len(DISPLAY)} separate reports and {ANALYSIS / 'TEST_1_UNIFIED_REPORT.md'}")


if __name__ == "__main__":
    main()
