"""Independent arithmetic/integrity checks on the additive offline deliverables."""
from pathlib import Path
import hashlib
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

def verify_cells(name):
    c = pd.read_csv(HERE / name)
    assert (c.n > 0).all()
    assert np.allclose(c.raw_accuracy, c.correct_count / c.n)
    assert np.allclose(c.baseline, c.baseline_expected_correct / c.n)
    assert c.excluded_constant.equals(c.baseline.eq(1))
    assert c.small_n.equals(c.n.lt(10))
    assert c.loc[c.excluded_constant, "adjusted_score"].isna().all()
    valid = c.loc[~c.excluded_constant]
    assert np.allclose(valid.adjusted_score, (valid.raw_accuracy-valid.baseline)/(1-valid.baseline))
    return c

def verify_aggregates(c, filename, keys):
    result = pd.read_csv(HERE / filename)
    for r in result.to_dict("records"):
        all_cells = c
        for key in keys:
            all_cells = all_cells[all_cells[key].eq(r[key])]
        valid = all_cells[~all_cells.excluded_constant & (r["include_small_n"] | ~all_cells.small_n)]
        assert valid.n.sum() == r["n"]
        assert all_cells.n.sum() == r["n_all_cells"]
        assert np.isclose(all_cells.correct_count.sum()/all_cells.n.sum(), r["raw_accuracy_all_cells"])
        if valid.empty:
            assert pd.isna(r["adjusted_score"])
        elif r["method"] == "MACRO":
            assert np.isclose(valid.adjusted_score.mean(), r["adjusted_score"])
        else:
            expected = (valid.correct_count.sum()-valid.baseline_expected_correct.sum())/(valid.n.sum()-valid.baseline_expected_correct.sum())
            assert np.isclose(expected, r["adjusted_score"])

def main():
    closed = verify_cells("adjusted_scores.csv")
    grain = verify_cells("test2_adjusted_cells.csv")
    syc = verify_cells("test3_adjusted_cells.csv")
    conditional = verify_cells("test1_conditional_adjusted_cells.csv")
    assert len(closed) == 1700 and closed.model.nunique() == 10
    assert len(grain) == 6800 and grain.model.nunique() == 10
    for name, keys in (("overall", ["model"]), ("by_level", ["model","level"]),
                       ("by_domain", ["model","domain"]), ("by_family", ["model","family"])):
        verify_aggregates(closed, f"test1_{name}.csv", keys)
    for name, keys in (("overall", ["model","sigma"]), ("by_level", ["model","sigma","level"]),
                       ("by_domain", ["model","sigma","domain"])):
        verify_aggregates(grain, f"test2_{name}.csv", keys)
    verify_aggregates(syc, "test3_by_level.csv", ["model","round","level"])
    for name, keys in (("overall", ["model"]), ("by_level", ["model","level"]), ("by_domain", ["model","domain"])):
        verify_aggregates(conditional, f"test1_conditional_{name}.csv", keys)
    deltas = pd.read_csv(HERE / "test2_adjusted_degradation.csv")
    assert np.allclose(deltas.adjusted_delta, deltas.adjusted_score-deltas.adjusted_score_clean)
    integrity = pd.read_csv(HERE / "input_integrity.csv")
    for row in integrity.itertuples():
        assert hashlib.sha256((ROOT / row.path).read_bytes()).hexdigest() == row.sha256
    print(f"PASS: {len(closed)+len(grain)+len(syc)+len(conditional):,} cell arithmetic checks; all macro/pooled tables; paired grain deltas; {len(integrity)} unchanged inputs/reports.")

if __name__ == "__main__":
    main()
