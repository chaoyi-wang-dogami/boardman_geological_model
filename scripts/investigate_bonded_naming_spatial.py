#!/usr/bin/env python3
"""Investigate exact bonded-name phrase reuse and location concentration.

Run after profile_raw_lithology.py. Only derived files under
04_analysis/raw_lithology_profile are written.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pyproj import Transformer


ROOT = Path(__file__).resolve().parents[1]
MIN_REPORTS = 10
K = 5
N_PERMUTATIONS = 999
SEED = 20260928
EXAMPLE_NAME = "BRANDON BROWN"


def usable_name(values: pd.Series) -> pd.Series:
    name = values.str.strip()
    return name.ne("") & ~name.str.upper().str.match(r"^UNKNOWN(?:\s|$)")


def nearest_indices(frame: pd.DataFrame) -> np.ndarray:
    """Return five nearest other *reports*, allowing coincident coordinates."""
    lon = frame.longitude.to_numpy(dtype=float)
    lat = frame.latitude.to_numpy(dtype=float)
    # OWRD's queried geometry is WGS84; all points lie in UTM zone 11N.
    x, y = Transformer.from_crs("EPSG:4326", "EPSG:32611", always_xy=True).transform(lon, lat)
    xy = np.column_stack([x, y])
    squared = ((xy[:, None, :] - xy[None, :, :]) ** 2).sum(axis=2)
    np.fill_diagonal(squared, np.inf)
    # Stable order makes exact-distance ties reproducible by wl_id row order.
    return np.argsort(squared, axis=1, kind="stable")[:, :K]


def neighbor_stats(frame: pd.DataFrame, *, seed: int, stratify: bool) -> pd.DataFrame:
    """Random-label reference keeps coordinates and label frequencies fixed."""
    if len(frame) <= K:
        raise ValueError("Not enough mapped reports for five nearest neighbours")
    frame = frame.reset_index(drop=True)
    neighbors = nearest_indices(frame)
    names, codes = np.unique(frame.bonded_full_name.to_numpy(), return_inverse=True)
    n_by_name = np.bincount(codes, minlength=len(names))

    def score(label_codes: np.ndarray) -> np.ndarray:
        same_count = (label_codes[:, None] == label_codes[neighbors]).sum(axis=1)
        return np.bincount(label_codes, weights=same_count, minlength=len(names)) / (K * n_by_name)

    observed = score(codes)
    simulated = np.empty((N_PERMUTATIONS, len(names)), dtype=float)
    rng = np.random.default_rng(seed)
    if stratify:
        decade = frame.complete_date_iso.str[:3].where(frame.complete_date_iso.ne(""), "missing")
        strata = (frame.type_of_log + "|" + decade).to_numpy()
        strata_indices = [np.flatnonzero(strata == value) for value in np.unique(strata)]
    for i in range(N_PERMUTATIONS):
        if stratify:
            shuffled = codes.copy()
            for indices in strata_indices:
                shuffled[indices] = rng.permutation(codes[indices])
        else:
            shuffled = rng.permutation(codes)
        simulated[i] = score(shuffled)
    null_mean = np.mean(simulated, axis=0)
    result = pd.DataFrame({
        "bonded_full_name": names,
        "reports": n_by_name,
        "observed_same_name_fraction": observed,
        "null_mean_fraction": null_mean,
        "null_median_fraction": np.median(simulated, axis=0),
        "null_p025_fraction": np.quantile(simulated, 0.025, axis=0),
        "null_p975_fraction": np.quantile(simulated, 0.975, axis=0),
        "enrichment_ratio": np.divide(observed, null_mean, out=np.full_like(observed, np.nan), where=null_mean > 0),
        "one_sided_permutation_p": (1 + (simulated >= observed).sum(axis=0)) / (N_PERMUTATIONS + 1),
    })
    return result


def write_named_example(phrases: pd.DataFrame, summary: pd.DataFrame, out: Path) -> None:
    """Keep the full Brandon Brown wording example reproducible and reviewable."""
    block = phrases[phrases.bonded_full_name == EXAMPLE_NAME]
    if block.empty:
        raise ValueError(f"Expected example name absent from interval data: {EXAMPLE_NAME}")
    stats = summary.set_index("bonded_full_name").loc[EXAMPLE_NAME]
    one_report = int((block.report_count == 1).sum())
    one_interval = int(((block.report_count == 1) & (block.interval_count == 1)).sum())
    lines = [
        f"# {EXAMPLE_NAME}: exact interval descriptions",
        "",
        "This example comes from the exact `bonded_full_name` value `BRANDON BROWN` in the OWRD well metadata, joined to structured `material_raw` intervals by report ID. It does not include the separate value `BRANDON C BROWN`. A bonded name is associated with a report; the structured data do not establish who wrote each description.",
        "",
        f"Across **{int(stats.reports):,} reports** and **{int(stats.intervals):,} intervals**, this name is associated with **{len(block):,} distinct exact description strings**. **{int(stats.phrases_reused_in_2plus_reports):,}** occur in at least two reports; **{one_report:,}** occur in one report only. Of the latter, **{one_interval:,}** occur in just one interval, and **{one_report - one_interval:,}** recur within their single report.",
        "",
        "These strings are not 539 rock types. Many combine material, colour, hardness, fracturing, and adjoining material; some are abbreviations, spelling variants, or construction notes. That detail is valuable source information but produces a long tail for any future classification. No descriptions are merged or assigned standardized labels here.",
        "",
        "Each table row is one exact stored `material_raw` string. Report count is the number of distinct report IDs containing it; interval count includes repeat occurrences within a report. This file is regenerated by `uv run python scripts/investigate_bonded_naming_spatial.py`.",
    ]
    for title, subset in [
        ("Descriptions used in two or more reports", block[block.report_count >= 2]),
        ("Descriptions used in one report", block[block.report_count == 1]),
    ]:
        lines.extend(["", f"## {title}", "", "| Exact description | Reports | Intervals |", "|---|---:|---:|"])
        for row in subset.itertuples():
            description = row.material_raw.replace("|", "\\|").replace("`", "\\`")
            lines.append(f"| {description} | {row.report_count} | {row.interval_count} |")
    (out / "BRANDON_BROWN.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def reused_phrases(intervals: pd.DataFrame, wells: pd.DataFrame, out: Path) -> pd.DataFrame:
    merged = intervals.merge(wells[["wl_id", "bonded_full_name"]], left_on="well_id", right_on="wl_id", how="left", validate="many_to_one", indicator=True)
    if (merged._merge != "both").any():
        raise ValueError("Interval rows without well metadata")
    merged["bonded_full_name"] = merged.bonded_full_name.str.strip()
    merged = merged[usable_name(merged.bonded_full_name) & merged.material_raw.str.strip().ne("")].copy()
    reports_by_name = merged.groupby("bonded_full_name").well_id.nunique()
    eligible_names = set(reports_by_name[reports_by_name >= MIN_REPORTS].index)
    merged = merged[merged.bonded_full_name.isin(eligible_names)]
    phrases = merged.groupby(["bonded_full_name", "material_raw"]).agg(
        interval_count=("well_id", "size"), report_count=("well_id", "nunique")
    ).reset_index()
    phrases["reused_across_reports"] = phrases.report_count.ge(2)
    phrases["name_report_count"] = phrases.bonded_full_name.map(reports_by_name)
    phrases["share_of_name_reports"] = phrases.report_count / phrases.name_report_count
    phrases = phrases.sort_values(["bonded_full_name", "report_count", "interval_count", "material_raw"], ascending=[True, False, False, True])
    phrases.to_csv(out / "bonded_reused_descriptions.csv", index=False)

    summary_rows = []
    for name, block in phrases.groupby("bonded_full_name"):
        rows = merged[merged.bonded_full_name == name]
        reused = block[block.reused_across_reports]
        repeated_text = set(reused.material_raw)
        top = block.iloc[0]
        summary_rows.append({
            "bonded_full_name": name,
            "reports": int(reports_by_name[name]),
            "intervals": len(rows),
            "distinct_exact_phrases": len(block),
            "phrases_reused_in_2plus_reports": len(reused),
            "reports_with_a_reused_phrase": rows.loc[rows.material_raw.isin(repeated_text), "well_id"].nunique(),
            "intervals_with_a_reused_phrase": int(rows.material_raw.isin(repeated_text).sum()),
            "top_phrase": top.material_raw,
            "top_phrase_reports": int(top.report_count),
            "top_phrase_intervals": int(top.interval_count),
            "top_phrase_report_share": float(top.share_of_name_reports),
        })
    summary = pd.DataFrame(summary_rows).sort_values(["reports", "bonded_full_name"], ascending=[False, True])
    summary.to_csv(out / "bonded_reuse_summary.csv", index=False)
    write_named_example(phrases, summary, out)

    return summary


def spatial(locations: pd.DataFrame, wells: pd.DataFrame, interval_ids: set[str], out: Path) -> tuple[pd.DataFrame, dict]:
    if locations.wl_id.duplicated().any() or wells.wl_id.duplicated().any():
        raise ValueError("Report ID is not unique")
    if not set(locations.wl_id).issubset(interval_ids):
        raise ValueError("Location table contains a report absent from the combined interval table")
    location_cols = ["wl_id", "bonded_full_name", "location_class", "type_of_log", "complete_date_iso", "latitude_dec", "longitude_dec", "tr_key"]
    mapped = locations.merge(wells[location_cols], on="wl_id", how="left", validate="one_to_one", indicator=True)
    if (mapped._merge != "both").any():
        raise ValueError("Location without well metadata")
    if not (mapped.latitude.eq(mapped.latitude_dec) & mapped.longitude.eq(mapped.longitude_dec)).all():
        raise ValueError("Location CSV does not match OWRD source latitude/longitude")
    mapped["latitude"] = pd.to_numeric(mapped.latitude, errors="coerce")
    mapped["longitude"] = pd.to_numeric(mapped.longitude, errors="coerce")
    if mapped[["latitude", "longitude"]].isna().any().any() or not mapped.latitude.between(-90, 90).all() or not mapped.longitude.between(-180, 180).all():
        raise ValueError("Invalid location coordinate")
    mapped["bonded_full_name"] = mapped.bonded_full_name.str.strip()
    named = mapped[mapped.location_class.isin(["A", "B"]) & usable_name(mapped.bonded_full_name)].copy().sort_values("wl_id").reset_index(drop=True)
    primary = neighbor_stats(named, seed=SEED, stratify=False)
    conditional = neighbor_stats(named, seed=SEED + 1, stratify=True)
    conditional = conditional.drop(columns=["reports"]).rename(columns={col: "type_decade_" + col for col in conditional if col != "bonded_full_name"})
    primary = primary.merge(conditional, on="bonded_full_name", validate="one_to_one")

    # Coincident report points can create artificial zero-distance neighbours.
    pair_size = named.groupby(["latitude", "longitude"]).wl_id.transform("size")
    unique = named[pair_size == 1].copy()
    unique_stats = neighbor_stats(unique, seed=SEED + 2, stratify=False)
    unique_stats = unique_stats[["bonded_full_name", "reports", "observed_same_name_fraction", "null_mean_fraction", "enrichment_ratio"]].rename(columns={
        "reports": "unique_coordinate_reports",
        "observed_same_name_fraction": "unique_coordinate_observed_fraction",
        "null_mean_fraction": "unique_coordinate_null_mean_fraction",
        "enrichment_ratio": "unique_coordinate_enrichment_ratio",
    })
    primary = primary.merge(unique_stats, on="bonded_full_name", validate="one_to_one")
    primary = primary[primary.reports >= MIN_REPORTS].sort_values(["reports", "bonded_full_name"], ascending=[False, True])
    primary.loc[primary.unique_coordinate_reports < MIN_REPORTS, ["unique_coordinate_observed_fraction", "unique_coordinate_null_mean_fraction", "unique_coordinate_enrichment_ratio"]] = np.nan
    # Benjamini-Hochberg adjustment for the reported set of name-wise tests.
    pvalues = primary.one_sided_permutation_p.to_numpy()
    order = np.argsort(pvalues)
    adjusted_sorted = np.minimum.accumulate((pvalues[order] * len(pvalues) / np.arange(1, len(pvalues) + 1))[::-1])[::-1]
    adjusted = np.empty_like(adjusted_sorted)
    adjusted[order] = np.minimum(adjusted_sorted, 1)
    primary["bh_adjusted_q"] = adjusted
    primary.to_csv(out / "bonded_spatial_summary.csv", index=False)

    # Plot all source locations faintly; color only A/B names with >=10 points.
    names = primary.bonded_full_name.tolist()
    colors = dict(zip(names, plt.get_cmap("tab20").colors[: len(names)]))
    fig, ax = plt.subplots(figsize=(13, 8))
    weak = mapped[~mapped.location_class.isin(["A", "B"])]
    ax.scatter(weak.longitude, weak.latitude, s=8, c="#c8c8c8", alpha=0.35, label=f"Class C/D ({len(weak)})", linewidths=0)
    other = mapped[mapped.location_class.isin(["A", "B"]) & ~mapped.bonded_full_name.isin(names)]
    ax.scatter(other.longitude, other.latitude, s=12, c="#777777", alpha=0.45, label=f"Other A/B ({len(other)})", linewidths=0)
    for name in names:
        block = named[named.bonded_full_name == name]
        result = primary.loc[primary.bonded_full_name == name].iloc[0]
        ax.scatter(block.longitude, block.latitude, s=23, alpha=0.8, c=[colors[name]], linewidths=0,
                   label=f"{name} ({len(block)}, {result.enrichment_ratio:.1f}×)")
    lat_span = mapped.latitude.max() - mapped.latitude.min()
    lon_span = mapped.longitude.max() - mapped.longitude.min()
    ax.set_xlim(mapped.longitude.min() - 0.03 * lon_span, mapped.longitude.max() + 0.03 * lon_span)
    ax.set_ylim(mapped.latitude.min() - 0.03 * lat_span, mapped.latitude.max() + 0.03 * lat_span)
    ax.set_aspect(1 / math.cos(math.radians(mapped.latitude.mean())))
    ax.set(xlabel="Longitude (WGS84)", ylabel="Latitude (WGS84)", title="Structured-interval reports by exact bonded name")
    ax.grid(alpha=0.15)
    ax.legend(title="Bonded name (A/B reports, neighbour enrichment)", bbox_to_anchor=(1.01, 1), loc="upper left", frameon=False, fontsize=8, title_fontsize=9, markerscale=1.4)
    fig.tight_layout()
    fig.savefig(out / "bonded_locations.png", dpi=170, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 8))
    shown = primary.sort_values("enrichment_ratio")
    ax.barh(shown.bonded_full_name, shown.observed_same_name_fraction, color="#376a8a", label="Observed")
    ax.scatter(shown.null_mean_fraction, shown.bonded_full_name, marker="|", s=120, color="#bb6d26", label="Random-label mean", zorder=3)
    ax.set(xlabel="Fraction of five nearest report neighbours with the same bonded name", title="Local same-name concentration (class A/B)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / "bonded_neighbor_fraction.png", dpi=170)
    plt.close(fig)

    meta = {
        "mapped_interval_reports": len(mapped),
        "unmapped_interval_reports": len(interval_ids - set(mapped.wl_id)),
        "location_class_counts": mapped.location_class.value_counts().to_dict(),
        "named_ab_pool": len(named),
        "named_ab_values": named.bonded_full_name.nunique(),
        "eligible_spatial_names": len(primary),
        "named_ab_reports_at_repeated_coordinates": int((pair_size > 1).sum()),
        "named_ab_unique_coordinate_pool": len(unique),
        "permutations": N_PERMUTATIONS,
        "nearest_neighbors": K,
        "crs_for_distances": "EPSG:32611",
    }
    (out / "bonded_investigation_summary.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return primary, meta


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    out = root / "04_analysis/raw_lithology_profile"
    out.mkdir(parents=True, exist_ok=True)
    wells = pd.read_csv(root / "01_raw/owrd/wells_raw.csv", dtype=str, keep_default_na=False)
    intervals = pd.read_csv(root / "03_processed/lithology/lithology_all_raw.csv", dtype=str, keep_default_na=False)
    locations = pd.read_csv(root / "03_processed/wells/well_with_lithology.csv", dtype=str, keep_default_na=False)
    names = reused_phrases(intervals, wells, out)
    space, meta = spatial(locations, wells, set(intervals.well_id), out)
    print(f"Reuse profiles: {len(names)} names; spatial profiles: {len(space)} names")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
