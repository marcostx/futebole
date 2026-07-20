"""
Aggregate the parameter-sweep results into LaTeX tables and pgfplots data.

Reads experiments/results.csv (written by run_experiments.py), computes per-
configuration means and standard deviations for the reported metrics, runs a
paired sign-flip permutation test of every configuration against the baseline
(seeds are shared, so matches are paired through common random numbers), and
writes:

    paper/generated/summary_main.tex      main results table body
    paper/generated/summary_flow.tex      ball-flow / spatial table body
    paper/generated/pvalues.tex           permutation p-value table body
    paper/generated/<metric>.dat          pgfplots-ready columns per metric
"""

import csv
import itertools
import os
import random
import statistics
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IN_CSV = os.path.join(BASE, "experiments", "results.csv")
OUT_DIR = os.path.join(BASE, "paper", "generated")

CONFIG_ORDER = [
    "baseline",
    "tackle-low", "tackle-high",
    "press-pass-low", "press-pass-high",
    "long-shot-off", "long-shot-high",
    "shoot-short", "shoot-long",
    "shape-rigid", "shape-elastic",
]

# Pretty LaTeX labels for configurations.
LABELS = {
    "baseline": r"\textsc{Baseline}",
    "tackle-low": r"$p_{\mathrm{tackle}}{=}0.01$",
    "tackle-high": r"$p_{\mathrm{tackle}}{=}0.15$",
    "press-pass-low": r"$p_{\mathrm{off}}{=}0.01$",
    "press-pass-high": r"$p_{\mathrm{off}}{=}0.20$",
    "long-shot-off": r"$p_{\mathrm{long}}{=}0$",
    "long-shot-high": r"$p_{\mathrm{long}}{=}0.10$",
    "shoot-short": r"$R_{\mathrm{shot}}{=}100$",
    "shoot-long": r"$R_{\mathrm{shot}}{=}220$",
    "shape-rigid": r"$\kappa_{\mathrm{slide}}{=}0.2$",
    "shape-elastic": r"$\kappa_{\mathrm{slide}}{=}0.8$",
}

MAIN_METRICS = ["goals", "shots", "passes", "pass_comp_pct", "poss_share_dev", "turnovers"]
FLOW_METRICS = ["free_pct", "restarts", "ball_mean_speed_moving", "ball_still_pct",
                "t1_spread_mean", "overlap_pct"]
PVAL_METRICS = ["goals", "shots", "passes", "turnovers", "free_pct", "t1_spread_mean"]

N_PERM = 20000


def load_rows():
    with open(IN_CSV) as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k, v in r.items():
            if k != "config":
                r[k] = float(v)
        # Derived metrics.
        r["pass_comp_pct"] = (r["pass_completed"] / r["passes"] * 100
                              if r["passes"] else 0.0)
        # Deviation from a perfectly even split of held-ball time. The raw
        # percentages include free-ball frames, so renormalize the two held
        # shares before comparing Team 1 with 50%.
        held = r["poss1_pct"] + r["poss2_pct"]
        r["poss_share_dev"] = (abs(r["poss1_pct"] / held * 100 - 50)
                               if held else 0.0)
    return rows


def by_config(rows):
    out = {}
    for r in rows:
        out.setdefault(r["config"], []).append(r)
    for cfg in out:
        out[cfg].sort(key=lambda r: r["seed"])
    return out


def mean_std(values):
    m = statistics.mean(values)
    s = statistics.stdev(values) if len(values) > 1 else 0.0
    return m, s


def paired_permutation_p(diffs, n_perm=N_PERM, rng_seed=123):
    """Two-sided sign-flip permutation test on paired differences."""
    rng = random.Random(rng_seed)
    observed = abs(sum(diffs) / len(diffs))
    if all(d == 0 for d in diffs):
        return 1.0
    count = 0
    for _ in range(n_perm):
        s = sum(d if rng.random() < 0.5 else -d for d in diffs)
        if abs(s / len(diffs)) >= observed - 1e-12:
            count += 1
    return (count + 1) / (n_perm + 1)


def fmt(m, s, digits=1):
    return f"${m:.{digits}f} \\pm {s:.{digits}f}$"


def table_body(groups, metrics, digits):
    lines = []
    for cfg in CONFIG_ORDER:
        if cfg not in groups:
            continue
        cells = [LABELS[cfg]]
        for met in metrics:
            m, s = mean_std([r[met] for r in groups[cfg]])
            cells.append(fmt(m, s, digits.get(met, 1)))
        lines.append(" & ".join(cells) + r" \\")
    return "\n".join(lines) + "\n"


def pvalue_body(groups):
    base = groups["baseline"]
    lines = []
    for cfg in CONFIG_ORDER:
        if cfg == "baseline" or cfg not in groups:
            continue
        cells = [LABELS[cfg]]
        for met in PVAL_METRICS:
            diffs = [a[met] - b[met] for a, b in zip(groups[cfg], base)]
            p = paired_permutation_p(diffs)
            delta = sum(diffs) / len(diffs)
            mark = ""
            if p < 0.01:
                mark = r"$^{**}$"
            elif p < 0.05:
                mark = r"$^{*}$"
            cells.append(f"${delta:+.1f}$ ({p:.3f}){mark}")
        lines.append(" & ".join(cells) + r" \\")
    return "\n".join(lines) + "\n"


def write_dat(groups, metric, fname):
    """pgfplots table: numeric index, mean, std (config order is fixed)."""
    with open(os.path.join(OUT_DIR, fname), "w") as f:
        f.write("idx mean std\n")
        for i, cfg in enumerate(c for c in CONFIG_ORDER if c in groups):
            m, s = mean_std([r[metric] for r in groups[cfg]])
            f.write(f"{i} {m:.3f} {s:.3f}\n")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rows = load_rows()
    groups = by_config(rows)

    n_seeds = {cfg: len(v) for cfg, v in groups.items()}
    print("configs:", n_seeds)

    digits = {"goals": 2, "shots": 1, "passes": 1, "pass_comp_pct": 1,
              "poss_share_dev": 1, "turnovers": 1, "free_pct": 1,
              "restarts": 1, "ball_mean_speed_moving": 0,
              "ball_still_pct": 1, "t1_spread_mean": 0, "overlap_pct": 1}

    # Wrap each table body in a macro: \input inside tabular breaks under
    # LaTeX's file hooks, so main.tex loads these in the preamble instead.
    with open(os.path.join(OUT_DIR, "summary_main.tex"), "w") as f:
        f.write("\\newcommand{\\SummaryMainRows}{%\n"
                + table_body(groups, MAIN_METRICS, digits) + "}\n")
    with open(os.path.join(OUT_DIR, "summary_flow.tex"), "w") as f:
        f.write("\\newcommand{\\SummaryFlowRows}{%\n"
                + table_body(groups, FLOW_METRICS, digits) + "}\n")
    with open(os.path.join(OUT_DIR, "pvalues.tex"), "w") as f:
        f.write("\\newcommand{\\PValueRows}{%\n"
                + pvalue_body(groups) + "}\n")

    for metric in ["goals", "shots", "passes", "turnovers", "free_pct",
                   "t1_spread_mean", "pass_comp_pct", "ball_mean_speed_moving"]:
        write_dat(groups, metric, f"{metric}.dat")

    print(f"wrote tables and .dat files to {OUT_DIR}")


if __name__ == "__main__":
    main()
