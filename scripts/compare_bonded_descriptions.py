#!/usr/bin/env python3
"""Compare exact description overlap within and between bonded names.

Run after the OWRD download. Writes one comparison table and one figure under
04_analysis/raw_lithology_profile; source data are not changed.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MIN_TOTAL_REPORTS = 10
MIN_REPORTS_PER_NAME_STRATUM = 3
MIN_MATCHED_REPORTS = 10
N_SHUFFLES = 999
SEED = 20260928
DEPTH_EDGES = [-0.01, 100, 300, 600, float("inf")]
DEPTH_LABELS = ["0-100", "100-300", "300-600", "600+"]


def dice_matrix(sets: list[frozenset[str]]) -> np.ndarray:
    """Dice similarity of exact-description sets from separate reports."""
    n = len(sets)
    out = np.zeros((n, n), dtype=float)
    lengths = np.array([len(value) for value in sets])
    for i in range(n):
        for j in range(i + 1, n):
            out[i, j] = out[j, i] = 2 * len(sets[i] & sets[j]) / (lengths[i] + lengths[j])
    return out


def stratum_scores(similarity: np.ndarray, codes: np.ndarray, labels: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Sum per-report within/between averages for each global name code."""
    n = len(codes)
    local = np.searchsorted(labels, codes)
    counts = np.bincount(local, minlength=len(labels))
    membership = np.eye(len(labels), dtype=float)[local]
    same_sums = similarity @ membership
    selected = same_sums[np.arange(n), local]
    within = selected / (counts[local] - 1)
    between = (similarity.sum(axis=1) - selected) / (n - counts[local])
    return np.bincount(local, weights=within, minlength=len(labels)), np.bincount(local, weights=between, minlength=len(labels)), counts


def build_strata(wells: pd.DataFrame, intervals: pd.DataFrame) -> tuple[list[tuple[np.ndarray, np.ndarray, np.ndarray]], list[str], pd.DataFrame]:
    if wells.wl_id.duplicated().any():
        raise ValueError("wl_id must be unique in wells_raw.csv")
    report_sets = intervals.groupby("well_id").material_raw.agg(lambda series: frozenset(series)).rename("phrases")
    reports = wells[wells.wl_id.isin(report_sets.index)].copy()
    reports["bonded_full_name"] = reports.bonded_full_name.str.strip()
    counts = reports.bonded_full_name.value_counts()
    names = sorted(counts[(counts >= MIN_TOTAL_REPORTS) & ~counts.index.str.match(r"^UNKNOWN(?:\s|$)") & (counts.index != "")].index)
    reports = reports[reports.bonded_full_name.isin(names)].copy()
    reports["phrases"] = reports.wl_id.map(report_sets)
    reports["year"] = pd.to_numeric(reports.complete_date_iso.str[:4], errors="coerce")
    reports["decade"] = (reports.year // 10 * 10).astype("Int64")
    reports["depth_bin"] = pd.cut(pd.to_numeric(reports.completed_depth, errors="coerce"), DEPTH_EDGES, labels=DEPTH_LABELS)
    reports = reports[reports.decade.notna() & reports.depth_bin.notna()]
    keys = ["type_of_log", "tr_key", "decade", "depth_bin"]
    strata = []
    matched_rows = []
    for key, group in reports.groupby(keys, observed=True):
        eligible = group.bonded_full_name.value_counts()
        eligible = set(eligible[eligible >= MIN_REPORTS_PER_NAME_STRATUM].index)
        group = group[group.bonded_full_name.isin(eligible)].sort_values("wl_id")
        if len(eligible) < 2:
            continue
        labels = np.array([names.index(name) for name in group.bonded_full_name], dtype=int)
        strata.append((dice_matrix(group.phrases.tolist()), labels, np.unique(labels)))
        matched_rows.extend({"wl_id": row.wl_id, "bonded_full_name": row.bonded_full_name, "type_of_log": key[0], "tr_key": key[1], "decade": key[2], "depth_bin": str(key[3])} for row in group.itertuples())
    return strata, names, pd.DataFrame(matched_rows)


def aggregate(strata: list[tuple[np.ndarray, np.ndarray, np.ndarray]], n_names: int, *, rng: np.random.Generator | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    within_sum = np.zeros(n_names)
    between_sum = np.zeros(n_names)
    report_count = np.zeros(n_names, dtype=int)
    for similarity, original_codes, labels in strata:
        codes = rng.permutation(original_codes) if rng is not None else original_codes
        within, between, count = stratum_scores(similarity, codes, labels)
        within_sum[labels] += within
        between_sum[labels] += between
        report_count[labels] += count
    return within_sum, between_sum, report_count


def bh_adjust(pvalues: np.ndarray) -> np.ndarray:
    order = np.argsort(pvalues)
    ranked = pvalues[order] * len(pvalues) / np.arange(1, len(pvalues) + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    adjusted = np.empty_like(ranked)
    adjusted[order] = np.minimum(ranked, 1)
    return adjusted


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    out = root / "04_analysis/raw_lithology_profile"
    out.mkdir(parents=True, exist_ok=True)
    wells = pd.read_csv(root / "01_raw/owrd/wells_raw.csv", dtype=str, keep_default_na=False)
    intervals = pd.read_csv(root / "03_processed/lithology/lithology_all_raw.csv", dtype=str, keep_default_na=False)
    strata, names, matched = build_strata(wells, intervals)
    if not strata:
        raise ValueError("No strata with at least two eligible bonded names")
    within_sum, between_sum, report_count = aggregate(strata, len(names))
    eligible = np.flatnonzero(report_count >= MIN_MATCHED_REPORTS)
    observed_within = within_sum[eligible] / report_count[eligible]
    observed_between = between_sum[eligible] / report_count[eligible]
    observed_delta = observed_within - observed_between
    rng = np.random.default_rng(SEED)
    shuffled_delta = np.empty((N_SHUFFLES, len(eligible)))
    for i in range(N_SHUFFLES):
        ws, bs, counts = aggregate(strata, len(names), rng=rng)
        if not np.array_equal(counts, report_count):
            raise AssertionError("Permutation changed name frequencies")
        shuffled_delta[i] = (ws[eligible] - bs[eligible]) / counts[eligible]
    pvalues = (1 + (shuffled_delta >= observed_delta).sum(axis=0)) / (N_SHUFFLES + 1)
    results = pd.DataFrame({
        "bonded_full_name": np.array(names)[eligible],
        "matched_reports": report_count[eligible],
        "within_dice": observed_within,
        "between_dice": observed_between,
        "within_minus_between": observed_delta,
        "shuffled_p025": np.quantile(shuffled_delta, 0.025, axis=0),
        "shuffled_p975": np.quantile(shuffled_delta, 0.975, axis=0),
        "one_sided_p": pvalues,
        "bh_adjusted_q": bh_adjust(pvalues),
    }).sort_values("within_minus_between", ascending=False)
    results.to_csv(out / "bonded_within_between_similarity.csv", index=False)

    shown = results.iloc[::-1]
    y = np.arange(len(shown))
    fig, (left, right) = plt.subplots(1, 2, figsize=(14, max(8, 0.45 * len(shown) + 2)), sharey=True, gridspec_kw={"width_ratios": [1.3, 1]})
    left.hlines(y, shown.between_dice * 100, shown.within_dice * 100, color="#9eaab1", linewidth=1.5)
    left.scatter(shown.between_dice * 100, y, color="#bd7436", s=40, label="Other bonded names", zorder=3)
    left.scatter(shown.within_dice * 100, y, color="#376a8a", s=40, label="Same bonded name", zorder=3)
    left.set_yticks(y, [f"{row.bonded_full_name} (n={row.matched_reports})" for row in shown.itertuples()])
    left.set_xlabel("Mean exact-description overlap (Dice, %)")
    left.set_xlim(left=0)
    left.set_title("Within vs. between reports")
    left.legend(loc="lower right", fontsize=9)
    left.grid(axis="x", alpha=0.2)
    right.hlines(y, shown.shuffled_p025 * 100, shown.shuffled_p975 * 100, color="#b7c3c8", linewidth=5, label="95% shuffled-label range")
    right.scatter(shown.within_minus_between * 100, y, color="#202c32", s=40, label="Observed difference", zorder=3)
    right.axvline(0, color="#555555", linewidth=1, linestyle="--")
    right.set_xlabel("Within minus between (percentage points)")
    right.set_title("Difference and shuffled-label reference")
    right.legend(loc="lower right", fontsize=9)
    right.grid(axis="x", alpha=0.2)
    fig.suptitle(f"Do bonded names reuse exact wording? {sum(results.within_minus_between > 0)}/{len(results)} show higher within-name overlap", fontsize=14)
    fig.subplots_adjust(left=0.23, right=0.98, top=0.89, bottom=0.1, wspace=0.13)
    fig.savefig(out / "bonded_within_between_similarity.png", dpi=180)
    plt.close(fig)
    print(f"Compared {len(results)} bonded names across {len(strata)} matched strata and {len(matched)} report-stratum rows")
    print(results.to_string(index=False, float_format=lambda value: f"{value:.3f}"))


if __name__ == "__main__":
    main()
