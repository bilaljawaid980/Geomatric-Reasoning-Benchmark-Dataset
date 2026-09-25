"""Shared, side-effect-free helpers for the open-ended cross-examination test."""

from __future__ import annotations

import ast
import hashlib
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pandas as pd

DEFAULT_MODELS = (
    "gpt_5_6_luna",
    "claude_opus_5",
    "claude_sonnet_5",
    "gemini_3_8_flash",
    "grok_4_6",
    "inking",
    "muse_glimmer_30b",
)

FAMILIES = {
    "angle_estimation": "Plane Geometry",
    "line_intersection": "Plane Geometry",
    "nested_hexagons": "Plane Geometry",
    "nested_squares": "Plane Geometry",
    "nested_triangles": "Plane Geometry",
    "combination3d": "Solid Geometry",
    "cube_net": "Solid Geometry",
    "cube_structure": "Solid Geometry",
    "depth_height": "Solid Geometry",
    "orthographic": "Solid Geometry",
    "polyhedron": "Solid Geometry",
    "combination": "Transformational",
    "embedded_figures": "Transformational",
    "fold_punch": "Transformational",
    "overlap_circles": "Transformational",
    "rotation_matching": "Transformational",
    "symmetry_pattern": "Transformational",
    "clock_reading": "Physical & Mechanical",
    "fbd": "Physical & Mechanical",
    "gauge_reading": "Physical & Mechanical",
    "gear_train": "Physical & Mechanical",
    "laser_mirror": "Physical & Mechanical",
    "physical_stability": "Physical & Mechanical",
    "projectile_motion": "Physical & Mechanical",
    "hex_pathfinding": "Topological",
    "route": "Topological",
    "surface_topology": "Topological",
    "occluded_pattern": "Projective",
    "shadow_inference": "Projective",
    "compass_bearing": "Analytic",
    "coordinate_geometry": "Analytic",
    "impossible_object": "Optical",
    "optical_illusion": "Optical",
    "rpm": "Inductive",
}

META_COLUMNS = {
    "question_id", "image", "prompt", "acceptance_set", "tolerances", "targets",
}


def stable_int(*parts: object) -> int:
    return int.from_bytes(
        hashlib.sha256("\x1f".join(map(str, parts)).encode("utf-8")).digest()[:8],
        "big",
    )


def parse_models(value: str | None) -> list[str]:
    models = list(DEFAULT_MODELS) if not value else [x.strip() for x in value.split(",") if x.strip()]
    if len(models) != len(set(models)):
        raise ValueError("Duplicate model keys are not allowed")
    return models


def json_list(value: Any) -> list[str]:
    parsed = json.loads(str(value))
    if not isinstance(parsed, list) or not all(isinstance(x, str) for x in parsed):
        raise ValueError(f"Expected a JSON string list, got {value!r}")
    return parsed


def parse_claim_string(value: str) -> dict[str, str]:
    claims: dict[str, str] = {}
    for part in str(value).split(";"):
        if "=" not in part:
            continue
        key, answer = part.split("=", 1)
        key, answer = key.strip(), answer.strip()
        if key:
            claims[key] = answer
    return claims


def canonical_claim_string(claims: dict[str, Any]) -> str:
    return "; ".join(f"{key}={str(value).strip()}" for key, value in claims.items())


def normalize_scalar(value: Any) -> str:
    text = str(value).strip().casefold()
    text = text.replace("°", " degrees ")
    text = re.sub(r"[`*_{}\[\]()]+", " ", text)
    return re.sub(r"\s+", " ", text).strip(" .,;:!?'\"")


def canonical_answer(value: str) -> str:
    claims = parse_claim_string(value)
    if not claims:
        return normalize_scalar(value)
    return ";".join(
        f"{normalize_scalar(key)}={normalize_scalar(answer)}"
        for key, answer in sorted(claims.items())
    )


SET_LIKE_LIST_FIELDS = {
    "attributes_changed_together",
    "flat_edge_neighbours",
    "hole_directions",
}
ORDERED_LIST_FIELDS = {
    "depth_ordering",
    "height_ordering_shortest_to_tallest",
}
UNORDERED_STRUCTURED_FIELDS = {"connectivity"}
PAIR_FIELDS = {"closest_pair", "farthest_pair"}


def _plain_value(value: Any) -> str:
    text = normalize_scalar(value).replace("<", "").replace(">", "")
    # Identifier-style separators do not change an open-ended answer's
    # meaning (`constant_factor`, `lowest_failing_joint`, and similar forms).
    text = text.replace("_", " ")
    text = re.sub(r"\s+", " ", text).strip()
    aliases = {
        "neither": "none",
        "non unique": "not unique",
        "non-unique": "not unique",
        "nonunique": "not unique",
        "counter clockwise": "counterclockwise",
        "counter-clockwise": "counterclockwise",
        "greater than": "greater",
        "less than": "less",
        "triangular": "triangle",
    }
    text = aliases.get(text, text)
    rotational = re.fullmatch(r"rotational[\s_-]*(\d+)[\s_-]*(?:fold)?", text)
    if rotational:
        return f"rotational {rotational.group(1)}"
    rotational = re.fullmatch(r"(\d+)[\s_-]*fold[\s_-]*rotational", text)
    if rotational:
        return f"rotational {rotational.group(1)}"
    if text in {"triangle", "square", "pentagon"}:
        return text + "s"
    return text


def _jsonish(value: Any) -> Any | None:
    text = str(value).strip()
    for parser in (json.loads, ast.literal_eval):
        try:
            parsed = parser(text)
        except (ValueError, SyntaxError, json.JSONDecodeError):
            continue
        if isinstance(parsed, (dict, list)):
            return parsed
    return None


def _normal_structured(value: Any, unordered_lists: bool = False) -> Any:
    if isinstance(value, dict):
        return (
            "dict",
            tuple(sorted(
                (_plain_value(key), _normal_structured(item, unordered_lists))
                for key, item in value.items()
            )),
        )
    if isinstance(value, list):
        items = [_normal_structured(item, unordered_lists) for item in value]
        return ("list", tuple(sorted(items, key=repr) if unordered_lists else items))
    return ("scalar", _plain_value(value))


def _simple_sequence(value: Any) -> list[str] | None:
    parsed = _jsonish(value)
    if isinstance(parsed, list) and not any(isinstance(item, (dict, list)) for item in parsed):
        return [_plain_value(item) for item in parsed]
    text = str(value).strip().strip("[](){} ").replace('"', "").replace("'", "")
    text = re.sub(r"\s+and\s+|\s*\+\s*|\s*[<>]\s*", ",", text, flags=re.IGNORECASE)
    items = [_plain_value(item) for item in text.split(",") if _plain_value(item)]
    return items or None


def _time_value(value: Any) -> tuple[int, int] | None:
    match = re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*", str(value))
    if not match:
        return None
    hour, minute = map(int, match.groups())
    return (hour, minute) if 1 <= hour <= 12 and 0 <= minute <= 59 else None


def _numeric_value(value: Any) -> Decimal | None:
    text = _plain_value(value)
    text = text.rstrip("°").strip()
    text = re.sub(r"^(?:row|column|position|slot)\s+", "", text)
    text = re.sub(
        r"\s*(?:degrees?|deg|bar|rpm|metres?|meters?|m)\s*$",
        "",
        text,
    ).strip()
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def _pair_value(value: Any) -> tuple[str, str] | None:
    letters = re.findall(r"\b[a-d]\b", _plain_value(value))
    if not letters:
        compact = re.fullmatch(r"([a-d])([a-d])", _plain_value(value))
        letters = list(compact.groups()) if compact else []
    if len(letters) != 2:
        return None
    return tuple(sorted(letters))


def _coordinate_value(value: Any) -> tuple[tuple[str, tuple[Decimal, Decimal]], ...] | None:
    parsed = _jsonish(value)
    if isinstance(parsed, dict):
        points: list[tuple[str, tuple[Decimal, Decimal]]] = []
        for key, coordinates in parsed.items():
            if not isinstance(coordinates, (list, tuple)) or len(coordinates) != 2:
                return None
            try:
                point = (Decimal(str(coordinates[0])), Decimal(str(coordinates[1])))
            except InvalidOperation:
                return None
            points.append((_plain_value(key), point))
        return tuple(sorted(points))
    matches = re.findall(
        r"\b([A-Da-d])\b\s*[:=]?\s*[\[(]?\s*(-?\d+(?:\.\d+)?)\s*,\s*"
        r"(-?\d+(?:\.\d+)?)\s*[\])]??",
        str(value),
    )
    if not matches:
        return None
    return tuple(sorted(
        (_plain_value(label), (Decimal(x), Decimal(y)))
        for label, x, y in matches
    ))


def _stability_value(value: Any) -> dict[str, str] | None:
    parsed = _jsonish(value)
    if isinstance(parsed, dict):
        return {_plain_value(key): _plain_value(item) for key, item in parsed.items()}
    text = _plain_value(value)
    status_match = re.search(r"\b(stable|stands|tips)\b", text)
    joint_match = re.search(
        r"lowest[\s_-]+fail(?:ing|ure)[\s_-]+joint\s*=\s*([a-f])\b",
        text,
    )
    if not status_match:
        return None
    status = "stable" if status_match.group(1) in {"stable", "stands"} else "tips"
    joint = joint_match.group(1) if joint_match else ""
    if not joint and status == "tips":
        on_match = re.search(r"\b([a-z])\s*-?\s*on\s*-?\s*([a-z])\b", text)
        pair_match = re.search(r"\b([a-z])\s*[-–—/]\s*([a-z])\b", text)
        between_match = re.search(
            r"\bbetween\s+(?:block\s+)?([a-z])\s+and\s+(?:block\s+)?([a-z])\b",
            text,
        )
        compact_pair_match = re.search(r"\b([A-F])([A-F])\b", str(value))
        if on_match:
            joint = on_match.group(1)
        elif pair_match:
            joint = pair_match.group(2)
        elif between_match:
            joint = between_match.group(2)
        elif compact_pair_match:
            joint = compact_pair_match.group(2).casefold()
    if not joint and status == "stable":
        joint = "none"
    if not joint:
        return None
    return {"status": status, "lowest failing joint": joint}


def _magnitude_ranking_value(value: Any) -> tuple[tuple[str, ...], ...] | None:
    parsed = _jsonish(value)
    if isinstance(parsed, list) and all(isinstance(level, list) for level in parsed):
        # Outer order is the ranking; labels inside one tied level are an unordered set.
        return tuple(tuple(sorted(_plain_value(label) for label in level)) for level in parsed)
    # Preserve the comparison operators until the ranking levels and ties
    # have been separated. `_plain_value` removes angle brackets for ordinary
    # scalar answers, which would collapse A > B.
    text = normalize_scalar(value)
    levels = re.split(r"\s*>\s*", text)
    if not levels:
        return None
    ranking: list[tuple[str, ...]] = []
    for level in levels:
        # Models may repeat the visually estimated magnitude after a label,
        # e.g. `W (195.4 N) > N (160.8 N)` or `W=198.6 N`. Magnitudes are
        # explanatory annotations; the graded value is the label ranking.
        labels = re.findall(r"(?:^|=)\s*([afntw])\b", level)
        if labels:
            tied = tuple(sorted(labels))
        else:
            tied = tuple(sorted(
                _plain_value(label)
                for label in re.split(r"\s*=\s*", level)
                if _plain_value(label)
            ))
        if not tied:
            return None
        ranking.append(tied)
    return tuple(ranking)


def _value_equivalent(field: str, actual: Any, expected: Any) -> bool:
    actual_text, expected_text = _plain_value(actual), _plain_value(expected)
    if field in {"constructible", "peak_above_13_m"}:
        boolean_aliases = {"true": "yes", "false": "no"}
        actual_text = boolean_aliases.get(actual_text, actual_text)
        expected_text = boolean_aliases.get(expected_text, expected_text)
    elif field == "light_direction":
        actual_text = actual_text.replace("-", " ")
        expected_text = expected_text.replace("-", " ")
        direction_aliases = {
            "left": "west",
            "from left": "west",
            "from the left": "west",
            "upper left": "west",
            "from the upper left": "west",
            "right": "east",
            "from right": "east",
            "from the right": "east",
            "upper right": "east",
            "from the upper right": "east",
        }
        actual_text = direction_aliases.get(actual_text, actual_text)
        expected_text = direction_aliases.get(expected_text, expected_text)
        if re.match(r"^(?:from (?:the )?)?(?:upper |front |behind )?left\b", actual_text):
            actual_text = "west"
        elif re.match(r"^(?:from (?:the )?)?(?:upper |front |behind )?right\b", actual_text):
            actual_text = "east"
    elif field == "light_height":
        height_aliases = {
            "high in the sky": "high",
            "high above the horizon": "high",
            "low near the horizon": "low",
            "low on the horizon": "low",
        }
        actual_text = height_aliases.get(actual_text, actual_text)
        expected_text = height_aliases.get(expected_text, expected_text)
        if actual_text.startswith("low near horizon"):
            actual_text = "low"
        elif actual_text.startswith("high in sky") or actual_text.startswith("moderately high"):
            actual_text = "high"
    elif field == "larger_angle":
        actual_text = re.sub(r"^angle\s+", "", actual_text)
        expected_text = re.sub(r"^angle\s+", "", expected_text)
    elif field == "shrink_pattern":
        shrink_aliases = {
            "same": "constant",
            "uniform": "constant",
            "same factor": "constant",
            "constant factor": "constant",
            "roughly same factor": "constant",
            "roughly the same factor": "constant",
            "roughly equal factor": "constant",
            "approximately the same factor": "constant",
            "roughly constant factor": "constant",
            "roughly constant": "constant",
        }
        actual_text = shrink_aliases.get(actual_text, actual_text)
        expected_text = shrink_aliases.get(expected_text, expected_text)
    elif field == "uniqueness":
        uniqueness_aliases = {
            "false": "not unique",
            "multiple": "not unique",
            "true": "unique",
        }
        actual_text = uniqueness_aliases.get(actual_text, actual_text)
        expected_text = uniqueness_aliases.get(expected_text, expected_text)
    elif field == "pattern_status":
        status_aliases = {
            "symmetric": "fully symmetric",
            "perfectly symmetric": "fully symmetric",
            "fully symmetrical": "fully symmetric",
            "asymmetric": "broken",
            "not fully symmetric": "broken",
            "one displaced": "broken",
            "one element displaced": "broken",
            "displaced": "broken",
        }
        actual_text = status_aliases.get(actual_text, actual_text)
        expected_text = status_aliases.get(expected_text, expected_text)
    elif field == "pattern_type":
        pattern_aliases = {
            "circular": "circle",
            "circular pattern": "circle",
            "circular ring": "circle",
            "rectangular grid": "grid",
            "regular rectangular grid": "grid",
            "regular grid": "grid",
            "triangular grid": "triangles",
            "triangular arrangement": "triangles",
            "triangular lattice": "triangles",
            "triangular array": "triangles",
        }
        actual_text = pattern_aliases.get(actual_text, actual_text)
        expected_text = pattern_aliases.get(expected_text, expected_text)
        if re.fullmatch(r"\d+x\d+\s+grid", actual_text):
            actual_text = "grid"
        if re.fullmatch(r"\d+x\d+\s+grid", expected_text):
            expected_text = "grid"
        if re.fullmatch(r"(?:regular\s+)?\d+(?:x|\s+by\s+)\d+\s+(?:rectangular\s+)?grid", actual_text):
            actual_text = "grid"
        if re.fullmatch(r"(?:regular\s+)?\d+(?:x|\s+by\s+)\d+\s+(?:rectangular\s+)?grid", expected_text):
            expected_text = "grid"
        # Square/rectangular lattices are the dataset's grid class. A
        # triangular grid remains the distinct triangle class above.
        if re.search(r"\b(?:square|rectangular)\s+grid\b", actual_text):
            actual_text = "grid"
        if re.search(r"\b(?:square|rectangular)\s+grid\b", expected_text):
            expected_text = "grid"
        if actual_text.startswith(("circle ", "circular ring")) or (
            "ring" in actual_text and actual_text.startswith(("octagon ", "hexagon "))
        ):
            actual_text = "circle"
        if actual_text.startswith(("right triangle", "triangular grid", "pyramid ")):
            actual_text = "triangles"
    elif field == "convexity":
        convexity_aliases = {"concave": "non-convex", "not convex": "non-convex"}
        actual_text = convexity_aliases.get(actual_text, actual_text)
        expected_text = convexity_aliases.get(expected_text, expected_text)
    elif field == "symmetry_type":
        actual_text = re.sub(r"^bilateral\s+", "", actual_text)
        expected_text = re.sub(r"^bilateral\s+", "", expected_text)
        symmetry_aliases = {
            "180 rotational": "rotational 2",
            "180 degree rotational symmetry": "rotational 2",
            "180-degree rotational symmetry": "rotational 2",
            "reflection symmetry about a vertical axis": "mirror vertical",
            "reflection symmetry about the vertical axis": "mirror vertical",
            "reflection symmetry across a vertical axis": "mirror vertical",
            "reflectional symmetry about a vertical axis": "mirror vertical",
            "reflectional symmetry about the vertical axis": "mirror vertical",
            "mirror symmetry about a vertical axis": "mirror vertical",
            "vertical reflection symmetry": "mirror vertical",
            "reflection symmetry about a horizontal axis": "mirror horizontal",
            "reflection symmetry about the horizontal axis": "mirror horizontal",
            "reflection symmetry across a horizontal axis": "mirror horizontal",
            "reflectional symmetry about a horizontal axis": "mirror horizontal",
            "mirror symmetry about a horizontal axis": "mirror horizontal",
            "horizontal reflection symmetry": "mirror horizontal",
        }
        actual_text = symmetry_aliases.get(actual_text, actual_text)
        expected_text = symmetry_aliases.get(expected_text, expected_text)
        actual_fold = re.search(r"\b(\d+)\s*-?fold\s+rotational\b", actual_text)
        expected_fold = re.search(r"\b(\d+)\s*-?fold\s+rotational\b", expected_text)
        if actual_fold:
            actual_text = f"rotational {actual_fold.group(1)}"
        if expected_fold:
            expected_text = f"rotational {expected_fold.group(1)}"
        if "point symmetry" in actual_text and "180" in actual_text:
            actual_text = "rotational 2"
        if "point symmetry" in expected_text and "180" in expected_text:
            expected_text = "rotational 2"
        if "vertical" in actual_text and re.search(r"reflection|mirror", actual_text):
            actual_text = "mirror vertical"
        if "horizontal" in actual_text and re.search(r"reflection|mirror", actual_text):
            actual_text = "mirror horizontal"
        for order in range(2, 13):
            phrases = {
                f"rotational symmetry order {order}",
                f"rotational symmetry of order {order}",
                f"rotational symmetry (order {order})",
            }
            if actual_text in phrases:
                actual_text = f"rotational {order}"
            if expected_text in phrases:
                expected_text = f"rotational {order}"
    elif field == "true_size_relation":
        size_aliases = {
            "a=b": "equal",
            "a equals b": "equal",
            "a is larger": "a",
            "a larger than b": "a",
            "b is larger": "b",
            "b larger than a": "b",
        }
        actual_text = size_aliases.get(actual_text, actual_text)
        expected_text = size_aliases.get(expected_text, expected_text)
        actual_text = re.sub(r"\s+larger$", "", actual_text)
        expected_text = re.sub(r"\s+larger$", "", expected_text)
    elif field == "fastest_gear":
        actual_text = re.sub(r"^gear\s+", "", actual_text)
        expected_text = re.sub(r"^gear\s+", "", expected_text)
    elif field == "direction_target":
        actual_text = re.sub(r"^gear\s+", "", actual_text)
        expected_text = re.sub(r"^gear\s+", "", expected_text)
    elif field == "target_direction_relation":
        relation_aliases = {
            "same as driver": "same",
            "same as the driver": "same",
            "opposite to driver": "opposite",
            "opposite to the driver": "opposite",
        }
        actual_text = relation_aliases.get(actual_text, actual_text)
        expected_text = relation_aliases.get(expected_text, expected_text)
    elif field == "range_half":
        half_aliases = {"upper half": "upper", "lower half": "lower"}
        actual_text = half_aliases.get(actual_text, actual_text)
        expected_text = half_aliases.get(expected_text, expected_text)
    elif field == "orientability":
        orientability_aliases = {
            "nonorientable": "non-orientable",
            "yes": "orientable",
            "no": "non-orientable",
        }
        actual_text = orientability_aliases.get(actual_text, actual_text)
        expected_text = orientability_aliases.get(expected_text, expected_text)
    elif field == "relation_to_12":
        actual_text = re.sub(r"\s+than\s+12(?:\s+units?)?$", "", actual_text)
        expected_text = re.sub(r"\s+than\s+12(?:\s+units?)?$", "", expected_text)
    elif field == "face_shapes":
        shape_words = {"triangles", "squares", "pentagons", "hexagons", "quadrilaterals"}
        actual_shapes = {word for word in shape_words if re.search(rf"\b{word}\b", actual_text)}
        expected_shapes = {word for word in shape_words if re.search(rf"\b{word}\b", expected_text)}
        if expected_text == "mixed" and len(actual_shapes) >= 2:
            actual_text = "mixed"
        if actual_text == "mixed" and len(expected_shapes) >= 2:
            expected_text = "mixed"
        for shape in ("triangles", "squares", "pentagons"):
            singular = shape[:-1]
            if expected_text == shape and re.search(rf"\b{singular}s?\b", actual_text):
                other = {word for word in shape_words if word != shape and re.search(rf"\b{word}\b", actual_text)}
                if not other:
                    actual_text = shape
    if actual_text == expected_text:
        return True
    if field == "rejection_reason":
        if actual_text.startswith(expected_text + " "):
            return True
        rejection_evidence = {
            "wrong cell count": r"\b(?:too few|too many|wrong (?:cell|square|cube) count|only \d+ .{0,30} total)\b",
            "requires being flipped over": r"\b(?:mirror(?:ed| image)?|flip(?:ped|ping)?|reflection)\b",
            "requires turning about a forbidden axis": r"\b(?:forbidden axis|upright axis|vertical axis|tumble|flat .{0,30} upright)\b",
            "gap or overlap": r"\b(?:gap|overlap|cannot be arranged|cannot fit|cannot reproduce .{0,40} outline)\b",
        }
        pattern = rejection_evidence.get(expected_text)
        if pattern and re.search(pattern, actual_text):
            return True
    actual_time, expected_time = _time_value(actual), _time_value(expected)
    if actual_time is not None and expected_time is not None:
        return actual_time == expected_time
    actual_number, expected_number = _numeric_value(actual), _numeric_value(expected)
    if actual_number is not None and expected_number is not None:
        return actual_number == expected_number
    if field in PAIR_FIELDS:
        actual_pair, expected_pair = _pair_value(actual), _pair_value(expected)
        return actual_pair is not None and actual_pair == expected_pair
    if field == "point_coordinates":
        actual_points, expected_points = _coordinate_value(actual), _coordinate_value(expected)
        return actual_points is not None and actual_points == expected_points
    if field == "stability_conclusion":
        actual_stability, expected_stability = _stability_value(actual), _stability_value(expected)
        return actual_stability is not None and actual_stability == expected_stability
    if field == "drawn_magnitude_ranking":
        actual_ranking = _magnitude_ranking_value(actual)
        expected_ranking = _magnitude_ranking_value(expected)
        return actual_ranking is not None and actual_ranking == expected_ranking
    if field in SET_LIKE_LIST_FIELDS | ORDERED_LIST_FIELDS:
        actual_items, expected_items = _simple_sequence(actual), _simple_sequence(expected)
        if actual_items is None or expected_items is None:
            return False
        if field == "hole_directions":
            actual_items = [] if actual_items == ["none"] else actual_items
            expected_items = [] if expected_items == ["none"] else expected_items
        if field == "attributes_changed_together":
            prose = _plain_value(actual)
            concept_patterns = {
                "color": r"\b(?:colou?r|hue)\b",
                "count": r"\b(?:count|number|quantity)\b",
                "rotation": r"\b(?:rotation|orientation|tilt|pointing|upright|downward|left-pointing|right-pointing)\b",
                "shape": r"\b(?:shape|sides?)\b",
                "size": r"\b(?:size|scale|small|medium|large)\b",
            }
            attribute_aliases = {
                "orientation": "rotation",
                "star orientation": "rotation",
                "rotation angle": "rotation",
                "shape type": "shape",
                "item count": "count",
                "number": "count",
                "number of dots": "count",
                "number of stars": "count",
                "number of shapes": "count",
                "shape count": "count",
                "shape size": "size",
                "size of triangles": "size",
                "star count": "count",
            }
            def normal_attribute(item: str) -> str:
                item = re.sub(r"\s+(?:rows?|columns?)$", "", item).strip()
                return attribute_aliases.get(item, item)
            actual_items = [normal_attribute(item) for item in actual_items]
            expected_items = [normal_attribute(item) for item in expected_items]
            mentioned = {
                name for name, pattern in concept_patterns.items()
                if re.search(pattern, prose)
            }
            if set(expected_items).issubset(mentioned):
                return True
        if field in ORDERED_LIST_FIELDS:
            colour_aliases = {"pink": "magenta", "cyan": "teal", "green": "teal"}
            actual_items = [re.sub(r"\s*\([^)]*\)\s*$", "", item) for item in actual_items]
            actual_items = [re.sub(r"\s+-?\d+(?:\.\d+)?\s*$", "", item) for item in actual_items]
            actual_items = [
                re.sub(r"\s+(?:closest|farthest|triangle|square|circle)\s*$", "", item)
                for item in actual_items
            ]
            actual_items = [colour_aliases.get(item, item) for item in actual_items]
            expected_items = [colour_aliases.get(item, item) for item in expected_items]
        if field in SET_LIKE_LIST_FIELDS:
            return sorted(actual_items) == sorted(expected_items)
        return actual_items == expected_items
    actual_json, expected_json = _jsonish(actual), _jsonish(expected)
    if actual_json is not None and expected_json is not None:
        unordered = field in UNORDERED_STRUCTURED_FIELDS
        return _normal_structured(actual_json, unordered) == _normal_structured(expected_json, unordered)
    return False


def _extract_expected_claims(answer: str, fields: list[str]) -> dict[str, str]:
    # Extract up to the next recognised field assignment rather than splitting
    # blindly at every semicolon. Free-form claim values may themselves use a
    # semicolon, as in `tips; first fails at C-D`.
    alternatives = "|".join(map(re.escape, fields))
    extracted: dict[str, str] = {}
    for field in fields:
        match = re.search(
            rf"(?is)(?:^|[;,\n])\s*`?{re.escape(field)}`?\s*=\s*(.*?)"
            rf"(?=\s*(?:[;,\n])\s*`?(?:{alternatives})`?\s*=|$)",
            answer,
        )
        if match:
            extracted[field] = match.group(1).strip().strip("`")
    return extracted


def answer_is_accepted(answer: str | None, acceptance_set: str) -> bool:
    if answer is None:
        return False
    actual = canonical_answer(answer)
    candidates = json_list(acceptance_set)
    if any(actual == canonical_answer(candidate) for candidate in candidates):
        return True
    for candidate in candidates:
        expected = parse_claim_string(candidate)
        observed = _extract_expected_claims(answer, list(expected))
        if set(observed) != set(expected):
            continue
        if all(_value_equivalent(field, observed[field], expected[field]) for field in expected):
            return True
    return False


def extract_line(raw: str, label: str) -> str | None:
    cleaned = str(raw).replace("**", "").replace("__", "")
    match = re.search(rf"(?im)^\s*{re.escape(label)}\s*:\s*(.*?)\s*$", cleaned)
    return match.group(1).strip() if match else None


def extract_section(raw: str, label: str, following: tuple[str, ...]) -> str | None:
    cleaned = str(raw).replace("**", "").replace("__", "")
    stops = "|".join(re.escape(item) for item in following)
    pattern = rf"(?ims)^\s*{re.escape(label)}\s*:\s*(.*?)(?=^\s*(?:{stops})\s*:|\Z)"
    match = re.search(pattern, cleaned)
    return match.group(1).strip() if match else None


def parse_confidence(raw: str) -> float | None:
    value = extract_line(raw, "CONFIDENCE")
    if value is None or not re.fullmatch(r"(?:0(?:\.\d+)?|1(?:\.0+)?)", value):
        return None
    result = float(value)
    return result if 0 <= result <= 1 else None


def parse_changed(raw: str) -> bool | None:
    value = extract_line(raw, "CHANGED")
    if value is None:
        return None
    normalized = normalize_scalar(value)
    return True if normalized == "yes" else False if normalized == "no" else None


def response_parts(raw: str, round2: bool = False) -> dict[str, Any]:
    following = ("JUSTIFICATION", "CONFIDENCE", "CHANGED")
    answer = extract_section(raw, "ANSWER", following)
    if answer is None:
        # Recover a complete field=value answer when the model omitted only
        # the `ANSWER:` heading but otherwise followed the requested layout.
        prefix = re.split(r"(?im)^\s*(?:JUSTIFICATION|CONFIDENCE|CHANGED)\s*:", str(raw), maxsplit=1)[0]
        prefix = prefix.replace("**", "").replace("__", "").strip()
        if re.match(r"^[a-z][a-z0-9_]*\s*=", prefix, flags=re.IGNORECASE):
            answer = prefix
    justification = extract_section(raw, "JUSTIFICATION", ("CONFIDENCE", "CHANGED"))
    return {
        "answer": answer,
        "justification": justification,
        "confidence": parse_confidence(raw),
        "changed": parse_changed(raw) if round2 else None,
        "parse_ok": answer is not None,
    }


def claims_from_key_row(row: dict[str, Any]) -> dict[str, str]:
    return {
        str(key): str(value).strip()
        for key, value in row.items()
        if key not in META_COLUMNS and str(value).strip()
    }


def checkable_claims(row: dict[str, Any], vocab: dict[str, list[str]]) -> str:
    claims = []
    for field, expected in claims_from_key_row(row).items():
        claims.append({
            "field": field,
            "expected": expected,
            "alternatives": [x for x in vocab.get(field, []) if x != expected],
        })
    return json.dumps(claims, ensure_ascii=False, separators=(",", ":"))


def load_jsonl_latest(path: Path, model: str | None = None) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    if not path.is_file():
        return records
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON at {path}:{line_number}: {error}") from error
            if model and record.get("model") not in (None, model):
                raise ValueError(f"Wrong model at {path}:{line_number}")
            row_id = str(record.get("row_id", ""))
            if row_id:
                records[row_id] = record
    return records


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def content_words(text: str) -> set[str]:
    stop = {
        "a", "an", "and", "are", "as", "at", "be", "because", "by", "for", "from",
        "i", "in", "is", "it", "of", "on", "or", "that", "the", "this", "to", "was",
        "with", "answer", "justification", "confidence", "changed",
    }
    return {word for word in re.findall(r"[a-z0-9]+", str(text).casefold()) if len(word) > 2 and word not in stop}


def jaccard(left: str, right: str) -> float:
    a, b = content_words(left), content_words(right)
    return len(a & b) / len(a | b) if a or b else 0.0
