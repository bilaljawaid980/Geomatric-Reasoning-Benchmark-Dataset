# GRIP Analog Clock Reading Dataset 3000

## 1. Overview

This is the third entry in GRIP-Benchmark's **Physical/Mechanical Reasoning** family. It tests exact analog-clock perception, continuous hour-hand motion, hand-angle calculation, and time-advance counterfactuals.

Analog-clock understanding is a documented vision-language weakness. Choi et al.'s [*It's Time to Get It Right*](https://arxiv.org/abs/2603.08011) reports frequent hour/minute-hand confusion and weak exact-time reading in current VLMs. Yang, Xie, and Zisserman's [*It's About Time: Analog Clock Reading in the Wild*](https://arxiv.org/abs/2111.09162) established synthetic-to-real clock recognition and minute-accurate clock benchmarks. These are independent related works; their authors are not affiliated with this dataset.

## 2. Contents

- 3,000 deterministic 600 x 600 RGB clock diagrams
- 15,000 questions, exactly five ordered levels per image
- Exact fractional hand angles and smaller-angle values in `annotations.jsonl`
- `question_set.csv`, private `answer_key.csv`, flattened CSV/JSONL
- PNG-aware independent validator, statistics, tests, and review sheets

## 3. Five-level questions

1. **Simple Description:** identify the hour most recently passed by the creeping short hand.
2. **Basic Relational:** determine whether the minute hand is before or after the 6.
3. **Comparative/Structural:** read the exact time in `HH:MM` format.
4. **Compound Reasoning:** calculate the smaller angle between both hands.
5. **Extrapolative/Counterfactual:** add 20 minutes, handle rollover, recompute both hand positions, and derive the new angle.

The original wording “What hour does the short hand point closest to?” would conflict with the stored hour after half past, because a physically creeping short hand is then closer to the next numeral. Level 1 therefore asks which hour the hand has **most recently passed**. Minute 30 is excluded because a hand exactly on the 6 is neither “before” nor “after”; before/after cases are selected 50/50 by generation parameters. Parameter selection also enforces at least 12° of separation between the two rendered hands so the short hand remains visibly distinguishable.

## 4. Exact physics and generation

```text
minute_angle = minute × 6°
hour_angle = (hour mod 12) × 30° + minute × 0.5°
smaller_angle = min(|hour_angle-minute_angle|, 360°-|hour_angle-minute_angle|)
```

```powershell
python generate_clock_reading_dataset.py --sample
python generate_clock_reading_dataset.py --count 3000
python flatten_annotations.py annotations.jsonl
python make_stats.py
python make_contact_sheet.py
```

Degree answers use conventional half-up rounding, so `7.5°` becomes `8°`. Level 5 converts the time to minutes in a 12-hour cycle, adds 20, applies hour/minute rollover, and recomputes both angles from the new time.

## 5. Independent validation

```powershell
python validate_clock_dataset.py
pytest -q
```

The validator independently recomputes all original and advanced-time angles from stored hour/minute values, re-derives all five answers, and compares every flattened row with its annotation. It also reads every final PNG and checks colored pixels along multiple expected points and endpoints of both rendered hands, catching metadata/rendering or file-association mismatches.

## 6. Reasoning skills

- Distinguishing short and long clock hands
- Continuous hour-hand creep
- Exact time reading
- Circular smaller-angle arithmetic
- Time addition and hour rollover
- Counterfactual angle recomputation

## 7. Limitations

The dataset uses clean front-facing schematic clocks with two hands, fixed typography, and no second hand. It excludes exactly `:30` to keep the binary Level 2 prompt unambiguous and excludes hand separations below 12° to prevent visual occlusion. It does not model perspective, glare, damaged faces, Roman numerals, missing numerals, decorative hands, or real-world backgrounds.

This repository contains generation data and ground truth only. It includes no model inference, evaluation, scoring, or benchmark runner.
