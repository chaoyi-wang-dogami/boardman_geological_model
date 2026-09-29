#!/usr/bin/env python3
"""Profile downloaded OWRD descriptions and associated report identities.

Run from any directory: uv run python scripts/profile_raw_lithology.py
Only derived files under 04_analysis/raw_lithology_profile are written.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from itertools import combinations
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
IDENTITIES = ["owner_name", "bonded_full_name", "bonded_name_company", "bonded_license_nbr"]
UNKNOWN = {"UNKNOWN", "UNK", "N/A", "NA", "NONE", "NOT KNOWN", "NOT PROVIDED", "?"}
MIN_WELLS = 10


def comparison_key(value: str) -> str:
    return " ".join(value.split()).upper()


def identity_key(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def is_unknown(values: pd.Series) -> pd.Series:
    upper = values.str.strip().str.upper()
    return upper.isin(UNKNOWN) | upper.str.match(r"^UNKNOWN(?:\s|$)")


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, index=False)


def fmt(value: float | int) -> str:
    return f"{value:,.0f}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    out = root / "04_analysis/raw_lithology_profile"
    out.mkdir(parents=True, exist_ok=True)

    wells_path = root / "01_raw/owrd/wells_raw.csv"
    intervals_path = root / "03_processed/lithology/lithology_all_raw.csv"
    wells = pd.read_csv(wells_path, dtype=str, keep_default_na=False)
    intervals = pd.read_csv(intervals_path, dtype=str, keep_default_na=False)
    required_wells = {"wl_id", "well_folder", "tr_key", "type_of_log", *IDENTITIES}
    required_intervals = {"well_id", "well_log", "interval_no", "from_ft", "to_ft", "thickness_ft", "material_raw"}
    if required_wells - set(wells) or required_intervals - set(intervals):
        raise ValueError(f"Missing columns: wells={required_wells-set(wells)}, intervals={required_intervals-set(intervals)}")
    if wells.wl_id.duplicated().any() or wells.well_folder.duplicated().any():
        raise ValueError("Well join keys are not unique; inspect wells_raw.csv before profiling")
    if (wells.wl_id == "").any() or (wells.well_folder == "").any():
        raise ValueError("Blank well join key")

    # Verify both source keys, rather than allowing a plausible but wrong one-key join.
    joined = intervals.merge(wells, how="left", left_on="well_id", right_on="wl_id", indicator=True, validate="many_to_one")
    joined["join_status"] = "matched"
    joined.loc[joined["_merge"] == "left_only", "join_status"] = "unmatched_well_id"
    joined.loc[(joined["_merge"] == "both") & (joined.well_log != joined.well_folder), "join_status"] = "folder_mismatch"
    unmatched = joined[joined.join_status != "matched"].copy()
    write_csv(unmatched[["well_id", "well_log", "interval_no", "join_status"]], out / "unmatched_intervals.csv")
    matched = joined[joined.join_status == "matched"].copy()
    matched_well_ids = set(matched.well_id)
    unmatched_wells = wells[~wells.wl_id.isin(matched_well_ids)]

    # Per-report files are the downloaded source for the combined interval table.
    per_well_paths = sorted((root / "01_raw/wells").glob("*/lithology.csv"))
    metadata_paths = sorted((root / "01_raw/wells").glob("*/metadata.json"))
    per_well_rows = 0
    per_well_nonempty = 0
    per_well_counts = {}
    source_rows = Counter()
    for path in per_well_paths:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        n = len(rows)
        source_rows.update(tuple(row.get(col, "") for col in intervals.columns) for row in rows)
        per_well_rows += n
        per_well_nonempty += n > 0
        per_well_counts[path.parent.name] = n
    metadata_key_mismatches = 0
    metadata_well_id_mismatches = 0
    folder_to_id = wells.set_index("well_folder").wl_id.to_dict()
    for path in metadata_paths:
        with path.open(encoding="utf-8") as handle:
            record = json.load(handle)
        metadata_key_mismatches += record.get("well_folder") != path.parent.name
        metadata_well_id_mismatches += str(record.get("wl_id", "")) != folder_to_id.get(path.parent.name, "")
    combined_folder_counts = intervals.well_log.value_counts().to_dict()
    per_well_count_mismatches = []
    for path in per_well_paths:
        n = per_well_counts[path.parent.name]
        if n != combined_folder_counts.get(path.parent.name, 0):
            per_well_count_mismatches.append((path.parent.name, n, combined_folder_counts.get(path.parent.name, 0)))
    write_csv(pd.DataFrame(per_well_count_mismatches, columns=["well_folder", "per_well_rows", "combined_rows"]), out / "source_count_mismatches.csv")
    combined_rows = Counter(map(tuple, intervals[list(intervals.columns)].itertuples(index=False, name=None)))
    source_row_disagreements = sum((source_rows - combined_rows).values()) + sum((combined_rows - source_rows).values())

    for col in ["from_ft", "to_ft", "thickness_ft"]:
        matched[col + "_num"] = pd.to_numeric(matched[col], errors="coerce")
    matched["calculated_thickness_ft"] = matched.to_ft_num - matched.from_ft_num
    matched["duplicate_full_row"] = matched.duplicated(subset=list(intervals.columns), keep=False)
    matched["duplicate_interval_key"] = matched.duplicated(subset=["well_id", "interval_no"], keep=False)
    matched["missing_description"] = matched.material_raw.str.strip().eq("")
    matched["invalid_bound"] = matched.from_ft_num.isna() | matched.to_ft_num.isna() | (matched.from_ft_num < 0) | (matched.to_ft_num < 0)
    matched["nonpositive_thickness"] = matched.calculated_thickness_ft.le(0)
    matched["recorded_thickness_mismatch"] = matched.thickness_ft_num.isna() | (matched.calculated_thickness_ft - matched.thickness_ft_num).abs().gt(0.01)
    ordered = matched.sort_values(["well_id", "from_ft_num", "to_ft_num", "interval_no"], kind="stable")
    ordered["previous_max_to_ft"] = ordered.groupby("well_id").to_ft_num.transform(lambda s: s.cummax().shift())
    ordered["overlap_with_previous"] = ordered.from_ft_num.lt(ordered.previous_max_to_ft - 0.01)
    ordered["gap_from_previous"] = ordered.from_ft_num.gt(ordered.previous_max_to_ft + 0.01)
    flags = ["duplicate_full_row", "duplicate_interval_key", "missing_description", "invalid_bound", "nonpositive_thickness", "recorded_thickness_mismatch", "overlap_with_previous", "gap_from_previous"]
    qc = ordered[["well_id", "well_log", "interval_no", "from_ft", "to_ft", "thickness_ft", "previous_max_to_ft", "material_raw", *flags]]
    write_csv(qc[qc[flags].any(axis=1)], out / "interval_qc.csv")

    matched["comparison_key"] = matched.material_raw.map(comparison_key)
    valid = matched[~matched.missing_description].copy()
    raw_stats = valid.groupby("material_raw", dropna=False).agg(interval_count=("well_id", "size"), distinct_wells=("well_id", "nunique"), thickness_ft=("calculated_thickness_ft", "sum")).reset_index().sort_values(["interval_count", "material_raw"], ascending=[False, True])
    key_stats = valid.groupby("comparison_key", dropna=False).agg(interval_count=("well_id", "size"), distinct_wells=("well_id", "nunique"), thickness_ft=("calculated_thickness_ft", "sum"), raw_variants=("material_raw", "nunique")).reset_index().sort_values(["interval_count", "comparison_key"], ascending=[False, True])
    variants = valid.groupby(["comparison_key", "material_raw"]).agg(interval_count=("well_id", "size"), distinct_wells=("well_id", "nunique")).reset_index()
    variants = variants[variants.comparison_key.isin(key_stats.loc[key_stats.raw_variants > 1, "comparison_key"])].sort_values(["comparison_key", "interval_count"], ascending=[True, False])
    for name, frame in [("raw_descriptions", raw_stats), ("comparison_keys", key_stats), ("collapsed_variants", variants)]:
        write_csv(frame, out / f"{name}.csv")

    # All four fields are independent report attributes. The same interval can
    # contribute to one value in each role; blank/unknown values are omitted.
    summaries = []
    identity_rows = []
    for field in IDENTITIES:
        values = wells[field].str.strip()
        blank = values.eq("")
        unknown = is_unknown(values)
        attached = matched.assign(identity_value=matched[field].str.strip())
        attached = attached[(attached.identity_value != "") & ~is_unknown(attached.identity_value)]
        counts = attached.groupby("identity_value").agg(interval_count=("well_id", "size"), interval_wells=("well_id", "nunique"))
        wc = wells.assign(identity_value=values).loc[~(blank | unknown)].groupby("identity_value").agg(all_wells=("wl_id", "nunique"))
        table = wc.join(counts, how="left").fillna(0).astype(int).reset_index().rename(columns={"identity_value": "value"})
        table.insert(0, "field", field)
        identity_rows.append(table)
        summaries.append({"field": field, "all_wells": len(wells), "blank_wells": int(blank.sum()), "unknown_wells": int(unknown.sum()), "nonblank_distinct_values": values[~(blank | unknown)].nunique(), "interval_wells_with_value": attached.well_id.nunique(), "intervals_with_value": len(attached), "interval_wells_missing_or_unknown": matched.well_id.nunique() - attached.well_id.nunique(), "intervals_missing_or_unknown": len(matched) - len(attached)})
    identity_counts = pd.concat(identity_rows, ignore_index=True)
    write_csv(identity_counts.sort_values(["field", "interval_count"], ascending=[True, False]), out / "identity_values.csv")
    write_csv(pd.DataFrame(summaries), out / "identity_summary.csv")

    # Candidate aliases use only identical punctuation-insensitive spelling or
    # a shared bonded license. Neither rule establishes a person's identity.
    alias_rows = []
    for field in IDENTITIES[:3]:
        table = identity_counts[identity_counts.field == field].copy()
        table["alias_key"] = table.value.map(identity_key)
        for key, group in table.groupby("alias_key"):
            if key and len(group) > 1:
                alias_rows.append({"field": field, "basis": "same letters/digits after punctuation and spaces removed", "evidence_key": key, "values": " | ".join(group.value), "all_wells": int(group.all_wells.sum())})
    license_names = wells.assign(name=wells.bonded_full_name.str.strip(), license=wells.bonded_license_nbr.str.strip())
    license_names = license_names[(license_names.name != "") & ~is_unknown(license_names.name) & (license_names.license != "")].drop_duplicates(["license", "name"])
    for license_no, group in license_names.groupby("license"):
        if group.name.nunique() > 1:
            alias_rows.append({"field": "bonded_full_name", "basis": "shared bonded_license_nbr; review license reuse and names", "evidence_key": license_no, "values": " | ".join(sorted(group.name)), "all_wells": int(wells[wells.bonded_license_nbr == license_no].shape[0])})
    write_csv(pd.DataFrame(alias_rows, columns=["field", "basis", "evidence_key", "values", "all_wells"]), out / "suspected_aliases.csv")

    # One report supplies at most one value per field. Count a phrase once per
    # report for well frequency, even if repeated in multiple intervals.
    profiles = []
    phrase_rows = []
    for field in IDENTITIES[:3]:
        eligible = identity_counts[(identity_counts.field == field) & (identity_counts.interval_wells >= MIN_WELLS)].value
        field_data = valid[valid[field].str.strip().isin(set(eligible))].copy()
        field_data["value"] = field_data[field].str.strip()
        group_phrase = field_data.groupby(["value", "material_raw"]).agg(interval_count=("well_id", "size"), well_count=("well_id", "nunique")).reset_index()
        prevalence = valid.loc[valid[field].str.strip().ne("") & ~is_unknown(valid[field])].groupby("material_raw")[field].nunique()
        group_phrase["other_values_use_phrase"] = group_phrase.material_raw.map(prevalence).gt(1)
        group_phrase.insert(0, "field", field)
        phrase_rows.append(group_phrase)
        for value, group in group_phrase.groupby("value"):
            n_intervals = int(group.interval_count.sum())
            n_wells = int(field_data.loc[field_data.value == value, "well_id"].nunique())
            p = group.interval_count / n_intervals
            top = group.sort_values("interval_count", ascending=False).head(3)
            profiles.append({"field": field, "value": value, "well_count": n_wells, "interval_count": n_intervals, "vocabulary_size": len(group), "single_interval_phrases": int((group.interval_count == 1).sum()), "phrases_used_in_2plus_wells": int((group.well_count >= 2).sum()), "unique_to_value_phrases": int((~group.other_values_use_phrase).sum()), "shared_phrases": int(group.other_values_use_phrase.sum()), "top_phrase_interval_share": float(p.max()), "simpson_concentration": float((p**2).sum()), "top_phrases": " | ".join(f"{r.material_raw} ({r.interval_count} intervals; {r.well_count} wells)" for r in top.itertuples())})
    profiles = pd.DataFrame(profiles).sort_values(["field", "well_count"], ascending=[True, False])
    phrase_frequency = pd.concat(phrase_rows, ignore_index=True).sort_values(["field", "value", "interval_count"], ascending=[True, True, False])
    write_csv(profiles, out / "naming_profiles.csv")
    write_csv(phrase_frequency, out / "identity_phrase_frequencies.csv")

    # A pair is comparable only when both logged at least 5 wells of the same
    # report type in the same township, completion decade, and depth bin. Coarse
    # covariates; the shared geology of specific intervals is still unverified.
    stratum_wells = wells.copy()
    stratum_wells["year"] = pd.to_numeric(stratum_wells.complete_date_iso.str[:4], errors="coerce")
    stratum_wells["decade"] = (stratum_wells.year // 10 * 10).astype("Int64")
    depth = pd.to_numeric(stratum_wells.completed_depth, errors="coerce")
    stratum_wells["depth_bin"] = pd.cut(depth, [-0.01, 100, 300, 600, float("inf")], labels=["0-100", "100-300", "300-600", "600+"])
    overlap_rows = []
    for field in ["bonded_full_name", "bonded_name_company"]:
        candidate = stratum_wells[stratum_wells.wl_id.isin(matched_well_ids)].copy()
        candidate["value"] = candidate[field].str.strip()
        candidate = candidate[candidate.value.isin(set(profiles.loc[profiles.field == field, "value"])) & candidate.decade.notna() & candidate.depth_bin.notna()]
        strata = candidate.groupby(["type_of_log", "tr_key", "decade", "depth_bin", "value"], observed=True).wl_id.nunique().reset_index(name="wells")
        for (report_type, township, decade, depth_bin), block in strata.groupby(["type_of_log", "tr_key", "decade", "depth_bin"], observed=True):
            block = block[block.wells >= 5]
            for a, b in combinations(block.itertuples(), 2):
                def phrases_for(value: str) -> set[str]:
                    ids = candidate.loc[(candidate.value == value) & (candidate.type_of_log == report_type) & (candidate.tr_key == township) & (candidate.decade == decade) & (candidate.depth_bin == depth_bin), "wl_id"]
                    return set(valid.loc[valid.well_id.isin(ids), "material_raw"])

                ap, bp = phrases_for(a.value), phrases_for(b.value)
                overlap_rows.append({"field": field, "report_type": report_type, "township": township, "decade": int(decade), "completed_depth_bin_ft": str(depth_bin), "value_a": a.value, "wells_a": a.wells, "value_b": b.value, "wells_b": b.wells, "shared_exact_phrases": len(ap & bp), "phrase_jaccard": len(ap & bp) / len(ap | bp) if ap | bp else 0, "example_a_only": " | ".join(sorted(ap - bp)[:3]), "example_b_only": " | ".join(sorted(bp - ap)[:3])})
    overlap = pd.DataFrame(overlap_rows, columns=["field", "report_type", "township", "decade", "completed_depth_bin_ft", "value_a", "wells_a", "value_b", "wells_b", "shared_exact_phrases", "phrase_jaccard", "example_a_only", "example_b_only"])
    write_csv(overlap, out / "overlap_review.csv")

    inventory = pd.DataFrame([
        {"source": str(wells_path.relative_to(root)), "records": len(wells), "distinct_reports": wells.wl_id.nunique(), "scope": "all three report types, 19 configured townships"},
        {"source": "01_raw/wells/*/metadata.json", "records": len(metadata_paths), "distinct_reports": len(metadata_paths), "scope": "downloaded report folders"},
        {"source": "01_raw/wells/*/lithology.csv", "records": per_well_rows, "distinct_reports": per_well_nonempty, "scope": f"{len(per_well_paths)} files; nonempty reports only in distinct_reports"},
        {"source": str(intervals_path.relative_to(root)), "records": len(intervals), "distinct_reports": intervals.well_id.nunique(), "scope": "structured intervals with bounds and nonblank description"},
    ])
    write_csv(inventory, out / "inventory.csv")
    by_type = wells.groupby("type_of_log").agg(all_reports=("wl_id", "nunique"), interval_reports=("wl_id", lambda ids: ids.isin(matched_well_ids).sum())).reset_index()
    by_type["interval_rows"] = by_type.type_of_log.map(matched.type_of_log.value_counts()).fillna(0).astype(int)
    write_csv(by_type, out / "scope_by_report_type.csv")

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    top = raw_stats.head(15).iloc[::-1]
    axes[0].barh(top.material_raw, top.interval_count, color="#376a8a")
    axes[0].set(xlabel="Intervals", title="Most frequent exact descriptions")
    bins = [1, 2, 3, 5, 10, 20, 50, 100, float("inf")]
    labels = ["1", "2", "3-4", "5-9", "10-19", "20-49", "50-99", "100+"]
    bucket = pd.cut(raw_stats.interval_count, bins=[0, *bins[1:]], labels=labels)
    axes[1].bar(labels, bucket.value_counts().reindex(labels, fill_value=0), color="#b78349")
    axes[1].set(xlabel="Intervals per exact description", ylabel="Number of descriptions", title="Long tail of descriptions")
    axes[1].tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig(out / "vocabulary.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 4.5))
    top_people = profiles[profiles.field == "bonded_full_name"].nlargest(12, "well_count").iloc[::-1]
    person_phrases = phrase_frequency[phrase_frequency.field == "bonded_full_name"]
    reused_counts = person_phrases[person_phrases.well_count >= 2].groupby("value").size()
    reused = top_people.value.map(reused_counts).fillna(0).astype(int)
    one_report = top_people.vocabulary_size - reused
    ax.barh(top_people.value, reused, color="#376a8a", label="Used in 2+ reports")
    ax.barh(top_people.value, one_report, left=reused, color="#b9c4cc", label="Used in 1 report")
    for y, total in enumerate(top_people.vocabulary_size):
        ax.text(total + 5, y, str(total), va="center", fontsize=8)
    ax.set_xlim(0, top_people.vocabulary_size.max() * 1.12)
    ax.set(xlabel="Distinct exact descriptions", title="Vocabulary size and report reuse by bonded name")
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "bonded_vocabulary.png", dpi=160)
    plt.close(fig)

    summary = {
        "all_reports": len(wells), "townships": wells.tr_key.nunique(), "intervals": len(intervals), "interval_reports": intervals.well_id.nunique(),
        "matched_intervals": len(matched), "unmatched_intervals": len(unmatched), "reports_without_intervals": len(unmatched_wells),
        "per_well_files": len(per_well_paths), "metadata_files": len(metadata_paths), "per_well_rows": per_well_rows,
        "per_well_count_mismatches": len(per_well_count_mismatches), "source_row_disagreements": source_row_disagreements, "metadata_folder_mismatches": metadata_key_mismatches, "metadata_well_id_mismatches": metadata_well_id_mismatches,
        "distinct_raw": len(raw_stats), "distinct_keys": len(key_stats), "keys_with_variants": int((key_stats.raw_variants > 1).sum()),
        "singletons": int((raw_stats.interval_count == 1).sum()), "rare_2_to_4": int(raw_stats.interval_count.between(2, 4).sum()),
        "qc": {flag: int(ordered[flag].sum()) for flag in flags}, "overlap_strata": len(overlap),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
