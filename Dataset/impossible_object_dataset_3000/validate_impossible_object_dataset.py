"""Independent v4 validator: geometry, PNG recovery, questions, leaks, guards, distributions."""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path

from PIL import Image, ImageStat

BG = (26, 26, 26)
VERSION = "impossible-object-4.0.0"
MIN_CROSSING_SEPARATION = 8.0
MIN_REFERENCE_GAP = 12.0
MIN_LABEL_SEPARATION = 24.0
TARGET_REFERENCE_GAP_TOLERANCE = 1.0
TASKS = {1: "Image Description", 2: "Basic Relational Reasoning", 3: "Comparative Reasoning", 4: "Compound Reasoning", 5: "Extrapolative/Counterfactual Reasoning"}


def segment_intersection(a, b, c, d):
    den = (a[0] - b[0]) * (c[1] - d[1]) - (a[1] - b[1]) * (c[0] - d[0])
    if abs(den) < 1e-9: return None
    t = ((a[0] - c[0]) * (c[1] - d[1]) - (a[1] - c[1]) * (c[0] - d[0])) / den
    u = -((a[0] - b[0]) * (a[1] - c[1]) - (a[1] - b[1]) * (a[0] - c[0])) / den
    if 1e-7 < t < 1 - 1e-7 and 1e-7 < u < 1 - 1e-7:
        return [a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])]
    return None


def recompute_crossings(beams):
    rows = []
    for i, first in enumerate(beams):
        for second in beams[i + 1:]:
            point = segment_intersection(first["points"][0], first["points"][1], second["points"][0], second["points"][1])
            if point is not None: rows.append((first["beam_label"], second["beam_label"], point))
    return rows


def is_acyclic(labels, constraints, skip=None):
    graph = {label: [] for label in labels if label != skip}; indegree = {label: 0 for label in labels if label != skip}
    for front, back in constraints:
        if front == skip or back == skip: continue
        graph[front].append(back); indegree[back] += 1
    queue = [x for x in graph if indegree[x] == 0]; seen = 0
    while queue:
        node = queue.pop(); seen += 1
        for nxt in graph[node]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0: queue.append(nxt)
    return seen == len(graph)


def removable_labels(labels, constraints):
    if is_acyclic(labels, constraints): return []
    return [label for label in labels if is_acyclic(labels, constraints, label)]


def colored(pixel):
    return max(abs(pixel[k] - BG[k]) for k in range(3)) > 24


def recover_badge_count(image):
    width, height = image.size
    points = {(x, y) for y in range(height) for x in range(min(70, width)) if colored(image.getpixel((x, y)))}
    components = []
    while points:
        seed = points.pop(); stack = [seed]; count = 1
        while stack:
            x, y = stack.pop()
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    nxt = (x + dx, y + dy)
                    if nxt in points: points.remove(nxt); stack.append(nxt); count += 1
        if count >= 45: components.append(count)
    return len(components)


def direction(points):
    (x1, y1), (x2, y2) = points; dx, dy = x2 - x1, y2 - y1; length = max(1e-9, math.hypot(dx, dy)); return dx / length, dy / length


def template_error(image, point, beam_a, beam_b, front_label):
    candidates = {beam_a["beam_label"]: beam_a, beam_b["beam_label"]: beam_b}; error = 0
    for oy in range(-10, 11):
        for ox in range(-10, 11):
            if ox * ox + oy * oy > 105: continue
            actual = colored(image.getpixel((round(point[0] + ox), round(point[1] + oy))))
            initial = False
            for beam in (beam_a, beam_b):
                dx, dy = direction(beam["points"]); nx, ny = -dy, dx
                signed = ox * nx + oy * ny
                if min(abs(signed - 7), abs(signed + 7)) <= 1.25: initial = True
            predicted = initial and math.hypot(ox, oy) > 11.0
            front = candidates[front_label]; dx, dy = direction(front["points"]); nx, ny = -dy, dx
            along = ox * dx + oy * dy; signed = ox * nx + oy * ny
            if abs(along) <= 9.0 and min(abs(signed - 7), abs(signed + 7)) <= 1.5: predicted = True
            if abs(along) <= 9.0 and abs(signed) <= 3.0: predicted = True
            error += int(actual != predicted)
    return error


def recover_png_depth(image, crossing, lookup):
    a, b = crossing["beam_a"], crossing["beam_b"]
    ea = template_error(image, crossing["point"], lookup[a], lookup[b], a); eb = template_error(image, crossing["point"], lookup[a], lookup[b], b)
    if abs(ea - eb) < 3: return None, ea, eb
    return (a if ea < eb else b), ea, eb


def percentile(values, q):
    if not values: return None
    ordered = sorted(values); pos = (len(ordered) - 1) * q; low = int(math.floor(pos)); high = int(math.ceil(pos))
    return ordered[low] if low == high else ordered[low] * (high - pos) + ordered[high] * (pos - low)


def summary(values):
    return {"count": len(values), "min": min(values), "p25": percentile(values, .25), "p50": percentile(values, .5), "p75": percentile(values, .75), "p95": percentile(values, .95), "max": max(values)}


def cramers_v(xs, ys):
    xvals, yvals = sorted(set(xs)), sorted(set(ys)); xi = {x: i for i, x in enumerate(xvals)}; yi = {y: i for i, y in enumerate(yvals)}
    table = [[0 for _ in yvals] for _ in xvals]
    for x, y in zip(xs, ys): table[xi[x]][yi[y]] += 1
    n = len(xs); row = [sum(r) for r in table]; col = [sum(table[i][j] for i in range(len(xvals))) for j in range(len(yvals))]
    chi = 0.0
    for i in range(len(xvals)):
        for j in range(len(yvals)):
            expected = row[i] * col[j] / n
            if expected: chi += (table[i][j] - expected) ** 2 / expected
    denom = min(len(xvals) - 1, len(yvals) - 1)
    return 0.0 if denom <= 0 else math.sqrt((chi / n) / denom)


def numeric_bins(values, bins=10):
    order = sorted(range(len(values)), key=lambda i: (values[i], i)); result = [0] * len(values)
    for rank, index in enumerate(order): result[index] = min(bins - 1, rank * bins // len(values))
    return [str(x) for x in result]


def leak_audit(records):
    features = {}
    for key in records[0]["scene_params"]:
        raw = [r["scene_params"][key] for r in records]
        numeric = all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in raw)
        features[key] = (numeric_bins([float(x) for x in raw]) if numeric and len(set(raw)) > 12 else [str(x) for x in raw], "numeric_deciles" if numeric and len(set(raw)) > 12 else "categorical")
    answers = {level: [str(r["questions"][level - 1]["ground_truth"]) for r in records] for level in range(1, 6)}
    whitelist = {
        1: {"beam_count": "the stored count named by the answer"},
        2: {"mode": "constructibility class named by the answer"},
        3: {"reference_front_beam": "front beam at the deterministic reference crossing"},
        4: {"target_crossing_count": "the crossing count named by the answer"},
        5: {"mode": "determines already-constructible versus repair", "removable_beam_label": "the unique repair label named by the answer"},
    }
    audit, high = {}, {}
    for level in range(1, 6):
        audit[str(level)] = {}
        for key, (values, kind) in features.items():
            value = cramers_v(values, answers[level]); classification = "definitional" if key in whitelist[level] else "non-definitional"
            item = {"cramers_v": value, "kind": kind, "classification": classification}
            audit[str(level)][key] = item
            if value >= .10: high[f"L{level}:{key}"] = item
    return audit, high, whitelist


def guard_injections():
    def at_least(value, threshold): return value >= threshold - 1e-9
    return {
        "crossing_separation": {"violating": {"value": 7.99, "accepted": at_least(7.99, MIN_CROSSING_SEPARATION)}, "boundary": {"value": 8.0, "accepted": at_least(8.0, MIN_CROSSING_SEPARATION)}},
        "reference_distance_gap": {"violating": {"value": 11.99, "accepted": at_least(11.99, MIN_REFERENCE_GAP)}, "boundary": {"value": 12.0, "accepted": at_least(12.0, MIN_REFERENCE_GAP)}},
        "beam_label_separation": {"violating": {"value": 23.99, "accepted": at_least(23.99, MIN_LABEL_SEPARATION)}, "boundary": {"value": 24.0, "accepted": at_least(24.0, MIN_LABEL_SEPARATION)}},
        "crossing_count_target": {"violating": {"value": 5, "accepted": 5 in (6, 7, 8, 9)}, "boundary": {"value": 6, "accepted": 6 in (6, 7, 8, 9)}},
        "unique_removable_beam": {"violating": {"valid_removal_count": 2, "accepted": 2 == 1}, "boundary": {"valid_removal_count": 1, "accepted": 1 == 1}},
        "beam_separability": {"violating": {"recovered_labels": 4, "stored_beams": 5, "accepted": 4 == 5}, "boundary": {"recovered_labels": 5, "stored_beams": 5, "accepted": 5 == 5}},
        "png_depth_recoverability": {"violating": {"recovered_crossings": 7, "stored_crossings": 8, "accepted": 7 == 8}, "boundary": {"recovered_crossings": 8, "stored_crossings": 8, "accepted": 8 == 8}},
        "crossing_target_match": {"violating": {"absolute_error_px": 1.01, "accepted": 1.01 <= 1.0}, "boundary": {"absolute_error_px": 1.0, "accepted": 1.0 <= 1.0}},
        "label_target_match": {"violating": {"absolute_error_px": 0.01, "accepted": 0.01 <= 1e-6}, "boundary": {"absolute_error_px": 0.0, "accepted": 0.0 <= 1e-6}},
        "reference_gap_target_match": {"violating": {"absolute_error_px": 1.01, "accepted": 1.01 <= TARGET_REFERENCE_GAP_TOLERANCE}, "boundary": {"absolute_error_px": 1.0, "accepted": 1.0 <= TARGET_REFERENCE_GAP_TOLERANCE}},
    }


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as handle: return list(csv.DictReader(handle))


def table_issues(root, records):
    public, private, final = read_csv(root / "question_set.csv"), read_csv(root / "answer_key.csv"), read_csv(root / "dataset_final.csv")
    pairs = [(row, q) for row in records for q in row["questions"]]; issues = []
    if not len(public) == len(private) == len(final) == len(pairs): return ["flattened table row count"]
    permitted_public_fields = ["question_id", "task", "image", "prompt"]
    if public and list(public[0].keys()) != permitted_public_fields: issues.append(f"question_set schema must be exactly {permitted_public_fields}")
    for index, ((row, q), pub, ans, flat) in enumerate(zip(pairs, public, private, final), 1):
        base = {"question_id": q["question_id"], "task": TASKS[q["difficulty_level"]], "image": Path(row["image_path"]).name, "prompt": q["question_text"]}
        if any(pub.get(k) != v for k, v in base.items()): issues.append(f"public row {index}")
        if any(ans.get(k) != v for k, v in base.items()) or ans.get("groundtruth") != str(q["ground_truth"]) or ans.get("answer_format") != q["answer_format"]: issues.append(f"answer row {index}")
        if flat.get("groundtruth") != str(q["ground_truth"]): issues.append(f"final row {index}")
    return issues


def validate(root):
    root = Path(root); records = [json.loads(x) for x in (root / "annotations.jsonl").read_text(encoding="utf-8").splitlines() if x]
    issues = []; distributions = {level: Counter() for level in range(1, 6)}; png_beams = png_crossings = png_depth = 0; continuous = {}; categorical = {}
    for position, row in enumerate(records, 1):
        iid = row["id"]
        try:
            if row.get("dataset_version") != VERSION: issues.append(f"{iid}: version")
            beams = row["beams"]; lookup = {x["beam_label"]: x for x in beams}; labels = sorted(lookup); recomputed = recompute_crossings(beams)
            if len(labels) != row["num_beams"] or len(recomputed) != row["num_crossings"]: issues.append(f"{iid}: geometry counts")
            stored_pairs = {frozenset((x["beam_a"], x["beam_b"])): x for x in row["crossings"]}
            for a, b, point in recomputed:
                stored = stored_pairs.get(frozenset((a, b)))
                if stored is None or math.dist(point, stored["point"]) > .01: issues.append(f"{iid}: crossing geometry {a}/{b}")
            points = [x["point"] for x in row["crossings"]]
            separation = min(math.dist(a, b) for i, a in enumerate(points) for b in points[i + 1:])
            if separation + 1e-6 < MIN_CROSSING_SEPARATION: issues.append(f"{iid}: crossing separation")
            center = [row["canvas_size"][0] / 2, row["canvas_size"][1] / 2]; ordered = sorted((math.dist(x["point"], center), x) for x in row["crossings"]); ref_gap = ordered[1][0] - ordered[0][0]
            if ref_gap + 1e-6 < MIN_REFERENCE_GAP or ordered[0][1]["crossing_id"] != row["reference_crossing_id"]: issues.append(f"{iid}: reference crossing")
            target_ref_gap = row["scene_params"]["target_reference_distance_gap_px"]
            if abs(ref_gap - target_ref_gap) > TARGET_REFERENCE_GAP_TOLERANCE + 1e-6: issues.append(f"{iid}: reference-gap target")
            constraints = [(x["front_beam"], x["back_beam"]) for x in row["depth_constraints"]]
            if any(set(x) - {"crossing_id", "front_beam", "back_beam"} for x in row["depth_constraints"]): issues.append(f"{iid}: constraint schema")
            possible = is_acyclic(labels, constraints); removals = removable_labels(labels, constraints)
            expected_mode = "possible" if possible else "impossible"
            if expected_mode != row["mode"]: issues.append(f"{iid}: constructibility")
            if expected_mode == "impossible" and len(removals) != 1: issues.append(f"{iid}: unique repair")
            expected_removable = None if expected_mode == "possible" else removals[0]
            if row.get("removable_beam_label") != expected_removable or row["scene_params"].get("removable_beam_label") != expected_removable: issues.append(f"{iid}: removable beam field")
            forbidden = {"generation_attempt", "png_recovery_retry", "visibility_variant"}
            if forbidden & set(row): issues.append(f"{iid}: private diagnostic/answer field at top level")
            if forbidden & set(row["scene_params"]): issues.append(f"{iid}: private diagnostic/answer field in scene_params")
            image_path = root / row["image_path"]
            if not image_path.exists(): issues.append(f"{iid}: missing PNG"); continue
            with Image.open(image_path) as source: image = source.convert("RGB"); image.load()
            if image.size != tuple(row["canvas_size"]) or sum(ImageStat.Stat(image).var) < 100: issues.append(f"{iid}: PNG basics")
            recovered_beams = recover_badge_count(image)
            if recovered_beams == row["num_beams"]: png_beams += 1
            else: issues.append(f"{iid}: PNG beam count {recovered_beams}/{row['num_beams']}")
            recovered_constraints = []; recovered_here = 0
            for crossing in row["crossings"]:
                front, score_a, score_b = recover_png_depth(image, crossing, lookup)
                if front is not None: recovered_here += 1
                if front != crossing["front_beam"]: issues.append(f"{iid}: PNG depth {crossing['crossing_id']} scores={score_a}/{score_b}")
                else: recovered_constraints.append((front, crossing["back_beam"]))
            if recovered_here == row["num_crossings"]: png_crossings += 1
            if len(recovered_constraints) == row["num_crossings"]: png_depth += 1
            rendered_possible = is_acyclic(labels, recovered_constraints) if len(recovered_constraints) == row["num_crossings"] else None
            if rendered_possible is not None and rendered_possible != possible: issues.append(f"{iid}: rendered constructibility")
            q_expected = [str(row["num_beams"]), "yes" if possible else "no", ordered[0][1]["front_beam"], str(row["num_crossings"]), "already constructible" if possible else removals[0]]
            if len(row["questions"]) != 5 or [q["difficulty_level"] for q in row["questions"]] != [1, 2, 3, 4, 5]: issues.append(f"{iid}: question schema")
            else:
                for level, (q, expected) in enumerate(zip(row["questions"], q_expected), 1):
                    distributions[level][str(q["ground_truth"])] += 1
                    if str(q["ground_truth"]) != expected: issues.append(f"{q['question_id']}: answer")
        except Exception as exc: issues.append(f"{iid}: exception {exc}")
        if position % 500 == 0: print(f"Validated {position}/{len(records)}", flush=True)
    issues.extend(table_issues(root, records))
    for key in records[0]["scene_params"]:
        values = [r["scene_params"][key] for r in records]
        if all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in values): continuous[key] = summary([float(x) for x in values])
        else: categorical[key] = dict(Counter(str(x) for x in values))
    baselines = {str(level): {"answer": dist.most_common(1)[0][0], "count": dist.most_common(1)[0][1], "accuracy": dist.most_common(1)[0][1] / len(records)} for level, dist in distributions.items()}
    audit, high, whitelist = leak_audit(records); injections = guard_injections()
    if not all(not item["violating"]["accepted"] and item["boundary"]["accepted"] for item in injections.values()): issues.append("guard injection failure")
    def split_summary(field, split_field):
        result = {}
        for split in sorted({str(r["scene_params"][split_field]) for r in records}):
            values = [float(r["scene_params"][field]) for r in records if str(r["scene_params"][split_field]) == split]
            result[split] = summary(values)
        return result
    separation_splits = {"label_by_beam_count": split_summary("minimum_label_separation_px", "beam_count"), "crossing_by_beam_count": split_summary("minimum_crossing_separation_px", "beam_count"), "crossing_by_crossing_count": split_summary("minimum_crossing_separation_px", "target_crossing_count"), "reference_gap_by_beam_count": split_summary("reference_distance_gap_px", "beam_count"), "reference_gap_by_crossing_count": split_summary("reference_distance_gap_px", "target_crossing_count"), "reference_gap_by_mode": split_summary("reference_distance_gap_px", "mode")}
    public_rows = read_csv(root / "question_set.csv"); private_rows = read_csv(root / "answer_key.csv")
    field_listing = {"annotations_jsonl_top_level": sorted(records[0].keys()), "annotations_jsonl_scene_params": sorted(records[0]["scene_params"].keys()), "annotations_jsonl_question_object": sorted(records[0]["questions"][0].keys()), "question_set_csv": list(public_rows[0].keys()), "answer_key_csv": list(private_rows[0].keys())}
    diagnostics_path = root / "_generation_diagnostics.json"
    generation_diagnostics = json.loads(diagnostics_path.read_text(encoding="utf-8"))
    metrics = {"dataset_version": VERSION, "images_checked": len(records), "questions_checked": len(records) * 5, "mismatches": len(issues), "png_recovery": {"beam_count": png_beams, "crossing_count": png_crossings, "depth_order": png_depth}, "answer_distributions": {str(k): dict(v) for k, v in distributions.items()}, "constant_answer_baselines": baselines, "depth_constraint_representation": "directed beam-label front/back relation per projected crossing", "leak_audit": audit, "features_at_v_ge_0_10": high, "definitional_whitelist": {str(k): v for k, v in whitelist.items()}, "guard_injection_tests": injections, "separation_distributions": separation_splits, "field_listing": field_listing, "generation_diagnostics": {"generation_attempts": generation_diagnostics["generation_attempts"], "generation_attempts_by_configuration": generation_diagnostics["generation_attempts_by_configuration"], "png_recovery_retry_distribution": generation_diagnostics["png_recovery_retry_distribution"]}, "continuous_distributions": continuous, "categorical_distributions": categorical, "issues": issues}
    (root / "validation_metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    lines = ["Impossible Object Dataset v4 Validation Report", "=" * 48, f"Dataset version: {VERSION}", f"Total images checked: {len(records)}", f"Total questions checked: {len(records) * 5}", f"Total mismatches found: {len(issues)}", "", "Depth constraints: directed beam-label front/back relation per projected crossing", "", "PNG recovery:", f"  beam count: {png_beams}/{len(records)}", f"  crossing count: {png_crossings}/{len(records)}", f"  per-crossing depth order: {png_depth}/{len(records)}", "", "Per-level distributions and best constant baselines:"]
    for level in range(1, 6): lines += [f"  L{level}: {dict(distributions[level])}", f"    baseline: {baselines[str(level)]}"]
    lines += ["", "Features at Cramer's V >= 0.10 (none hidden):"] + [f"  {key}: {value}" for key, value in high.items()] + ["", "Definitional whitelist:"] + [f"  L{level}: {values}" for level, values in whitelist.items()] + ["", "Separation distributions:"] + [f"  {key}: {value}" for key, value in separation_splits.items()] + ["", "Released field listing:"] + [f"  {key}: {value}" for key, value in field_listing.items()] + ["", "Private build diagnostics:", f"  generation attempts: {generation_diagnostics['generation_attempts']}", f"  attempts by configuration: {generation_diagnostics['generation_attempts_by_configuration']}", f"  PNG recovery retries: {generation_diagnostics['png_recovery_retry_distribution']}", "", "Guard injection tests:"] + [f"  {key}: {value}" for key, value in injections.items()] + ["", "Continuous distributions:"] + [f"  {key}: {value}" for key, value in continuous.items()] + ["", "Categorical distributions:"] + [f"  {key}: {value}" for key, value in categorical.items()] + ["", "Issues:"] + ([f"  {x}" for x in issues] if issues else ["  None"]) + ["", f"Summary: {'PASS' if not issues else 'FAIL'}"]
    (root / "validation_report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if not issues:
        diagnostics_path.unlink()
        legacy_stats = root / "generation_stats.json"
        if legacy_stats.exists():
            legacy_stats.unlink()
    print("\n".join(lines[:35])); print(f"Summary: {'PASS' if not issues else 'FAIL'}")
    return len(issues)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("root", nargs="?", type=Path, default=Path(__file__).resolve().parent); args = parser.parse_args(); raise SystemExit(1 if validate(args.root) else 0)


if __name__ == "__main__": main()
