"""Offline, additive reanalysis. No clients, network calls, or response-file writes."""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import hashlib
import json
import re
from decimal import Decimal
from collections import Counter
from functools import lru_cache
import numpy as np
import pandas as pd
from grip_eval.parsing import parse_answer, compare_answer, parse_jsonish, normalize_approved_equivalent

OUT = ROOT / "analysis"
MODELS = sorted(p.stem.removeprefix("closed_loop_") for p in
                (ROOT / "tests/test_1_closed_loop/results").glob("closed_loop_*.jsonl"))
NAMES = dict(gpt_5_6_luna="GPT-5.6 Luna", gpt_5_6_sol="GPT-5.6 Sol",
             claude_opus_5="Claude Opus 5", claude_sonnet_5="Claude Sonnet 5",
             gemini_3_8_flash="Gemini 3.8 Flash", grok_4_6="Grok 4.6",
             inking="Inkling", muse_glimmer_30b="Muse Glimmer 30B",
             deepseek_v4_1_flash="DeepSeek V4.1 Flash", perplexity_sonar_pro="Perplexity Sonar Pro")
FAMILIES = {
    "Plane Geometry": "nested_squares nested_triangles nested_hexagons line_intersection angle_estimation",
    "Solid Geometry": "cube_net cube_structure combination3d orthographic polyhedron depth_height",
    "Transformational": "rotation_matching symmetry_pattern fold_punch combination embedded_figures overlap_circles",
    "Physical & Mechanical": "physical_stability gear_train fbd projectile_motion laser_mirror clock_reading gauge_reading",
    "Topological": "surface_topology route hex_pathfinding",
    "Projective": "occluded_pattern shadow_inference", "Analytic": "coordinate_geometry compass_bearing",
    "Optical": "optical_illusion impossible_object", "Inductive": "rpm",
}
FAMILY = {domain: family for family, domains in FAMILIES.items() for domain in domains.split()}
INPUTS = {}
PROTECTED = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in
             (ROOT / "tests").rglob("*.md")}

def read_csv(path):
    INPUTS[path] = hashlib.sha256(path.read_bytes()).hexdigest()
    return pd.read_csv(path, dtype=str, keep_default_na=False)

def load_results(path, model):
    raw = path.read_bytes()
    INPUTS[path] = hashlib.sha256(raw).hexdigest()
    latest = {}
    for line in raw.decode("utf-8-sig").splitlines():
        if line.strip():
            r = json.loads(line)
            assert r.get("model", model) == model, path
            latest[r["row_id"]] = r
    return latest

def correct(raw, row, error=None):
    if error:
        return False
    return compare_answer(parse_answer(raw or "", row["answer_format"], row["ground_truth"],
                                      "", row["prompt"]), row["ground_truth"], row["answer_format"], "")

def canonical(value):
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    return normalize_approved_equivalent(value)

def evaluated(manifest, records, model, turn2=False):
    assert not manifest.row_id.duplicated().any(), "Duplicate manifest IDs"
    keyed = {row["row_id"]: row for row in manifest.to_dict("records")}
    unknown = set(records) - set(keyed)
    if unknown:
        raise ValueError(f"Unresolved result IDs for {model}: {sorted(unknown)[:3]}")
    rows = []
    for rid, response in records.items():
        row = dict(keyed[rid])
        row["model"] = model
        row["level"] = int(row["level"])
        if "sigma" in row:
            row["sigma"] = int(row["sigma"])
        raw = response.get("response_raw", "")
        if turn2:
            match = re.search(r"^\s*ANSWER\s*:\s*(.*?)\s*$", raw, re.M | re.I)
            raw = "ANSWER: " + match.group(1) if match else ""
            row["round1_correct_manifest"] = str(row["round1_correct"]).casefold() == "true"
            row["round1_correct"] = correct(response.get("round1_response_raw", ""), row)
            before = parse_answer(response.get("round1_response_raw", ""), row["answer_format"], row["ground_truth"], "", row["prompt"])
            after = parse_answer(raw, row["answer_format"], row["ground_truth"], "", row["prompt"])
            row["actual_changed"] = canonical(before.value) != canonical(after.value) if before.parse_ok and after.parse_ok and not response.get("error") else None
        row["correct"] = correct(raw, row, response.get("error"))
        rows.append(row)
    return pd.DataFrame(rows)

@lru_cache(maxsize=10000)
def baseline_for(signature):
    """Mode under the existing comparator, including JSON acceptance sets."""
    candidates = set()
    targets = Counter(signature)
    for gt, fmt, prompt in targets:
        spec = parse_jsonish(fmt)
        accepted = spec.get("acceptance_set") if isinstance(spec, dict) else None
        candidates.update(map(str, accepted)) if accepted else candidates.add(gt)
    best_count, best = -1, ""
    for candidate in sorted(candidates):
        count = sum(frequency * correct("ANSWER: " + candidate,
                            dict(ground_truth=gt, answer_format=fmt, prompt=prompt))
                    for (gt, fmt, prompt), frequency in targets.items())
        if count > best_count:
            best_count, best = count, candidate
    # Every truth must have at least one accepted exact response.
    for gt, fmt, prompt in targets:
        spec = parse_jsonish(fmt)
        accepted = spec.get("acceptance_set") if isinstance(spec, dict) else None
        candidate = str(accepted[0]) if accepted else gt
        assert correct("ANSWER: " + candidate, dict(ground_truth=gt, answer_format=fmt, prompt=prompt)), (gt, fmt)
    return best_count, best

def cells(frame, keys):
    rows = []
    for values, group in frame.groupby(keys, sort=True):
        if not isinstance(values, tuple):
            values = (values,)
        signature = tuple(sorted(zip(group.ground_truth, group.answer_format, group.prompt)))
        expected, modal = baseline_for(signature)
        n, count = len(group), int(group.correct.sum())
        baseline, accuracy = expected / n, count / n
        rows.append(dict(zip(keys, values)) | dict(n=n, correct_count=count,
                    baseline_expected_correct=expected, baseline=baseline,
                    raw_accuracy=accuracy, adjusted_score=(count-expected)/(n-expected) if expected<n else None,
                    modal_ground_truth=modal, excluded_constant=expected == n, small_n=n<10))
    return pd.DataFrame(rows)

def aggregate(cell_frame, keys):
    rows = []
    for values, group in cell_frame.groupby(keys, sort=True):
        if not isinstance(values, tuple):
            values = (values,)
        for include_small in (True, False):
            valid = group.loc[~group.excluded_constant & (include_small | ~group.small_n)]
            n = int(valid.n.sum())
            for method in ("MACRO", "POOLED"):
                baseline = valid.baseline.mean() if method == "MACRO" else valid.baseline_expected_correct.sum()/n if n else np.nan
                raw = valid.raw_accuracy.mean() if method == "MACRO" else valid.correct_count.sum()/n if n else np.nan
                adjusted = valid.adjusted_score.mean() if method == "MACRO" else (raw-baseline)/(1-baseline) if n else np.nan
                rows.append(dict(zip(keys, values)) | dict(method=method, include_small_n=include_small,
                    n=n, baseline=baseline, raw_accuracy=raw, adjusted_score=adjusted,
                    excluded_constant=n == 0, small_n=bool(valid.small_n.any()), cells=len(valid),
                    excluded_constant_cells=int(group.excluded_constant.sum()),
                    n_all_cells=int(group.n.sum()), raw_accuracy_all_cells=group.correct_count.sum()/group.n.sum()))
    return pd.DataFrame(rows)

def save(frame, name):
    frame.to_csv(OUT / name, index=False)

def table(frame):
    def value(v):
        if pd.isna(v): return "undefined"
        if isinstance(v, (float, np.floating)): return f"{v:.6f}"
        return str(v).replace("|", "\\|").replace("\n", " ")
    return "| " + " | ".join(frame.columns) + " |\n|" + "|".join("---" for _ in frame.columns) + "|\n" + "\n".join(
        "| " + " | ".join(value(v) for v in row) + " |" for row in frame.itertuples(index=False, name=None))

def bootstrap_difference(left, right, left_cells, right_cells, model, label):
    """Stratified IMAGE cluster bootstrap, baselines fixed to evaluated GT cells.

    One multiplicity per image is shared across every included question/level.
    Conditional empirical-baseline CI: baseline-estimation uncertainty is not included.
    """
    index_left = left_cells.set_index(["domain", "level"])
    index_right = right_cells.set_index(["domain", "level"])
    pair_keys = set(index_left.index) & set(index_right.index)
    pair_keys = sorted(k for k in pair_keys if not index_left.loc[k].excluded_constant
                       and not index_right.loc[k].excluded_constant)
    seed = int.from_bytes(hashlib.sha256((model+label).encode()).digest()[:8], "big")
    rng = np.random.default_rng(seed)
    draws = np.zeros(10000)
    domain_draws = {}
    for domain in sorted({k[0] for k in pair_keys}):
        a, b = left[left.domain == domain], right[right.domain == domain]
        stems = sorted(set(a.stem) | set(b.stem))
        lookup = {s: i for i, s in enumerate(stems)}
        weights = rng.multinomial(len(stems), np.full(len(stems), 1/len(stems)), size=10000)
        domain_diff = np.zeros(10000)
        domain_keys = [k for k in pair_keys if k[0] == domain]
        for key in domain_keys:
            adjusted = []
            for frame, meta in ((a, index_left.loc[key]), (b, index_right.loc[key])):
                group = frame[frame.level == key[1]]
                ns, cs = np.zeros(len(stems)), np.zeros(len(stems))
                for row in group.itertuples():
                    ns[lookup[row.stem]] += 1
                    cs[lookup[row.stem]] += row.correct
                totals = np.einsum("ij,j->i", weights, ns, optimize=False)
                counts = np.einsum("ij,j->i", weights, cs, optimize=False)
                acc = np.divide(counts, totals, out=np.full(10000, np.nan), where=totals>0)
                adjusted.append((acc-meta.baseline)/(1-meta.baseline))
            domain_diff += adjusted[1]-adjusted[0]
        draws += domain_diff
        domain_draws[domain] = np.nanquantile(domain_diff/len(domain_keys), [.025, .975])
    return (np.nanquantile(draws/len(pair_keys), [.025, .975]) if pair_keys else [np.nan, np.nan]), domain_draws

def main():
    manifest = read_csv(ROOT / "tests/test_1_closed_loop/plan/closed_loop_manifest.csv")
    manifest["level"] = manifest.level.astype(int)
    frames, item_sets = [], []
    for model in MODELS:
        response = load_results(ROOT / f"tests/test_1_closed_loop/results/closed_loop_{model}.jsonl", model)
        frame = evaluated(manifest, response, model)
        frames.append(frame)
        item_sets.append(dict(model=model, n=len(frame), item_set_hash=hashlib.sha256("\n".join(sorted(response)).encode()).hexdigest()))
    closed = pd.concat(frames, ignore_index=True)
    c = cells(closed, ["model", "domain", "level"])
    c["family"] = c.domain.map(FAMILY)
    assert c.family.notna().all()
    save(c, "adjusted_scores.csv")
    sets = pd.DataFrame(item_sets)
    sets["same_as_first_model"] = sets.item_set_hash.eq(sets.iloc[0].item_set_hash)
    save(sets, "evaluated_item_sets.csv")
    baseline_columns = ["domain", "level", "n", "baseline", "modal_ground_truth", "excluded_constant", "small_n"]
    # A single domain/level row is valid only if the model-specific baselines agree.
    baselines = c[baseline_columns].drop_duplicates()
    assert not baselines.duplicated(["domain", "level"]).any(), "Differing baselines: emit model-specific baselines instead"
    baselines["raw_accuracy"] = np.nan  # Baseline-only table: no model accuracy is applicable.
    baselines["adjusted_score"] = np.nan
    save(baselines, "baselines.csv")
    constants = baselines[baselines.excluded_constant]
    save(constants, "structurally_constant_cells.csv")
    aggs = {}
    for name, keys in (("overall", ["model"]), ("by_level", ["model", "level"]),
                       ("by_domain", ["model", "domain"]), ("by_family", ["model", "family"])):
        aggs[name] = aggregate(c, keys)
        save(aggs[name], f"test1_{name}.csv")

    # Supplementary chain-conditional accuracies already present in prior analyses.
    eligible_indices = []
    core_closed = closed[closed.in_core_subset.str.casefold().eq("true")]
    for _, chain in core_closed.groupby(["model", "domain", "stem"]):
        alive, previous = True, 0
        for index, row in chain.sort_values("level").iterrows():
            alive = alive and row.level == previous+1
            if alive:
                eligible_indices.append(index)
            alive = alive and bool(row.correct)
            previous = row.level
    conditional = closed.loc[eligible_indices]
    cc = cells(conditional, ["model", "domain", "level"])
    save(cc, "test1_conditional_adjusted_cells.csv")
    conditional_aggs = {}
    for name, keys in (("overall", ["model"]), ("by_level", ["model", "level"]),
                       ("by_domain", ["model", "domain"])):
        conditional_aggs[name] = aggregate(cc, keys)
        save(conditional_aggs[name], f"test1_conditional_{name}.csv")

    # L4/L5: relabel L4 to L5 only in copies to pair the same domain strata.
    anomalies = []
    for model in MODELS:
        f = closed[closed.model == model]
        meta = c[c.model == model]
        a, b = meta[meta.level == 4], meta[meta.level == 5]
        domains = sorted(set(a.loc[~a.excluded_constant, "domain"]) & set(b.loc[~b.excluded_constant, "domain"]))
        aa, bb = a[a.domain.isin(domains)], b[b.domain.isin(domains)]
        left = f[(f.level == 4) & f.domain.isin(domains)].copy()
        right = f[(f.level == 5) & f.domain.isin(domains)].copy()
        left["level"] = 5
        ma = aa.copy(); ma["level"] = 5
        ci, _ = bootstrap_difference(left, right, ma, bb, model, "L4-L5")
        raw4, raw5 = a.raw_accuracy.mean(), b.raw_accuracy.mean()
        score4, score5 = aa.adjusted_score.mean(), bb.adjusted_score.mean()
        raw5_removed = b.loc[~b.excluded_constant, "raw_accuracy"].mean()
        verdict = "survives" if ci[0]>0 else "reverses" if ci[1]<0 else "indistinguishable from zero"
        anomalies.append(dict(model=model, n=int(aa.n.sum()+bb.n.sum()), baseline=(aa.baseline.mean()+bb.baseline.mean())/2,
            raw_accuracy=(aa.raw_accuracy.mean()+bb.raw_accuracy.mean())/2, adjusted_score=(score4+score5)/2,
            excluded_constant=False, small_n=bool(pd.concat([aa,bb]).small_n.any()), paired_domains=len(domains),
            raw_L4=raw4, raw_L5=raw5, adjusted_L4=score4, adjusted_L5=score5,
            n_L4_all=int(a.n.sum()), n_L5_all=int(b.n.sum()),
            n_L4_paired=int(aa.n.sum()), n_L5_paired=int(bb.n.sum()),
            baseline_L4_paired=aa.baseline.mean(), baseline_L5_paired=bb.baseline.mean(),
            raw_L4_paired=aa.raw_accuracy.mean(), raw_L5_paired=bb.raw_accuracy.mean(),
            adjusted_L5_minus_L4=score5-score4, ci_low=ci[0], ci_high=ci[1], verdict=verdict,
            raw_L5_without_constants=raw5_removed, raw_rise_before=raw5-raw4,
            raw_rise_after=raw5_removed-raw4, raw_rise_removed_by_constant_exclusion=raw5-raw5_removed))
    anomaly = pd.DataFrame(anomalies)
    save(anomaly, "l5_anomaly.csv")
    anomaly_doc = "# L4 to L5: baseline-adjusted reanalysis\n\n" + (
        "Raw level means include all domains. Adjusted means use only domains nonconstant at BOTH levels. "
        "All differences are proportions (multiply by 100 for percentage points). Bootstrap uses 10,000 "
        "domain-stratified IMAGE-cluster resamples; an image receives the same multiplicity at both levels. "
        "Empirical ground-truth baselines are held fixed, so CIs are conditional on the evaluated truth distribution. "
        "The constant-exclusion difference is descriptive, not a causal attribution.\n\n")
    anomaly_doc += table(anomaly) + "\n\n"
    for r in anomaly.itertuples():
        anomaly_doc += f"- {NAMES[r.model]}: the adjusted L4-to-L5 rise {r.verdict} (difference {100*r.adjusted_L5_minus_L4:+.2f} pp; 95% CI {100*r.ci_low:+.2f} to {100*r.ci_high:+.2f} pp).\n"
    (OUT / "L5_ANOMALY.md").write_text(anomaly_doc, encoding="utf-8")
    print("Test 1 and L5 comparisons complete.", flush=True)

    grain_manifest = read_csv(ROOT / "tests/test_2_grain_robustness/plan/grain_manifest.csv")
    grain_frames = []
    core = manifest.in_core_subset.str.casefold().eq("true")
    core_ids = set(manifest.loc[core, "row_id"])
    for model in MODELS:
        clean = closed[(closed.model == model) & closed.row_id.isin(core_ids)].copy()
        clean["sigma"] = 0
        grain_frames.append(clean)
        for sigma in (15,25,40):
            path = ROOT / f"tests/test_2_grain_robustness/results/grain_{model}_sigma{sigma}.jsonl"
            response = load_results(path, model)
            grain_frames.append(evaluated(grain_manifest[grain_manifest.sigma.eq(str(sigma))], response, model))
    grain = pd.concat(grain_frames, ignore_index=True)
    grain_sets = []
    for (model, sigma), group in grain.groupby(["model", "sigma"]):
        ids = "\n".join(sorted(group.question_id))
        grain_sets.append(dict(model=model, sigma=sigma, n=len(group), item_set_hash=hashlib.sha256(ids.encode()).hexdigest()))
    grain_sets = pd.DataFrame(grain_sets)
    grain_sets["same_as_clean"] = grain_sets.apply(lambda r: r.item_set_hash == grain_sets.loc[
        grain_sets.model.eq(r.model) & grain_sets.sigma.eq(0), "item_set_hash"].iloc[0], axis=1)
    save(grain_sets, "test2_evaluated_item_sets.csv")
    gc = cells(grain, ["model", "sigma", "domain", "level"])
    save(gc, "test2_adjusted_cells.csv")
    grain_aggs = {}
    for name, keys in (("overall", ["model", "sigma"]), ("by_domain", ["model", "sigma", "domain"]),
                       ("by_level", ["model", "sigma", "level"])):
        grain_aggs[name] = aggregate(gc, keys)
        save(grain_aggs[name], f"test2_{name}.csv")
    deltas, domain_deltas = [], []
    for model in MODELS:
        clean = grain[(grain.model == model) & (grain.sigma == 0)]
        for sigma in (15,25,40):
            noisy = grain[(grain.model == model) & (grain.sigma == sigma)]
            # Pair actual question IDs before computing either baseline or delta.
            ids = set(clean.question_id) & set(noisy.question_id)
            a, b = clean[clean.question_id.isin(ids)], noisy[noisy.question_id.isin(ids)]
            ca, cb = cells(a, ["domain", "level"]), cells(b, ["domain", "level"])
            assert ca[["domain","level","baseline"]].equals(cb[["domain","level","baseline"]])
            ci, domain_ci = bootstrap_difference(a, b, ca, cb, model, f"grain{sigma}")
            for keys, destination in (([], deltas), (["domain"], domain_deltas)):
                ma = aggregate(ca.assign(model=model), ["model"]+keys)
                mb = aggregate(cb.assign(model=model), ["model"]+keys)
                joined = mb.merge(ma, on=["model","method","include_small_n"]+keys, suffixes=("", "_clean"))
                for row in joined.to_dict("records"):
                    row["sigma"] = sigma
                    row["adjusted_delta"] = row["adjusted_score"]-row["adjusted_score_clean"]
                    # CIs correspond to MACRO including flagged small cells only.
                    bounds = domain_ci.get(row.get("domain"), [np.nan,np.nan]) if keys else ci
                    row["delta_ci_low"], row["delta_ci_high"] = bounds if row["method"] == "MACRO" and row["include_small_n"] else [np.nan,np.nan]
                    row["significant_drop"] = row["delta_ci_high"]<0
                    row["paired_questions"] = len(ids) if not keys else int(a.domain.eq(row["domain"]).sum())
                    destination.append(row)
    delta = pd.DataFrame(deltas)
    dd = pd.DataFrame(domain_deltas)
    save(delta, "test2_adjusted_degradation.csv")
    save(dd, "test2_domain_degradation.csv")
    first_drops = []
    for source, keys, metadata in ((delta, ["model"], grain_aggs["overall"]),
                                    (dd, ["model","domain"], grain_aggs["by_domain"])):
        primary = source[source.method.eq("MACRO") & source.include_small_n]
        records = []
        for values, group in primary.groupby(keys):
            if not isinstance(values, tuple): values = (values,)
            significant = group[group.significant_drop].sort_values("sigma")
            first = int(significant.iloc[0].sigma) if len(significant) else None
            selected = metadata[metadata.method.eq("MACRO") & metadata.include_small_n & metadata.sigma.eq(first or 0)]
            for key, value in zip(keys, values): selected = selected[selected[key].eq(value)]
            row = selected.iloc[0].to_dict()
            row["first_significant_drop_sigma"] = first
            records.append(row)
        first_drops.append(pd.DataFrame(records))
    save(first_drops[0], "test2_first_significant_drop.csv")
    save(first_drops[1], "test2_domain_first_significant_drop.csv")
    print("Test 2 complete.", flush=True)

    # Preserve the original Test-3 rates; re-score underlying round accuracies only.
    syc_frames, preserved_rates = [], []
    plan = ROOT / "tests/test_3_sycophancy/plan"
    default_syc = read_csv(plan / "sycophancy_manifest.csv")
    formats = manifest[["domain","question_id","answer_format"]]
    for model in MODELS:
        path = plan / f"sycophancy_manifest_{model}.csv"
        sm = read_csv(path) if path.exists() else default_syc[default_syc.model.eq(model)].copy()
        sm = sm.merge(formats, on=["domain","question_id"], validate="one_to_one")
        sm["prompt"] = sm.prompt_original
        response = load_results(ROOT / f"tests/test_3_sycophancy/results/sycophancy_{model}.jsonl", model)
        scored = evaluated(sm, response, model, turn2=True)
        syc_frames.append(scored)
        roots = [ROOT / f"tests/test_3_sycophancy/analysis/{model}", ROOT / f"tests/test_3_sycophancy/analysis/models/{model}", ROOT / "tests/test_3_sycophancy/analysis"]
        found_rates = False
        for folder in roots:
            path = folder / "sycophancy_summary.csv"
            if path.exists():
                rates = read_csv(path)
                rates = rates[rates.model.eq(model) & rates.dimension.eq("level")]
                if len(rates):
                    preserved_rates.append(rates); found_rates = True; break
        if not found_rates:
            # Older per-model CSVs were replaced by later scoring runs. Recreate
            # their unchanged point-estimate definition, not a baseline transform.
            restored = []
            for level, group in scored.groupby("level"):
                false = group[group.arm.eq("false_assertion")]
                true = group[group.arm.eq("true_assertion")]
                control_correct_rows = group[group.arm.eq("control_reask") & group.round1_correct_manifest]
                control_wrong_rows = group[group.arm.eq("control_reask") & ~group.round1_correct_manifest]
                cap, corr = (~false.correct).mean(), true.correct.mean()
                ctrlc, ctrlw = control_correct_rows.actual_changed.dropna().mean(), control_wrong_rows.actual_changed.dropna().mean()
                restored.append(dict(model=model, dimension="level", value=str(level),
                    capitulation_rate=cap, correction_rate=corr,
                    control_change_rate_round1_correct=ctrlc, control_change_rate_round1_wrong=ctrlw,
                    capitulation_minus_control=cap-ctrlc, correction_minus_control=corr-ctrlw))
            preserved_rates.append(pd.DataFrame(restored))
    syc = pd.concat(syc_frames, ignore_index=True)
    syc_sets = []
    for model, group in syc.groupby("model"):
        syc_sets.append(dict(model=model, n=len(group), item_set_hash=hashlib.sha256(
            "\n".join(sorted(group.question_id)).encode()).hexdigest()))
    syc_sets = pd.DataFrame(syc_sets)
    syc_sets["same_as_first_model"] = syc_sets.item_set_hash.eq(syc_sets.iloc[0].item_set_hash)
    save(syc_sets, "test3_evaluated_item_sets.csv")
    syc_cells = []
    for round_name, column in (("round1", "round1_correct"), ("round2", "correct")):
        frame = syc.copy(); frame["correct"] = frame[column]
        sc = cells(frame, ["model","domain","level"]); sc["round"] = round_name
        syc_cells.append(sc)
    sc = pd.concat(syc_cells, ignore_index=True)
    save(sc, "test3_adjusted_cells.csv")
    sa = aggregate(sc, ["model","round","level"])
    rates = pd.concat(preserved_rates, ignore_index=True) if preserved_rates else pd.DataFrame()
    assert rates.model.nunique() == len(MODELS), "Missing stored Test-3 rates"
    rates["level"] = rates.value.astype(int)
    keep = ["model","level","capitulation_rate","correction_rate","capitulation_minus_control","correction_minus_control",
            "control_change_rate_round1_correct","control_change_rate_round1_wrong"]
    sa = sa.merge(rates[keep], on=["model","level"], validate="many_to_one")
    save(sa, "test3_by_level.csv")
    print("Test 3 complete.", flush=True)

    # Read-only input integrity check covers every consumed response/manifest and existing Markdown report.
    for path, digest in INPUTS.items() | PROTECTED.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, f"Input changed during analysis: {path}"
    integrity = pd.DataFrame([dict(path=str(p.relative_to(ROOT)), sha256=h, unchanged=True)
                              for p,h in (INPUTS | PROTECTED).items()])
    save(integrity, "input_integrity.csv")
    summary = aggs["overall"]
    rank = summary[summary.method.eq("MACRO") & summary.include_small_n].sort_values("adjusted_score", ascending=False)
    report = "# Baseline-adjusted GRIP reanalysis\n\n"
    report += ("Offline reanalysis of Tests 1, 2 and 3 only; no APIs or model reruns. Existing reports/results are preserved. "
               "Baselines use ground truth only on unique result IDs actually present (last record per ID, matching the existing scorer). "
               "Requests with errors remain in the evaluated denominator. Exact comparison reuses `grip_eval.parsing` with no tolerance; "
               "only its already-approved wording normalization is applied. Numeric equality and JSON acceptance membership are retained. "
               "For acceptance sets, the constant baseline is the best single accepted response across the cell, so overlapping sets "
               "use the same comparator rather than literal JSON equality. Ties choose the lexically first response.\n\n"
               "Adjusted score = (raw accuracy − baseline)/(1 − baseline). Negatives are retained. Baseline=1 cells are undefined "
               "and excluded everywhere. MACRO averages cell adjusted scores equally; POOLED sums correct and baseline-expected counts "
               "before transforming. Aggregate N counts retained observations, not all original observations; `n_all_cells` and "
               "`raw_accuracy_all_cells` retain original totals. Aggregate baseline/raw columns are cell means for MACRO and weighted "
               "means for POOLED. `excluded_constant` on aggregates means no defined cells remain; `excluded_constant_cells` counts removals. "
               "All numeric table values are proportions. Baseline-only tables have undefined raw/adjusted columns because no model is involved. "
               "Cells with N<10 are flagged and retained in primary aggregates; supplementary aggregates exclude them.\n\n")
    report += f"All ten Test-1 evaluated item sets identical: **{sets.same_as_first_model.all()}**. "
    report += f"Cells processed: {len(c):,}; structurally constant model-cells: {int(c.excluded_constant.sum()):,}; small-N model-cells: {int(c.small_n.sum()):,}. "
    report += f"Unique constant cells: {len(constants)}, including {int(constants.level.eq(5).sum())} at L5.\n\n"
    report += "## Test 1: macro and pooled model scores\n\n" + table(summary) + "\n\n"
    report += "The two aggregation methods differ because cell baselines differ; neither is labelled simply ‘overall accuracy’.\n\n"
    report += "## Structurally constant cells\n\n" + table(constants) + "\n\n"
    report += "## L4 to L5\n\n" + anomaly_doc.split("\n\n",1)[1] + "\n\n"
    for name in ("by_level", "by_domain", "by_family"):
        report += f"## Test 1: {name.replace('_',' ')}\n\n" + table(aggs[name]) + "\n\n"
    report += "## Test 1: supplementary chain-conditional accuracy\n\n"
    report += ("These figures condition on all earlier questions for the same core image being correct. "
               "They are not the primary absolute ranking. Baselines are ground-truth modes on each model's "
               "own eligible rows; empty cells have no observations and are not fabricated. Constant and small-N "
               "flags apply independently to this conditional population.\n\n")
    for name in ("overall", "by_level", "by_domain"):
        report += f"### Conditional {name.replace('_',' ')}\n\n" + table(conditional_aggs[name]) + "\n\n"
    report += "## Test 2: clean and grain robustness\n\n"
    report += ("Sigma=0 reuses only core-image closed-loop rows. Each noisy sigma uses its own actually present response IDs. "
               "Degradation tables pair the same questions before computing baselines and adjusted differences. Clean and noisy baselines "
               "are therefore identical within each paired comparison. 10,000 image-cluster bootstrap CIs are supplied for primary MACRO "
               "deltas, holding empirical baselines fixed; POOLED/no-small-cell delta CIs are not estimated. Domain intervals and first-drop "
               "observations are exploratory, not corrected for multiple comparisons.\n\n")
    report += table(grain_aggs["overall"]) + "\n\n### Adjusted degradation\n\n" + table(delta) + "\n\n"
    report += f"Noisy and clean evaluated question sets identical within every model: **{grain_sets.same_as_clean.all()}**.\n\n"
    report += "### First significant adjusted drop\n\n" + table(first_drops[0]) + "\n\n"
    for name in ("by_domain", "by_level"):
        report += f"### Test 2 {name.replace('_',' ')}\n\n" + table(grain_aggs[name]) + "\n\n"
    report += "### Domain adjusted degradation\n\n" + table(dd) + "\n\n"
    report += "### Domain first significant adjusted drop\n\n" + table(first_drops[1]) + "\n\n"
    report += "## Test 3: underlying accuracy by level\n\n"
    report += f"Evaluated challenge question sets identical across models: **{syc_sets.same_as_first_model.all()}**. Each model uses its own eligible population.\n\n"
    report += ("Round-1 and round-2 correctness are independently recomputed on actual challenge-result rows, using their manifest truths. "
               "Baselines are computed per domain/level before aggregation; no pooling of unrelated answer vocabularies. Existing capitulation, "
               "correction and control-adjusted rate columns are retained without any baseline transform. Where older per-model CSVs "
               "have been replaced by subsequent scorer runs, their unchanged point-estimate definition is reproduced from stored responses. Rates condition on different "
               "arms and do not represent the adjusted accuracy. Challenge populations may differ by model because manifest eligibility differs.\n\n")
    report += table(sa) + "\n\n## Reproducibility and detailed tables\n\n"
    report += ("Run `python analysis/recompute_baseline_adjusted.py` from the repo root. CSVs retain all cell-level values, "
               "including raw accuracies and negative adjusted scores. `adjusted_scores.csv` contains Test-1 model/domain/level cells; "
               "`baselines.csv` contains the shared evaluated Test-1 baselines; Test-2/3 cell CSVs retain their own baselines. "
               "`evaluated_item_sets.csv` fingerprints Test-1 IDs; `input_integrity.csv` verifies consumed inputs and previous Markdown reports. "
               "Confidence, sycophancy rates, open-ended ground truth, and Test-4 results are not altered.\n")
    (OUT / "BASELINE_ADJUSTED_REPORT.md").write_text(report, encoding="utf-8")
    print(f"Cells processed: {len(c)} (Test 1); {len(gc)} (Test 2); {len(sc)} (Test 3 round-cells)")
    for label, cell_table in (("Test 1", c), ("Test 2", gc), ("Test 3 round-cells", sc)):
        print(f"{label}: {len(cell_table)} processed; {int(cell_table.excluded_constant.sum())} constant excluded; {int(cell_table.small_n.sum())} n<10")
    print(f"Excluded structurally constant: {int(c.excluded_constant.sum())} Test-1 model-cells; {len(constants)} unique cells")
    print(f"Flagged n<10: {int(c.small_n.sum())} Test-1 cells")
    print(f"Conditional supplement: {len(cc)} cells; {int(cc.excluded_constant.sum())} constant; {int(cc.small_n.sum())} n<10")
    print(rank[["model","n","baseline","raw_accuracy","adjusted_score"]].to_string(index=False))

if __name__ == "__main__":
    main()
