# GRIP Optical Illusion Dataset 3000

## 1. Overview

This dataset tests perceptual robustness rather than ordinary geometric competence. Each image places two objectively measured targets inside a classic misleading context and asks whether a vision-language model separates apparent size from true pixel geometry. The central research distinction is therefore human-like illusion susceptibility versus measurement-like context immunity.

Level 2 explicitly asks what a **typical human viewer** would perceive under the illusion context. It does not claim that the target pixels differ or penalize accurate measurement; Levels 3–5 retain the true-size frame.

The three families follow the classic Müller-Lyer (1889), Ponzo (1911), and Ebbinghaus/Titchener-circle traditions. This is synthetic data and ground truth only: there is no model inference, scoring, accuracy computation, or evaluation harness.

## 2. Dataset contents

- 3,000 deterministic 500–550 px RGB PNGs on `#FDFAF4`
- 1,050 Müller-Lyer, 1,050 Ponzo, and 900 Ebbinghaus scenes
- Exactly 50% equal and 50% unequal targets inside every illusion family
- Unequal cases split as evenly as integer counts permit between matching and contradicting the contextual suggestion
- Five ordered questions per image, for 15,000 total
- Exact primitive coordinates, exact rational percentage differences, public questions, private answers, statistics, contact sheets, tests, and PNG-aware validation

## 3. Visual construction and exact truth

Müller-Lyer scenes use 38°–48° fins of 36–46 px, around the familiar approximately 45° configuration. Ponzo scenes use two strong converging rails plus transverse depth cues, with one target nearer the convergence. Ebbinghaus scenes use six evenly spaced inducers: small surrounds are 35%–45% of their target diameter and large surrounds are 130%–150%. These configurations are informed by psychophysics designs using angled Müller-Lyer fins, converging Ponzo contours, and six small-versus-large Ebbinghaus inducers ([Franz et al., 2009](https://www.yorku.ca/jdc/Franz_et_al2009_ying_April_2009.pdf), [Plewan et al., 2012](https://pmc.ncbi.nlm.nih.gov/articles/PMC3062603/), [Kaneko et al., 2021](https://pmc.ncbi.nlm.nih.gov/articles/PMC8196426/)).

Target lengths and diameters are stored as integer construction primitives before context is drawn. For unequal cases, the true difference is controlled to approximately 5%–20%. Percentage difference is defined unambiguously as:

    percent_difference = abs(A - B) / min(A, B) × 100

## 4. Unified five-level questions

1. **Simple Description:** count the two comparison targets.
2. **Basic Relational:** identify which target the hard-coded illusion rule predicts will appear larger.
3. **Comparative/Structural:** ignore context and compare true target geometry.
4. **Compound Reasoning:** calculate the rounded true percentage difference.
5. **Extrapolative/Counterfactual:** remove the misleading context conceptually and determine whether the apparent answer changes.

The validator hard-codes the directional rules independently: outward fins suggest longer in Müller-Lyer; the target nearer convergence suggests longer in Ponzo; and smaller surrounding circles make the Ebbinghaus center appear bigger.

## 5. Commands and files

    python generate_optical_illusion_dataset.py --sample
    python flatten_annotations.py sample_test/annotations.jsonl
    python validate_optical_illusion_dataset.py sample_test

    python generate_optical_illusion_dataset.py --count 3000
    python flatten_annotations.py
    python make_stats.py
    python make_contact_sheet.py
    python validate_optical_illusion_dataset.py
    pytest -q test_optical_illusion_dataset.py

Primary outputs are `annotations.jsonl`, `images/`, `dataset_final.csv`, `dataset_final.jsonl`, `question_set.csv`, `answer_key.csv`, `stats.md`, `contact_sheet.png`, `review_sheet.png`, and `validation_report.txt`.

## 6. Independent validation

The validator does not trust stored target values or question answers. It reconstructs line length from saved endpoints and circle diameter from the circle primitive, recalculates equality, true ordering, exact percentage difference, appearance direction, alignment status, and every Level 1–5 answer. It reads every final PNG and checks canvas dimensions, background, nonblank content, and target-colored samples along each expected line or circle outline. It also checks exact dataset balance and every flattened public/private row.

## 7. Related work and limitations

Recent work directly studies whether language-grounded vision systems respond to illusions like humans, including [*Grounding Visual Illusions in Language*](https://aclanthology.org/2023.emnlp-main.348/) and later counterfactual/tool-guided analyses. Psychophysical work confirms that Ebbinghaus apparent size depends on inducer size and distance ([Weintraub et al., 2015](https://pmc.ncbi.nlm.nih.gov/articles/PMC4631937/)) and can influence preattentive visual search ([Busch & Müller, 2004](https://pubmed.ncbi.nlm.nih.gov/15283072/)). These are independent related works; their authors are not affiliated with GRIP.

Limitations: this release covers only three of many documented illusions, samples controlled literature-informed parameter ranges rather than the full psychometric strength space, uses clean two-target diagrams rather than multi-element or photographic scenes, and records the canonical predicted illusion direction rather than collecting human perceptual judgments for each generated instance.
