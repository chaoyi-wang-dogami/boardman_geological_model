#!/usr/bin/env python3
"""Compare exact description overlap among reports of selected drillers."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from driller_analysis_common import selected_drillers, well_units
from township_location_qc import audit_locations


ROOT = Path(__file__).resolve().parents[1]


def dice_matrix(sets: list[frozenset[str]]) -> np.ndarray:
    """Pairwise Dice scores; diagonal is zero because a report cannot compare to itself."""
    n = len(sets)
    result = np.zeros((n, n), dtype=np.float32)
    sizes = [len(value) for value in sets]
    for i in range(n):
        for j in range(i + 1, n):
            result[i, j] = result[j, i] = 2 * len(sets[i] & sets[j]) / (sizes[i] + sizes[j])
    return result


def compare(reports: pd.DataFrame) -> pd.DataFrame:
    """Each selected well contributes one within and one between mean."""
    reports = reports.sort_values("wl_id").reset_index(drop=True)
    names = reports.bonded_full_name.to_numpy()
    similarity = dice_matrix(reports.phrases.tolist())
    rows = []
    for name in sorted(set(names)):
        own = np.flatnonzero(names == name)
        other = np.flatnonzero(names != name)
        if len(own) < 2 or len(other) == 0:
            raise ValueError(f"Insufficient reports for {name}")
        within = similarity[np.ix_(own, own)].sum(axis=1) / (len(own) - 1)
        between = similarity[np.ix_(own, other)].mean(axis=1)
        rows.append({
            "bonded_full_name": name,
            "lithology_wells": len(own),
            "within_dice": float(within.mean()),
            "between_dice": float(between.mean()),
            "within_minus_between": float(within.mean() - between.mean()),
        })
    return pd.DataFrame(rows).sort_values("within_minus_between", ascending=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    root = parser.parse_args().root.resolve()
    out = root / "04_analysis/raw_lithology_profile/artifacts"
    out.mkdir(parents=True, exist_ok=True)
    wells = pd.read_csv(root / "01_raw/owrd/wells_raw.csv", dtype=str, keep_default_na=False)
    intervals = pd.read_csv(root / "03_processed/lithology/lithology_all_raw.csv", dtype=str, keep_default_na=False)
    units, _ = well_units(wells, intervals, audit_locations(root, wells)[0])
    cohort = selected_drillers(units)
    report_sets = intervals.groupby("well_id").material_raw.agg(lambda x: frozenset(x))
    reports = units[units.bonded_full_name.isin(cohort.bonded_full_name)].copy()
    reports["phrases"] = reports.wl_id.map(report_sets)
    result = compare(reports)
    if set(result.bonded_full_name) != set(cohort.bonded_full_name):
        raise AssertionError("Comparison does not cover the selected driller cohort")
    result.to_csv(out / "bonded_within_between_similarity.csv", index=False)

    # Figure 5 uses identical A/B well units on its vocabulary and spatial axes.
    ab_reports = reports[reports.location_class.isin(["A", "B"])].copy()
    ab_result = compare(ab_reports)
    if set(ab_result.bonded_full_name) != set(cohort.bonded_full_name):
        raise AssertionError("A/B wording comparison does not cover the selected cohort")
    ab_result.to_csv(out / "bonded_ab_within_between_similarity.csv", index=False)

    shown = result.iloc[::-1]
    y = np.arange(len(shown))
    fig, ax = plt.subplots(figsize=(11, max(7, 0.43 * len(shown) + 1.5)))
    ax.hlines(y, shown.between_dice * 100, shown.within_dice * 100, color="#a9b5bb", linewidth=1.6)
    ax.scatter(shown.between_dice * 100, y, color="#dfaa35", edgecolor="#80621e", linewidth=0.4, s=49,
               label="Well units by other drillers", zorder=3)
    ax.scatter(shown.within_dice * 100, y, color="#376a8a", s=49,
               label="Other well units by the same driller", zorder=3)
    ax.set_yticks(y, [f"{r.bonded_full_name} (n={r.lithology_wells})" for r in shown.itertuples()])
    ax.set(xlabel="Mean exact-description overlap (Dice, %)", title="Description overlap within and between drillers")
    ax.set_xlim(left=0)
    ax.grid(axis="x", alpha=0.2)
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(out / "bonded_within_between_similarity.png", dpi=180)
    plt.close(fig)
    print(result.to_string(index=False, float_format=lambda x: f"{x:.3f}"))


if __name__ == "__main__":
    main()
