# GRIP Laser Mirror Reflection Dataset 3000

This dataset contains 3,000 programmatically generated grid-optics puzzles and 15,000 questions. A single laser enters a 5×5–8×8 grid, reflects from 2–5 diagonal mirrors, and exits at a deterministically simulated boundary position. Images use a clean 500–550 px light-theme renderer. The laser path itself is not drawn; only the entry and actual exit markers are visible.

## Inspiration and scope

The design is directly inspired by Jane Street's [Hall of Mirrors](https://www.janestreet.com/puzzles/hall-of-mirrors-index/) puzzle series and especially the [Hall of Mirrors 3](https://www.janestreet.com/puzzles/hall-of-mirrors-3-index/) constraint that mirrors may not occupy orthogonally adjacent cells. This is a new parameterized adaptation and does not reproduce any published Jane Street puzzle instance.

Unlike `rotation_matching_dataset_3000`, this dataset tests propagation through multiple reflections rather than a single-object transform. Unlike `shadow_inference_dataset_3000`, it tests forward ray tracing rather than inference about an unseen light source.

## Questions

Every image has exactly five questions:

1. mirror count;
2. whether the laser hits a mirror;
3. number of reflections;
4. final exit edge and position;
5. the counterfactual exit after flipping one named mirror by 90 degrees.

## Exact simulation

Cells and positions use one-based indexing. Top/bottom positions increase left-to-right; left/right positions increase top-to-bottom. The reflection table is:

- `/`: right↔up and left↔down;
- `\`: right↔down and left↔up.

Generation rejects an original path if it loops. It also checks every possible one-mirror flip and rejects the scene if any such counterfactual loops. Mirrors are unique, in bounds, and never orthogonally adjacent.

## Files and commands

- `images/laser_mirror_0001.png` … `laser_mirror_3000.png`
- `annotations.jsonl`: complete mirror geometry, paths, exits, counterfactuals, and questions
- `question_set.csv`: public prompts without answers
- `answer_key.csv`: private ground truth and answer formats
- `dataset_final.csv` / `dataset_final.jsonl`: flattened dataset
- `contact_sheet.png`, `review_sheet.png`, `generation_stats.json`, and `stats.md`
- `manual_trace_samples.txt`: human-readable traces for the five deterministic review samples
- `validation_report.txt` / `validation_metrics.json`: independent full-build validation

```powershell
python .\generate_laser_mirror_dataset.py --sample
python .\generate_laser_mirror_dataset.py
python .\validate_laser_mirror_dataset.py
```

The validator contains its own ray simulator and does not import generation logic. It reconstructs every original and Level 5 path, verifies every possible single-mirror flip terminates, checks all question ground truths and flattened tables, confirms public-answer separation, and checks all PNG files.
