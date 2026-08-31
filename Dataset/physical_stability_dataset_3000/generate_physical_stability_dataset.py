"""Generate 3,000 exact 2D block-stack stability reasoning scenes."""

from __future__ import annotations

import argparse
import json
import random
from fractions import Fraction
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


CANVAS_SIZE = 600
BACKGROUND = "#FDFAF4"
INK = "#18344B"
GROUND = "#46545E"
COM_COLOR = "#B43E35"
FILLS = ["#D8E9EE", "#F2D8B3", "#DCE7C8", "#E6D8EA", "#F0D5D1"]


def font(size: int, bold: bool = False):
    name = "arialbd.ttf" if bold else "arial.ttf"
    path = Path("C:/Windows/Fonts") / name
    try:
        return ImageFont.truetype(str(path), size)
    except OSError:
        return ImageFont.load_default()


def compute_combined_com(blocks_above_joint: list[dict]) -> Fraction:
    total_mass = sum(int(block["mass"]) for block in blocks_above_joint)
    if total_mass <= 0:
        raise ValueError("combined center of mass requires positive mass")
    moment = sum(
        int(block["mass"]) * Fraction(str(block["center_of_mass_x"]))
        for block in blocks_above_joint
    )
    return moment / total_mass


def check_stack_stability(blocks: list[dict]):
    """Return overall stability, lowest failing joint, and all joint checks.

    Blocks are ordered bottom-to-top. Joint zero is the ground/bottom-block
    contact and uses the bottom block's footprint. Joint k>0 is the contact
    between blocks k-1 and k and supports blocks k..top.
    """
    if not blocks:
        return True, None, []
    joints = []
    first_failure = None
    for upper_index in range(len(blocks)):
        upper = blocks[upper_index]
        if upper_index == 0:
            below_label = "ground"
            support = blocks[0]
        else:
            support = blocks[upper_index - 1]
            below_label = support["label"]
        supported = blocks[upper_index:]
        combined = compute_combined_com(supported)
        left = Fraction(str(support["x_position"]))
        right = left + Fraction(str(support["width"]))
        stable = left <= combined <= right
        joint = {
            "joint_between": [below_label, upper["label"]],
            "block_below": below_label,
            "upper_block": upper["label"],
            "blocks_above": [block["label"] for block in supported],
            "combined_com_x": round(float(combined), 6),
            "combined_com_x_fraction": f"{combined.numerator}/{combined.denominator}",
            "supporting_base_range": [float(left), float(right)],
            "is_stable_at_this_joint": stable,
        }
        joints.append(joint)
        if not stable and first_failure is None:
            first_failure = upper["label"]
    return first_failure is None, first_failure, joints


def remove_top_block_and_recheck(blocks: list[dict]):
    return check_stack_stability(blocks[:-1])


def block_records(labels, widths, heights, centers):
    ground_y = 515
    records = []
    current_bottom = ground_y
    for label, width, height, center in zip(labels, widths, heights, centers):
        top = current_bottom - height
        left = center - width // 2
        records.append({
            "label": label,
            "width": width,
            "height": height,
            "x_position": left,
            "y_position": top,
            "center_of_mass_x": center,
            "center_of_mass_y": top + height / 2,
            "mass": width * height,
        })
        current_bottom = top
    return records


def central_stack(rng, num_blocks):
    widths = [rng.randrange(120, 182, 2) for _ in range(num_blocks)]
    heights = [rng.randrange(42, 78, 2) for _ in range(num_blocks)]
    centers = [300]
    for index in range(1, num_blocks):
        magnitude = 4 * index
        centers.append(centers[-1] + rng.choice([-1, 1]) * magnitude)
    return widths, heights, centers


def construct_configuration(index: int):
    """Construct one of four exact original/removal stability combinations."""
    rng = random.Random(index)
    mode = index % 4
    if mode in {0, 2}:
        num_blocks = rng.choice([2, 3, 4, 5])
    else:
        num_blocks = rng.choice([3, 4, 5])
    labels = [chr(ord("A") + i) for i in range(num_blocks)]

    if mode == 1:  # Stable only because the heavy top block counterbalances right overhang.
        widths = [120] + [180] * (num_blocks - 1)
        heights = [70] + [34] * (num_blocks - 2) + [90]
        centers = [300] + [365] * (num_blocks - 2) + [285]
        scenario = "stable_becomes_unstable"
    else:
        widths, heights, centers = central_stack(rng, num_blocks)
        if mode == 0:
            scenario = "stable_remains_stable"
        elif mode == 2:  # Top block alone overhangs its support's right edge.
            support_index = num_blocks - 2
            centers[-1] = centers[support_index] + widths[support_index] // 2 + 10
            widths[-1] = min(widths[-1], 120)
            scenario = "unstable_becomes_stable"
        else:  # Top two share an overhanging center, so removing one does not fix it.
            support_index = num_blocks - 3
            overhang_center = centers[support_index] + widths[support_index] // 2 + 10
            centers[-2] = overhang_center
            centers[-1] = overhang_center
            widths[-2] = min(widths[-2], 120)
            widths[-1] = min(widths[-1], 120)
            scenario = "unstable_remains_unstable"

    blocks = block_records(labels, widths, heights, centers)
    is_stable, tipping_joint, joints = check_stack_stability(blocks)
    reduced_stable, reduced_tipping, reduced_joints = remove_top_block_and_recheck(blocks)
    expected = {
        0: (True, True),
        1: (True, False),
        2: (False, True),
        3: (False, False),
    }[mode]
    if (is_stable, reduced_stable) != expected:
        raise AssertionError(
            f"constructive scene {index} failed: {(is_stable, reduced_stable)} != {expected}"
        )
    return blocks, scenario, is_stable, tipping_joint, joints, reduced_stable, reduced_tipping, reduced_joints


def relative_position(upper, lower):
    if upper["center_of_mass_x"] < lower["center_of_mass_x"]:
        return "left"
    if upper["center_of_mass_x"] > lower["center_of_mass_x"]:
        return "right"
    return "directly above"


def joint_answer(tipping_joint, blocks):
    if tipping_joint is None:
        return "stable"
    index = next(i for i, block in enumerate(blocks) if block["label"] == tipping_joint)
    below = "ground" if index == 0 else f"block {blocks[index - 1]['label']}"
    return f"tips between block {tipping_joint} and {below}"


def counterfactual_answer(top_label, stable, tipping_joint, blocks):
    if stable:
        return (
            f"stable; after removing block {top_label}, every cumulative center of mass "
            "remains within its supporting base"
        )
    index = next(i for i, block in enumerate(blocks[:-1]) if block["label"] == tipping_joint)
    below = "ground" if index == 0 else f"block {blocks[index - 1]['label']}"
    return (
        f"unstable; after removing block {top_label}, the cumulative center of mass at "
        f"the joint between block {tipping_joint} and {below} lies outside its supporting base"
    )


def make_scene(index: int):
    rng = random.Random(index)
    blocks, scenario, stable, tipping, joints, reduced_stable, reduced_tipping, reduced_joints = construct_configuration(index)
    upper_index = rng.randrange(1, len(blocks))
    upper, lower = blocks[upper_index], blocks[upper_index - 1]
    offsets = {
        block["label"]: abs(block["center_of_mass_x"] - blocks[i - 1]["center_of_mass_x"])
        for i, block in enumerate(blocks) if i > 0
    }
    max_offset = max(offsets.values())
    leaders = [label for label, value in offsets.items() if value == max_offset]
    if len(leaders) != 1:
        raise AssertionError(f"scene {index} has ambiguous maximum offset: {leaders}")
    furthest = leaders[0]
    top = blocks[-1]
    iid = f"physical_stability_{index:04d}"
    questions = [
        {
            "question_id": f"{iid}_q1", "difficulty_level": 1,
            "question_type": "block_count",
            "question_text": "How many blocks are in this stack?",
            "ground_truth": str(len(blocks)), "answer_format": "number",
        },
        {
            "question_id": f"{iid}_q2", "difficulty_level": 2,
            "question_type": "relative_center_of_mass",
            "question_text": (
                f"Is block {upper['label']}'s center of mass positioned to the left, right, "
                f"or directly above the center of block {lower['label']}, which it rests on?"
            ),
            "ground_truth": relative_position(upper, lower),
            "answer_format": "left, right, or directly above",
        },
        {
            "question_id": f"{iid}_q3", "difficulty_level": 3,
            "question_type": "largest_support_offset",
            "question_text": (
                "Which block has the largest absolute horizontal center offset from the "
                "block directly beneath it? Answer with the letter."
            ),
            "ground_truth": furthest, "answer_format": "single uppercase letter",
        },
        {
            "question_id": f"{iid}_q4", "difficulty_level": 4,
            "question_type": "whole_stack_stability",
            "question_text": (
                "Is this entire stack stable, or will it tip over? If it tips, state the "
                "lowest joint at which it first becomes unstable."
            ),
            "ground_truth": joint_answer(tipping, blocks),
            "answer_format": "stable or 'tips between block X and <block Y|ground>'",
        },
        {
            "question_id": f"{iid}_q5", "difficulty_level": 5,
            "question_type": "remove_top_recheck_stability",
            "question_text": (
                f"If topmost block {top['label']} were removed, would the remaining stack "
                "be stable or unstable? Answer accordingly and briefly state the "
                "center-of-mass reason."
            ),
            "ground_truth": counterfactual_answer(top["label"], reduced_stable, reduced_tipping, blocks),
            "answer_format": "'<stable|unstable>; <brief cumulative-center-of-mass reason>'",
        },
    ]
    difficulty = 0.25 + 0.09 * len(blocks) + (0.12 if not stable else 0.04) + (0.10 if scenario in {"stable_becomes_unstable", "unstable_remains_unstable"} else 0)
    return {
        "id": iid,
        "image_path": f"images/{iid}.png",
        "canvas_size": [CANVAS_SIZE, CANVAS_SIZE],
        "seed": index,
        "num_blocks": len(blocks),
        "blocks": blocks,
        "is_stable": stable,
        "tipping_joint": tipping,
        "per_joint_stability": joints,
        "level2_upper_block": upper["label"],
        "largest_offset_block": furthest,
        "counterfactual_scenario": scenario,
        "after_top_removal": {
            "removed_block": top["label"],
            "is_stable": reduced_stable,
            "tipping_joint": reduced_tipping,
            "per_joint_stability": reduced_joints,
        },
        "difficulty_score": round(min(difficulty, 0.98), 4),
        "questions": questions,
    }


def render(scene: dict, destination: Path):
    scale = 2
    image = Image.new("RGB", (CANVAS_SIZE * scale, CANVAS_SIZE * scale), BACKGROUND)
    draw = ImageDraw.Draw(image)
    def S(values): return tuple(int(round(value * scale)) for value in values)

    title = "CENTER-OF-MASS STACK"
    title_font = font(22 * scale, True)
    box = draw.textbbox((0, 0), title, font=title_font)
    draw.text(((CANVAS_SIZE * scale - (box[2] - box[0])) / 2, 35 * scale), title, fill=INK, font=title_font)
    draw.ellipse(S((420, 75, 430, 85)), fill=COM_COLOR, outline=INK, width=1 * scale)
    draw.text(S((438, 68)), "block center of mass", fill="#52636D", font=font(14 * scale))

    ground_y = 515
    draw.line([S((45, ground_y)), S((555, ground_y))], fill=GROUND, width=4 * scale)
    for x in range(55, 556, 18):
        draw.line([S((x, ground_y)), S((x - 8, ground_y + 10))], fill="#89939A", width=1 * scale)
    draw.text(S((50, 535)), "GROUND", fill="#65727A", font=font(14 * scale, True))

    for index, block in enumerate(scene["blocks"]):
        left, top = block["x_position"], block["y_position"]
        right, bottom = left + block["width"], top + block["height"]
        draw.rounded_rectangle(
            S((left, top, right, bottom)), radius=5 * scale,
            fill=FILLS[index % len(FILLS)], outline=INK, width=3 * scale,
        )
        label_font = font(23 * scale, True)
        draw.text(S((left + 12, top + 8)), block["label"], fill=INK, font=label_font)
        cx, cy = block["center_of_mass_x"], block["center_of_mass_y"]
        radius = 5
        draw.ellipse(S((cx - radius, cy - radius, cx + radius, cy + radius)), fill=COM_COLOR, outline=INK, width=1 * scale)

    image = image.resize((CANVAS_SIZE, CANVAS_SIZE), Image.Resampling.LANCZOS)
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, optimize=True)


def write_dataset(output_dir: Path, count: int, start_index: int, render_images: bool = True):
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "images").mkdir(parents=True, exist_ok=True)
    rows = []
    for position, index in enumerate(range(start_index, start_index + count), 1):
        scene = make_scene(index)
        image_path = output_dir / scene["image_path"]
        if render_images:
            render(scene, image_path)
        elif not image_path.exists():
            raise FileNotFoundError(f"metadata-only pass requires {image_path}")
        rows.append(scene)
        if count >= 100 and position % 100 == 0:
            print(f"{'Rendered' if render_images else 'Processed'} {position}/{count}", flush=True)
    with (output_dir / "annotations.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"Generated {len(rows)} {'images' if render_images else 'metadata rows'} in {output_dir}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--count", type=int, default=3000)
    parser.add_argument("--start-index", type=int, default=1)
    parser.add_argument("--sample", action="store_true")
    parser.add_argument("--metadata-only", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    output = args.output_dir or (root / "sample_test" if args.sample else root)
    write_dataset(output, 5 if args.sample else args.count, args.start_index, not args.metadata_only)


if __name__ == "__main__":
    main()
