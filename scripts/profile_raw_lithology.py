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
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from driller_analysis_common import selected_drillers, well_units
from township_location_qc import SOURCE, audit_locations, outside_ids


ROOT = Path(__file__).resolve().parents[1]
IDENTITIES = ["owner_name", "bonded_full_name", "bonded_name_company", "bonded_license_nbr"]
UNKNOWN = {"UNKNOWN", "UNK", "N/A", "NA", "NONE", "NOT KNOWN", "NOT PROVIDED", "?"}


def comparison_key(value: str) -> str:
    return " ".join(value.split()).upper()


def identity_key(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def is_unknown(values: pd.Series) -> pd.Series:
    upper = values.str.strip().str.upper()
    return upper.isin(UNKNOWN) | upper.str.match(r"^UNKNOWN(?:\s|$)")


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    out = root / "04_analysis/raw_lithology_profile/artifacts"
    out.mkdir(parents=True, exist_ok=True)

    wells_path = root / "01_raw/owrd/wells_raw.csv"
    intervals_path = root / "03_processed/lithology/lithology_all_raw.csv"
    wells = pd.read_csv(wells_path, dtype=str, keep_default_na=False)
    intervals = pd.read_csv(intervals_path, dtype=str, keep_default_na=False)
    location_audit, _, _, boundary_hash = audit_locations(root, wells)
    write_csv(location_audit, out / "coordinate_qc.csv")
    excluded_ids = outside_ids(location_audit)
    units, well_audit = well_units(wells, intervals, location_audit)
    write_csv(well_audit, out / "well_report_audit.csv")
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

    # Candidate aliases use only identical punctuation-insensitive spelling or
    # a shared bonded license. Neither rule establishes a person's identity.
    alias_rows = []
    for field in IDENTITIES[:3]:
        values = wells[field].str.strip()
        table = (wells.assign(value=values).loc[values.ne("") & ~is_unknown(values)]
                 .groupby("value").agg(all_wells=("wl_id", "nunique")).reset_index())
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

    fig, ax = plt.subplots(figsize=(9, 5.5))
    top = raw_stats.head(15).iloc[::-1]
    ax.barh(top.material_raw, top.interval_count, color="#376a8a")
    ax.set(xlabel="Interval rows", title="Most frequent exact descriptions")
    fig.tight_layout()
    fig.savefig(out / "vocabulary.png", dpi=160)
    plt.close(fig)

    cohort = selected_drillers(units)
    write_csv(cohort, out / "driller_cohort.csv")
    fig, ax = plt.subplots(figsize=(10, max(6, 0.42 * len(cohort) + 1.5)))
    person_phrases_all = valid.merge(
        units[["wl_id", "bonded_full_name"]], left_on="well_id", right_on="wl_id",
        how="inner", validate="many_to_one", suffixes=("_source", ""),
    )
    person_phrases_all = person_phrases_all[person_phrases_all.bonded_full_name.isin(cohort.bonded_full_name)].copy()
    person_phrases_all["value"] = person_phrases_all.bonded_full_name
    phrase_counts = person_phrases_all.groupby(["value", "material_raw"]).agg(interval_count=("well_id", "size"), well_count=("well_id", "nunique")).reset_index()
    top_people = phrase_counts.groupby("value").agg(vocabulary_size=("material_raw", "size")).reset_index().sort_values("vocabulary_size")
    if len(top_people) != len(cohort):
        raise ValueError("Cohort and vocabulary profiles disagree")
    reused_counts = phrase_counts[phrase_counts.well_count >= 2].groupby("value").size()
    reused = top_people.value.map(reused_counts).fillna(0).astype(int)
    one_report = top_people.vocabulary_size - reused
    labels_by_name = cohort.set_index("bonded_full_name").lithology_wells
    labels = [f"{name} (n={labels_by_name[name]})" for name in top_people.value]
    ax.barh(labels, reused, color="#376a8a", label="Used in 2+ wells")
    ax.barh(labels, one_report, left=reused, color="#b9c4cc", label="Used in 1 well")
    for y, (blue, total) in enumerate(zip(reused, top_people.vocabulary_size)):
        ax.text(blue / 2 if blue >= 25 else blue + 1, y, str(blue),
                ha="center" if blue >= 25 else "left", va="center", fontsize=7.5,
                color="white" if blue >= 25 else "#263746", fontweight="bold")
        ax.text(total + 5, y, str(total), va="center", fontsize=8)
    ax.set_xlim(0, top_people.vocabulary_size.max() * 1.12)
    ax.set(xlabel="Distinct exact descriptions", title="Vocabulary size and reuse by driller")
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
        "qc": {flag: int(ordered[flag].sum()) for flag in flags}, "selected_drillers": len(cohort),
        "well_unit_qc": {"selected_geological_wells": len(units),
                         "untagged_selected_wells_using_report_id": int(units.well_tag_nbr.eq("").sum()),
                         "selection_status_counts": well_audit.selection_status.value_counts().to_dict(),
                         "different_geology_log_wells": int(well_audit.loc[well_audit.different_geology_logs_for_well, "well_key"].nunique())},
        "coordinate_qc": {"boundary_source": SOURCE, "boundary_sha256": boundary_hash,
                          "source_coordinates": int(location_audit.coordinate_basis.eq("source").sum()),
                          "map_fallback_coordinates": int(location_audit.coordinate_basis.eq("map_fallback").sum()),
                          "missing_coordinates": int(location_audit.coordinate_basis.eq("missing").sum()),
                          "outside_reports": len(excluded_ids),
                          "outside_interval_reports": int(len(excluded_ids & set(intervals.well_id)))},
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
