"""Generate 1,000 exact-parameter projectile-motion diagrams for GRIP."""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

G = 9.8
BACKGROUND = "#FDFAF4"
INK = "#18344B"
ARC = "#287D8E"
BALL = "#D75B3F"
WALL = "#D8B26E"


def font(size: int, bold: bool = False):
    path = Path("C:/Windows/Fonts") / ("arialbd.ttf" if bold else "arial.ttf")
    try:
        return ImageFont.truetype(str(path), size)
    except OSError:
        return ImageFont.load_default()


def kinematics(speed: float, angle_degrees: float):
    theta = math.radians(angle_degrees)
    vx = speed * math.cos(theta)
    vy = speed * math.sin(theta)
    flight = 2.0 * vy / G
    height = vy * vy / (2.0 * G)
    horizontal_range = speed * speed * math.sin(2.0 * theta) / G
    return flight, height, horizontal_range, vx, vy


def trajectory_height(speed: float, angle_degrees: float, x: float):
    theta = math.radians(angle_degrees)
    return x * math.tan(theta) - G * x * x / (2.0 * speed * speed * math.cos(theta) ** 2)


def fmt(value: float, places: int = 3):
    text = f"{value:.{places}f}"
    return text.rstrip("0").rstrip(".")


def make_scene(index: int):
    rng = random.Random(73_000_000 + index)
    speed = rng.randint(10, 40)
    angle = rng.randint(15, 75)
    flight, max_height, horizontal_range, vx, vy = kinematics(speed, angle)
    has_obstacle = index % 10 in (0, 1, 2)
    obstacle = None
    if has_obstacle:
        fraction = rng.uniform(0.28, 0.72)
        x = horizontal_range * fraction
        path_height = max(0.0, trajectory_height(speed, angle, x))
        # Alternate clearly hit/clear cases and keep a visible margin.
        if index % 2 == 0:
            wall_height = path_height * rng.uniform(0.42, 0.78)
        else:
            wall_height = path_height * rng.uniform(1.18, 1.55)
        clears = path_height > wall_height
        obstacle = {
            "position_m": x,
            "height_m": wall_height,
            "trajectory_height_m": path_height,
            "clears_obstacle": clears,
            "clearance_margin_m": path_height - wall_height,
        }
    range_45 = speed * speed / G
    comparison_epsilon = 1e-9
    if range_45 > horizontal_range + comparison_epsilon:
        range_change = "increase"
    elif range_45 < horizontal_range - comparison_epsilon:
        range_change = "decrease"
    else:
        range_change = "stay the same"
    item_id = f"projectile_motion_{index:04d}"
    q4_truth = {"time_of_flight_s": round(flight, 1), "range_m": round(horizontal_range, 1)}
    if obstacle:
        if obstacle["clears_obstacle"]:
            q5_truth = f"clears; by {obstacle['clearance_margin_m']:.1f} m"
        else:
            q5_truth = f"hits; at {obstacle['trajectory_height_m']:.1f} m"
        q5_text = (
            "Does the projectile clear the obstacle shown, or does it hit it? If it clears, "
            "by how much height in meters? If it hits, at what height does it strike?"
        )
        q5_type = "obstacle_clearance"
    else:
        q5_truth = range_change
        q5_text = (
            "If the launch angle were changed to 45 degrees while keeping the same initial "
            "speed, would the horizontal range increase, decrease, or stay the same?"
        )
        q5_type = "range_at_45_degrees"
    questions = [
        {"question_id": f"{item_id}_q1", "difficulty_level": 1, "question_type": "read_launch_angle", "question_text": "What is the initial launch angle shown, in degrees?", "ground_truth": str(angle), "answer_format": "integer degrees"},
        {"question_id": f"{item_id}_q2", "difficulty_level": 2, "question_type": "height_above_20m", "question_text": "Will the projectile reach a higher maximum height than 20 meters? Answer yes or no.", "ground_truth": "yes" if max_height > 20.0 else "no", "answer_format": "yes or no"},
        {"question_id": f"{item_id}_q3", "difficulty_level": 3, "question_type": "horizontal_position_at_peak", "question_text": "At what horizontal distance from launch does the projectile reach its maximum height? Answer in meters, rounded to 1 decimal.", "ground_truth": f"{horizontal_range / 2.0:.1f}", "answer_format": "meters rounded to 1 decimal; numeric tolerance 2%"},
        {"question_id": f"{item_id}_q4", "difficulty_level": 4, "question_type": "flight_time_and_range", "question_text": "What are the total time of flight in seconds and total horizontal range in meters? Round both to 1 decimal.", "ground_truth": q4_truth, "answer_format": {"type": "numeric_tolerance", "tolerance_percent": 2, "fields": ["time_of_flight_s", "range_m"]}},
        {"question_id": f"{item_id}_q5", "difficulty_level": 5, "question_type": q5_type, "question_text": q5_text, "ground_truth": q5_truth, "answer_format": "classification plus meters rounded to 1 decimal" if obstacle else "increase, decrease, or stay the same"},
    ]
    difficulty = 0.25 + 0.12 * (angle % 5 != 0) + 0.12 * (speed % 5 != 0) + 0.18 * has_obstacle + 0.12 * (max_height > 20)
    return {
        "id": item_id,
        "dataset_version": "projectile-motion-1.0.0",
        "image_path": f"images/{item_id}.png",
        "seed": index,
        "canvas_width": 550 + (index % 6) * 20,
        "canvas_height": 400 + (index % 3) * 25,
        "gravity_m_s2": G,
        "initial_speed_m_s": speed,
        "launch_angle_degrees": angle,
        "time_of_flight_s": flight,
        "max_height_m": max_height,
        "range_m": horizontal_range,
        "initial_velocity_x_m_s": vx,
        "initial_velocity_y_m_s": vy,
        "horizontal_position_at_peak_m": horizontal_range / 2.0,
        "has_obstacle": has_obstacle,
        "obstacle": obstacle,
        "range_at_45_degrees_m": range_45,
        "range_change_at_45_degrees": range_change,
        "difficulty_score": round(min(difficulty, 0.98), 4),
        "questions": questions,
    }


def arrow(draw, start, end, fill, width, head=12):
    draw.line([start, end], fill=fill, width=width)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    for offset in (2.55, -2.55):
        point = (end[0] + head * math.cos(angle + offset), end[1] + head * math.sin(angle + offset))
        draw.line([end, point], fill=fill, width=width)


def render(scene, destination: Path):
    width, height = scene["canvas_width"], scene["canvas_height"]
    scale = 2
    image = Image.new("RGB", (width * scale, height * scale), BACKGROUND)
    draw = ImageDraw.Draw(image)
    ground_y = height - 52
    left = 54
    right = width - 42
    top = 48
    x_scale = (right - left) / scene["range_m"]
    obstacle_height = scene["obstacle"]["height_m"] if scene["obstacle"] else 0.0
    y_scale = (ground_y - top) / max(max(scene["max_height_m"], obstacle_height) * 1.16, 1.0)
    sx = scale

    def P(x, y):
        return (int(round(x * sx)), int(round(y * sx)))

    draw.rectangle((0, ground_y * sx, width * sx, height * sx), fill="#F0E9DC")
    draw.line([P(24, ground_y), P(width - 24, ground_y)], fill=INK, width=3 * sx)
    for x in range(32, width - 20, 22):
        draw.line([P(x, ground_y + 2), P(x - 8, ground_y + 10)], fill="#A8A39A", width=sx)

    points = []
    speed = scene["initial_speed_m_s"]
    angle = scene["launch_angle_degrees"]
    for step in range(181):
        physical_x = scene["range_m"] * step / 180.0
        physical_y = max(0.0, trajectory_height(speed, angle, physical_x))
        points.append(P(left + physical_x * x_scale, ground_y - physical_y * y_scale))
    for i in range(len(points) - 1):
        if (i // 5) % 2 == 0:
            draw.line([points[i], points[i + 1]], fill=ARC, width=3 * sx)

    peak_x = left + scene["horizontal_position_at_peak_m"] * x_scale
    peak_y = ground_y - scene["max_height_m"] * y_scale
    draw.ellipse((peak_x * sx - 6, peak_y * sx - 6, peak_x * sx + 6, peak_y * sx + 6), fill="#7B3F91", outline=INK, width=2)
    draw.text(P(peak_x + 8, peak_y - 25), "PEAK", fill=INK, font=font(12 * sx, True))

    landing_x = left + scene["range_m"] * x_scale
    draw.line([P(landing_x, ground_y), P(landing_x, ground_y - 35)], fill=INK, width=3 * sx)
    draw.polygon([P(landing_x, ground_y - 35), P(landing_x + 22, ground_y - 27), P(landing_x, ground_y - 19)], fill="#D75B3F")

    if scene["obstacle"]:
        obstacle = scene["obstacle"]
        wall_x = left + obstacle["position_m"] * x_scale
        wall_height_px = obstacle["height_m"] * y_scale
        wall_width = max(10, min(18, width // 35))
        draw.rectangle([P(wall_x - wall_width / 2, ground_y - wall_height_px), P(wall_x + wall_width / 2, ground_y)], fill=WALL, outline=INK, width=2 * sx)
        label = f"WALL {obstacle['height_m']:.1f} m"
        draw.text(P(wall_x - 34, ground_y - wall_height_px - 24), label, fill=INK, font=font(11 * sx, True))

    draw.ellipse([P(left - 8, ground_y - 8), P(left + 8, ground_y + 8)], fill=BALL, outline=INK, width=2 * sx)
    vector_length = 72
    theta = math.radians(angle)
    end = P(left + vector_length * math.cos(theta), ground_y - vector_length * math.sin(theta))
    arrow(draw, P(left, ground_y), end, BALL, 4 * sx, 10 * sx)
    label = f"v0 = {speed} m/s\nangle = {angle}°"
    draw.multiline_text(P(left + 10, max(8, ground_y - vector_length * math.sin(theta) - 50)), label, fill=INK, font=font(14 * sx, True), spacing=3 * sx)
    draw.text(P(24, height - 28), "GROUND", fill="#69777F", font=font(11 * sx, True))
    image = image.resize((width, height), Image.Resampling.LANCZOS)
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, optimize=True)


def write_dataset(output: Path, count: int, start: int, render_images: bool = True):
    output.mkdir(parents=True, exist_ok=True)
    (output / "images").mkdir(parents=True, exist_ok=True)
    rows = []
    for position, index in enumerate(range(start, start + count), 1):
        scene = make_scene(index)
        image_path = output / scene["image_path"]
        if render_images:
            render(scene, image_path)
        elif not image_path.exists():
            raise FileNotFoundError(image_path)
        rows.append(scene)
        if position % 100 == 0:
            print(f"Processed {position}/{count}", flush=True)
    with (output / "annotations.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"Generated {len(rows)} records in {output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--count", type=int, default=1000)
    parser.add_argument("--start-index", type=int, default=1)
    parser.add_argument("--sample", action="store_true")
    parser.add_argument("--metadata-only", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    output = args.output_dir or (root / "sample_test" if args.sample else root)
    write_dataset(output, 5 if args.sample else args.count, args.start_index, not args.metadata_only)


if __name__ == "__main__":
    main()
