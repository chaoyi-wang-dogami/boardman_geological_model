"""Audit source-depth ordering and update provisional sediment and parent G codes.

Uses only the standard library. Does not edit authoritative CSVs or the XLS.
Run from any directory. Numeric facies codes are not correlation hypotheses.
"""
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
PACKAGE = ROOT / "input/35_paired_spread"
SOURCE = REPO / "03_processed/boardman_19_townships/boardman_wells_stratigraphy.csv"
PROPOSAL = PACKAGE / "proposed_stratigraphy_order_and_styles.csv"
REFERENCES = {
    "alkali": "https://pubs.oregon.gov/dogami/og/OGv43n10.pdf",
    "geolex": "https://ngmdb.usgs.gov/Geolex/UnitRefs/AlkaliCanyonRefs_4537.html",
    "burns": "https://www.usgs.gov/publications/three-dimensional-model-geologic-framework-columbia-plateau-regional-aquifer-system",
    "interflood_loess": "https://www.usgs.gov/publications/case-periodic-colossal-jokulhlaups-pleistocene-glacial-lake-missoula",
    "rockworks": "https://help.rockware.com/rockworks/WebHelp/table_stratigraphy.htm",
}


def read(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def write(path, rows, fields):
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def family(label):
    if label.startswith("Sediment.MissoulaFlood"):
        return "MissoulaFlood"
    if label.startswith("Crbg"):
        return "CRBG"
    return label


def relation(a, b):
    if float(a["end_depth"]) <= float(b["start_depth"]):
        return "above_or_touching"
    if float(b["end_depth"]) <= float(a["start_depth"]):
        return "below_or_touching"
    return "overlapping"


def main():
    before = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    rows = read(SOURCE)
    selected = {r["well_id"] for r in read(PACKAGE / "selected_wells.csv")}
    reports = defaultdict(list)
    for n, row in enumerate(rows, 2):
        row["source_csv_row"] = n
        reports[row["well_id"]].append(row)
    targets = {"MissoulaFlood", "Sediment.Loess", "AlkaliCanyonFm",
               "Sediment.AlluvialFan", "Sediment.PostCrb"}
    pairs = []
    adjacency = []
    for well, intervals in reports.items():
        ordered = sorted(intervals, key=lambda r: float(r["start_depth"]))
        for a, b in zip(ordered, ordered[1:]):
            if family(a["strat_unit"]) in targets and family(b["strat_unit"]) in targets:
                adjacency.append({"well_id": well, "gw_site_id": a["gw_site_id"],
                    "selected_35": well in selected,
                    "shallower_label": a["strat_unit"], "deeper_label": b["strat_unit"],
                    "shallower_source_row": a["source_csv_row"], "deeper_source_row": b["source_csv_row"],
                    "relation": relation(a, b)})
        for a in intervals:
            if family(a["strat_unit"]) not in targets:
                continue
            for b in intervals:
                if family(b["strat_unit"]) != "CRBG":
                    continue
                pairs.append({"well_id": well, "gw_site_id": a["gw_site_id"],
                    "selected_35": well in selected, "sediment_family": family(a["strat_unit"]),
                    "sediment_label": a["strat_unit"], "sediment_top_ft": a["start_depth"],
                    "sediment_bottom_ft": a["end_depth"], "sediment_source_row": a["source_csv_row"],
                    "basalt_label": b["strat_unit"], "basalt_top_ft": b["start_depth"],
                    "basalt_bottom_ft": b["end_depth"], "basalt_source_row": b["source_csv_row"],
                    "relation": relation(a, b)})
    write(PACKAGE / "sediment_vs_basalt_depth_audit.csv", pairs, list(pairs[0]))
    write(PACKAGE / "sediment_adjacency_audit.csv", adjacency, list(adjacency[0]))
    summary = {"source_sha256": before, "depth_units": "feet as recorded",
        "method": "Compare every targeted sediment interval with every CRBG interval in each report; count each report and GWIS site separately. Linked reports are not independent evidence.",
        "references": REFERENCES, "scopes": {}}
    for scope in ("selected_35", "full_19_townships"):
        subset = [p for p in pairs if scope != "selected_35" or p["selected_35"]]
        stats = {}
        for target in sorted(targets):
            ps = [p for p in subset if p["sediment_family"] == target]
            bad = [p for p in ps if p["relation"] != "above_or_touching"]
            stats[target] = {"cooccurring_reports": len({p["well_id"] for p in ps}),
                "cooccurring_gwis_sites": len({p["gw_site_id"] for p in ps}),
                "reports_not_entirely_above_basalt": sorted({p["well_id"] for p in bad})}
        summary["scopes"][scope] = stats
    summary["example_repeat"] = {"well_id": "UMAT_0002307", "sequence_ft":
        [[r["strat_unit"], float(r["start_depth"]), float(r["end_depth"])]
        for r in sorted(reports["UMAT_0002307"], key=lambda r: float(r["start_depth"]))]}
    weather_label = "Crbg.Undifferentiated.WeatheredFlowTop"
    weather = [r for r in rows if r["strat_unit"] == weather_label]
    summary["weathered_flow_top_prevalence"] = {
        "source_label": weather_label,
        "intervals": len(weather),
        "reports": len({r["well_id"] for r in weather}),
        "gwis_sites": len({r["gw_site_id"] for r in weather}),
        "all_stratigraphy_reports": len(reports),
        "all_stratigraphy_gwis_sites": len({r["gw_site_id"] for r in rows}),
        "selected_reports": sorted({r["well_id"] for r in weather if r["well_id"] in selected}),
        "min_thickness_ft": min(float(r["end_depth"]) - float(r["start_depth"]) for r in weather),
        "max_thickness_ft": max(float(r["end_depth"]) - float(r["start_depth"]) for r in weather),
    }
    proposal = read(PROPOSAL)
    codes = {"Sediment.Loess": (10, 10, "#E8D7A0"),
        "Sediment.AlluvialFan": (20, 20, "#D2B48C"),
        "Sediment.MissoulaFlood.Coarse": (31, 30, "#C59B55"),
        "Sediment.MissoulaFlood.Fine": (32, 30, "#F0DBAC"),
        "Sediment.MissoulaFlood.Gravel": (33, 30, "#A87940"),
        "Sediment.MissoulaFlood.Sand": (34, 30, "#DFC17F"),
        "Sediment.MissoulaFlood.Silt": (35, 30, "#EAD3AE"),
        "Sediment.MissoulaFlood.general": (36, 30, "#BDBDBD"),
        "Sediment.PostCrb": (40, 40, "#A9B99A"),
        "AlkaliCanyonFm": (50, 50, "#B7C982")}
    for row in proposal:
        row.setdefault("family_G_reference_only", "")
        row.setdefault("order_basis", "literature_relative_sequence" if row["proposed_order_G"] else "representation_pending")
        if row["formation"] not in codes:
            continue
        g, fam, color = codes[row["formation"]]
        row.update(proposed_order_G=str(g), family_G_reference_only=str(fam), proposed_color_hex=color)
        row["evidence"] = REFERENCES["alkali"] + " ; sediment_vs_basalt_depth_audit.csv ; sediment_adjacency_audit.csv"
        if row["formation"].startswith("Sediment.MissoulaFlood"):
            row["status"] = "provisional_unique_facies_code_user_authorized"
            row["order_basis"] = "family_above_basalt_supported_within_family_order_arbitrary"
            row["review_note"] = "Family 30 is bookkeeping only, not a RockWorks hierarchy field. Codes 31-36 do not assert facies order, synonymy, or a merge. Repeated facies retained. Disable order-based truncation/filling for diagnostic trial. .general is resolved at parent level."
        elif row["formation"] == "Sediment.PostCrb":
            row["status"] = "provisional_broad_sediment_code"
            row["order_basis"] = "sample_order_only_full_dataset_exception"
            row["review_note"] = "Broad post-CRBG label retained; not necessarily a separate unit from Alkali Canyon or Quaternary sediments. Full dataset UMAT_0002049 alternates PostCrb and basalt; retain flagged exception."
        elif row["formation"] == "Sediment.AlluvialFan":
            row["status"] = "provisional_display_position"
            row["order_basis"] = "below_loess_in_one_selected_report_other_relations_untested"
            row["review_note"] = "Observed below loess and above basalt in UMAT_0056806; repeated label retained. Position relative to Missoula Flood not established."
        elif row["formation"] == "Sediment.Loess":
            row["status"] = "proposed_sample_supported_position"
            row["order_basis"] = "sample_loess_cap_not_universal_age_order"
            row["review_note"] = "Selected wells show loess above flood or fan deposits; regional literature also records loess between flood beds. Do not enforce this position universally."
        else:
            row["status"] = "proposed_literature_and_depth_supported_position"
            row["order_basis"] = "above_CRBG_and_below_Quaternary_deposits"
            row["review_note"] = "Post-basalt late Miocene to early Pliocene(?) formation; can rest on different basalt members or exposed Ellensburg interbeds. Not synonymous with a particular Missoula Flood facies."
    parent_codes = {
        "Crbg.Undifferentiated.general": (91, 90, "Resolved CRBG interpretation; named formation unspecified. Family 90 is a reserved broad-CRBG code range, not a position above all named basalts."),
        "Crbg.Wb.PriestRapids.general": (161, 160, "Resolved Priest Rapids interpretation; encompasses member-level evidence without choosing Lolo, Rosalia, or an extra layer."),
        "Crbg.Wb.FrenchmanSprings.general": (201, 200, "Resolved Frenchman Springs interpretation; named flow unspecified. Not a separate flow between Sentinel Gap and Sand Hollow."),
        "Crbg.Grb.general": (251, 250, "Resolved Grande Ronde interpretation; magnetostratigraphic subdivision unspecified. Not evidence for a distinct layer beneath N2."),
    }
    for row in proposal:
        label = row["formation"]
        if label == weather_label:
            row.update(proposed_order_G="92", family_G_reference_only="90",
                status="provisional_weathered_basalt_code_user_authorized",
                order_basis="within_family_code_arbitrary_not_regional_horizon",
                evidence="User instruction: assign numeric code; authoritative source-label frequency in sediment_order_audit_summary.json.",
                review_note="Weathered basalt interval with named formation unspecified. Family 90 reserved for undifferentiated CRBG. Code 92 does not establish position relative to general basalt or named members; retain original tops and bottoms. Not automatically a thin regional weathering horizon.")
        if label.startswith("Crbg.Wb.PriestRapids."):
            row["family_G_reference_only"] = "160"
        elif label.startswith("Crbg.Wb.FrenchmanSprings."):
            row["family_G_reference_only"] = "200"
        elif label.startswith("Crbg.Grb."):
            row["family_G_reference_only"] = "250"
        if label not in parent_codes:
            continue
        g, fam, note = parent_codes[label]
        row.update(proposed_order_G=str(g), family_G_reference_only=str(fam),
            status="provisional_resolved_parent_code_user_authorized",
            order_basis="within_family_code_arbitrary_not_extra_layer",
            evidence="User instruction: assign resolved parent interpretations unique numbers within their family.",
            review_note=note + " Numeric code assigned by user-authorized family convention. Keep original labels and contacts; family reference is bookkeeping only. Order-based truncation/filling must not infer a separate parent layer.")
    assigned = [r["proposed_order_G"] for r in proposal if r["proposed_order_G"]]
    assert len(assigned) == len(set(assigned)), "Proposed G codes must be unique"
    assert len(proposal) == 31 and all(r["proposed_order_G"] for r in proposal)
    assert all(r["proposed_order_G"] for r in proposal if r["formation"] in parent_codes)
    assert not any(r["status"] == "resolved_parent_or_broad_interpretation_no_unique_flat_G" for r in proposal)
    write(PROPOSAL, proposal, list(proposal[0]))
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == before
    (PACKAGE / "sediment_order_audit_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary["scopes"], indent=2))
    print("Updated 10 sediment, 4 parent, and 1 weathered-basalt code; all 31 labels have unique G values; source CSV and XLS unchanged.")


if __name__ == "__main__":
    main()
