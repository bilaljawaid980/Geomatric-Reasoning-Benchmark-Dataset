# GRIP Analog Gauge Reading Dataset 3000

## Overview

This is the fourth entry in GRIP-Benchmark's **Physical/Mechanical Reasoning** family. It extends analog-clock reading to single-needle instruments with varied labeled ranges and angular sweeps, closer to speedometers, pressure gauges, temperature dials, and general analog meters.

Visual measurement reading is a documented weakness of vision-language models. Lin et al.'s [*Do Vision-Language Models Measure Up? Benchmarking Visual Measurement Reading with MeasureBench*](https://arxiv.org/abs/2510.26865) identifies indicator localization as a recurring failure mode: models may recognize labels while mislocating the pointer and consequently return a large numerical error. The paper is independent related work; its authors are not affiliated with this dataset.

## Contents

- 3,000 deterministic 600 × 600 RGB gauge diagrams
- Five instrument/range configurations across four instrument labels, including PSI and bar pressure gauges plus 180° and 270° sweeps
- 1,200 images with an upper-range danger band (exactly 40%)
- 15,000 questions, exactly five ordered levels per image
- Exact rational needle values, angles, threshold values, and projected values
- Public question_set.csv, private answer_key.csv, raw annotations, tests, statistics, and PNG-aware validation

## Five-level questions

1. **Simple Description:** read the minimum labeled scale value.
2. **Basic Relational:** classify the needle in the lower or upper half of the range.
3. **Comparative/Structural:** interpolate the needle and round to the nearest tick interval.
4. **Compound Reasoning:** combine pointer location and a marked threshold to determine danger-zone status and exceedance.
5. **Extrapolative/Counterfactual:** add 25% of the full range, derive the new value, and determine whether it exceeds the maximum.

Midpoint needle values are excluded because “lower half or upper half” would otherwise be ambiguous. Danger thresholds lie on labeled major ticks, and needle values equal to the threshold are excluded so “exceeds” has an exact interpretation. Half-tick pointer positions make interpolation meaningful rather than reducing every sample to direct label lookup.

## Exact mapping

    fraction_along_scale = (needle_value - min_value) / (max_value - min_value)
    needle_angle = dial_start_angle + fraction_along_scale × dial_sweep_degrees
    projected_value = needle_value + 0.25 × (max_value - min_value)

Angles use a rendering convention of 0° at 12 o'clock and increase clockwise. All generation and validation arithmetic uses exact rational numbers; displayed decimal fields are secondary conveniences.

## Commands

    python generate_gauge_reading_dataset.py --sample
    python flatten_annotations.py sample_test/annotations.jsonl
    python validate_gauge_dataset.py sample_test

    python generate_gauge_reading_dataset.py --count 3000
    python flatten_annotations.py
    python make_stats.py
    python make_contact_sheet.py
    python validate_gauge_dataset.py
    pytest -q

The --sample pass is mandatory before a full regeneration because angle-to-value interpolation is the principal image/label mismatch risk.

## Independent validation

The validator independently reconstructs the angle from the stored value, range, start angle, and sweep. It independently recomputes nearest-tick rounding, danger-zone status, and the 25%-range counterfactual. It also reads every saved PNG, segments the distinct needle color, estimates the rendered endpoint angle and length, samples the expected needle centerline, verifies danger-arc placement, and cross-checks every flattened CSV row against the raw annotations.

## Limitations

These are clean, front-facing schematic dials. They do not model glass reflections, perspective, multiple needles, damaged scales, arbitrary nonlinear tick spacing, or photographic industrial clutter. “Non-uniform range” here means that instruments use different numeric minima, maxima, intervals, units, and angular sweeps; each individual dial still uses a linear calibrated scale.

This repository contains synthetic images and ground truth only. It includes no model inference, scoring, accuracy computation, or evaluation harness.
