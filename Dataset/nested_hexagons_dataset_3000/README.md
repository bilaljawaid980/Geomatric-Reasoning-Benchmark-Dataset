# GRIP Nested Hexagons Dataset 3000 — v8

Version `nested-hexagons-8.0.0` contains 3,000 images and 15,000 questions. V8 occupies the unsuffixed release paths; superseded local builds were removed to keep the repository clean.

## Phase 8 changes

Level 5 now uses the shared 12% outermost-side threshold and rescaled 9.6%–14.4% exclusion band. This threshold follows the v7 empirical review plus the shared worst-case visibility calibration. The v8 result is exactly 1,500 `yes` / 1,500 `no`, with shape-count correlation `0.000000` and an achievable extrapolated-fraction range of 9.30%–16.99%.

The unchanged 15 px inner-size and 3 px clear-background guards remain active. Matched nuisance-rank clearance sampling reduces minimum-clearance Cramér's V to `0.002981`. The definitional whitelist now contains exactly `factor_progression_direction` and `reduction_factor_span`; every other audited scene parameter remains below V=0.10.

All 3,000 PNG outline counts were independently recovered. Every guard injection test passes, Level 4 retains its `0.268293` theoretical baseline and `0.269020` observed capture, and validation reports **PASS — 0 mismatches**. Full distributions and both minimum-clearance rejections are recorded in `validation_report.txt`.
