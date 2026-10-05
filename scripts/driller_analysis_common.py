"""Auditable one-well cohort and approved driller-name normalization."""

from __future__ import annotations

import pandas as pd

EXCLUDED_NAME = "ZACHARY NEIGEL"
MIN_AB_WELLS = 10
ZOLLMAN_ALIASES = {"GARRY L ZOLLMAN", "GARRY ZOLLMAN"}
ZOLLMAN_LICENSE = "1881.0"


def canonical_name(name: str, license_number: str) -> str:
    name = name.strip()
    if name in ZOLLMAN_ALIASES:
        if license_number.strip() != ZOLLMAN_LICENSE:
            raise ValueError(f"Unexpected license for Zollman alias: {name}, {license_number}")
        return "GARRY ZOLLMAN"
    return name


def well_units(wells: pd.DataFrame, intervals: pd.DataFrame,
               location_audit: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Choose one geological report per tagged well; return units and report audit.

    Untagged reports retain individual report IDs because their physical-well
    identity cannot be established. Both new and abandonment flags can occur
    on the same report, so only abandonment-only reports are removed.
    """
    if wells.wl_id.duplicated().any() or location_audit.wl_id.duplicated().any():
        raise ValueError("Report IDs must be unique")
    report_ids = set(intervals.well_id)
    reports = wells[wells.wl_id.isin(report_ids)].copy()
    if len(reports) != len(report_ids):
        raise ValueError("Interval report missing from wells_raw.csv")
    reports = reports.merge(location_audit[["wl_id", "within_19_townships"]], on="wl_id",
                            how="left", validate="one_to_one")
    if reports.within_19_townships.isna().any():
        raise ValueError("Missing coordinate QC for an interval report")
    tag = reports.well_tag_nbr.str.strip()
    # County protects against possible tag reuse across county namespaces.
    reports["well_key"] = "tag:" + reports.wl_county_code.str.strip() + ":" + tag
    reports.loc[tag.eq(""), "well_key"] = "report:" + reports.loc[tag.eq(""), "wl_id"]
    reports["recorded_bonded_full_name"] = reports.bonded_full_name.str.strip()
    reports["bonded_full_name"] = [canonical_name(n, lic) for n, lic in
                                   zip(reports.bonded_full_name, reports.bonded_license_nbr)]
    reports["abandonment_only"] = reports.work_new.ne("1") & reports.work_abandonment.eq("1")
    reports["eligible_geology"] = reports.within_19_townships.eq(True) & ~reports.abandonment_only
    reports["interval_rows"] = reports.wl_id.map(intervals.well_id.value_counts()).astype(int)
    signatures = intervals.groupby("well_id").apply(
        lambda group: tuple(sorted(zip(group.from_ft, group.to_ft, group.material_raw))),
        include_groups=False,
    )
    reports["interval_signature"] = reports.wl_id.map(signatures)
    reports["selection_status"] = "linked_other_geology_report"
    reports.loc[reports.within_19_townships.eq(False), "selection_status"] = "outside_townships"
    reports.loc[reports.abandonment_only & reports.within_19_townships.eq(True),
                "selection_status"] = "abandonment_only"
    reports["selected_wl_id"] = ""
    reports["eligible_reports_for_well"] = reports.groupby("well_key").eligible_geology.transform("sum").astype(int)
    reports["different_geology_logs_for_well"] = False

    candidates = reports[reports.eligible_geology].copy()
    candidates["new_priority"] = candidates.work_new.ne("1").astype(int)
    candidates["location_priority"] = ~candidates.location_class.isin(["A", "B"])
    candidates["completion_sort"] = candidates.complete_date_iso.replace("", "9999-12-31")
    candidates["wl_id_sort"] = pd.to_numeric(candidates.wl_id, errors="raise")
    candidates = candidates.sort_values(
        ["well_key", "new_priority", "location_priority", "completion_sort", "wl_id_sort"],
        kind="stable",
    )
    chosen = candidates.drop_duplicates("well_key")
    chosen_id = chosen.set_index("well_key").wl_id
    reports["selected_wl_id"] = reports.well_key.map(chosen_id).fillna("")
    reports.loc[reports.wl_id.eq(reports.selected_wl_id), "selection_status"] = "selected"
    distinct_signatures = candidates.groupby("well_key").interval_signature.agg(lambda x: len(set(x)))
    conflicting = set(distinct_signatures[distinct_signatures.gt(1)].index)
    reports["different_geology_logs_for_well"] = reports.well_key.isin(conflicting)
    units = reports[reports.selection_status.eq("selected")].drop(columns=["interval_signature"]).copy()
    if units.well_key.duplicated().any():
        raise AssertionError("A physical well was selected more than once")
    audit = reports.drop(columns=["interval_signature"]).copy()
    return units, audit


def selected_drillers(units: pd.DataFrame) -> pd.DataFrame:
    """Canonical names with at least ten independent A/B lithology wells."""
    named = units[units.bonded_full_name.ne("") &
                  ~units.bonded_full_name.str.upper().str.match(r"^UNKNOWN(?:\s|$)") &
                  units.bonded_full_name.ne(EXCLUDED_NAME)]
    total = named.groupby("bonded_full_name").well_key.nunique().rename("lithology_wells")
    ab = named[named.location_class.isin(["A", "B"])].groupby("bonded_full_name").well_key.nunique().rename("ab_wells")
    cohort = pd.concat([total, ab], axis=1).fillna(0).astype(int)
    cohort = cohort[cohort.ab_wells >= MIN_AB_WELLS].sort_values(
        ["lithology_wells", "ab_wells"], ascending=False).reset_index()
    if cohort.empty:
        raise ValueError("No driller has enough independent A/B lithology wells")
    return cohort
