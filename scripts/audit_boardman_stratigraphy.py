"""Exploratory, lossless Boardman sequence audit; no geological corrections.

Run: python3 scripts/audit_boardman_stratigraphy.py
Only standard-library modules are required. CSV source_row is a one-based CSV
record ordinal including the header, not a physical line number in multiline CSV.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "03_processed/boardman_19_townships"
OUTPUT = ROOT / "04_analysis/stratigraphy_sequences/artifacts"
VERSION = "1.0"
SCIENTIFIC = (
    "start_depth", "end_depth", "start_depth_elev", "end_depth_elev",
    "depth_thickness", "strat_unit", "sample_source", "picked_by", "est_age",
    "est_age_error",
)
GEOMETRY = ("strat_unit", "start_depth", "end_depth")
NUMERIC = {"start_depth", "end_depth", "start_depth_elev", "end_depth_elev",
           "depth_thickness", "est_age", "est_age_error"}
REFERENCES = {
    "group": "https://www.usgs.gov/observatories/cvo/science/columbia-river-basalt-group-stretches-oregon-idaho",
    "regional_order": "https://pubs.usgs.gov/wri/1987/4268/report.pdf",
    "frenchman": "https://ngmdb.usgs.gov/Geolex/UnitRefs/FrenchmanSpringsRefs_5359.html",
    "sentinel_gap": "https://ngmdb.usgs.gov/Geolex/Units/SentinelGap_16757.html",
    "sentinel_bluffs": "https://ngmdb.usgs.gov/Geolex/Units/SentinelBluffs_16754.html",
    "winter_water": "https://pubs.usgs.gov/of/1999/0141/readme.html",
    "polarity": "https://www.usgs.gov/publications/regional-correlation-grande-ronde-basalt-flows-columbia-river-basalt-group-washington",
    "priest_rapids": "https://pubs.usgs.gov/of/1981/0797/report.pdf",
}
ISSUE_CLASS = {
    "missing_depth": "verified_numeric_issue", "invalid_depth": "verified_numeric_issue",
    "negative_depth": "verified_numeric_issue", "reversed_depth": "verified_numeric_issue",
    "zero_thickness": "verified_numeric_issue", "thickness_mismatch": "verified_numeric_issue",
    "missing_thickness": "verified_metadata_gap", "invalid_thickness": "verified_numeric_issue",
    "missing_elevation": "verified_metadata_gap", "invalid_elevation": "verified_numeric_issue",
    "elevation_thickness_mismatch": "verified_numeric_issue",
    "implied_surface_inconsistent": "verified_numeric_issue",
    "gap": "verified_geometry", "overlap": "verified_geometry",
    "duplicate_interval": "review_required", "repeated_unit": "review_required",
    "parent_child_mixed": "review_required", "unexpected_order": "review_required",
    "first_pick_below_zero": "coverage_note", "beyond_report_depth": "review_required",
    "nonpositive_report_depth": "verified_metadata_issue",
    "linked_report_conflict": "review_required", "linked_report_metadata_difference": "provenance_note",
    "lithology_named_unit_disagreement": "review_required",
    "broad_named_basalt_mixed": "review_required",
}
NAME_PATTERNS = {
    "EllensburgFm.Selah": r"\bselah\b", "EllensburgFm.Mabton": r"\bmabton\b",
    "EllensburgFm.RattlesnakeRidge": r"\brattlesnake[\s-]+ridge\b", "EllensburgFm.Vantage": r"\bvantage\b",
    "EllensburgFm.Quincy-SquawCreek": r"\bquincy[\s-]+squaw[\s-]+creek\b",
    "EllensburgFm.SquawCreek": r"(?<!quincy-)\bsquaw[\s-]+creek\b", "EllensburgFm.Byron": r"\bbyron\b",
    "Crbg.Smb.ElephantMtn": r"\belephant[\s-]+(?:mountain|mtn)\b", "Crbg.Smb.Pomona": r"\bpomona\b",
    "Crbg.Smb.Umatilla": r"\bumatilla\b", "Crbg.Wb.PriestRapids.Lolo": r"\blolo\b",
    "Crbg.Wb.PriestRapids.Rosalia": r"\brosalia\b", "Crbg.Wb.FrenchmanSprings.Ginkgo": r"\bginkgo\b",
    "Crbg.Wb.FrenchmanSprings.SilverFalls": r"\bsilver[\s-]+falls\b",
    "Crbg.Wb.FrenchmanSprings.SandHollow": r"\bsand[\s-]+hollow\b",
    "Crbg.Wb.FrenchmanSprings.SentinelGap": r"\bsentinel[\s-]+gap\b",
    "Crbg.Grb.N2.SentinelBluffs": r"\bsentinel[\s-]+bluffs\b",
    "Crbg.Grb.N2.WinterWater": r"\bwinter[\s-]*water\b", "AlkaliCanyonFm": r"\balkali[\s-]+canyon\b",
}


def number(value):
    """Blank and nonfinite numbers are distinct flags; retain the original text."""
    if value is None or not str(value).strip():
        return None
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        return None
    return result if result.is_finite() else None


def decimal_text(value):
    return "" if value is None else format(value, "f")


def packed(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    if any(None in row or any(v is None for v in row.values()) for row in rows):
        raise ValueError(f"Malformed CSV record in {path}")
    for ordinal, row in enumerate(rows, 2):
        row["source_row"] = ordinal
    return rows, fields


def write(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def cell_signature(row, fields, numeric=False):
    return tuple(str(number(row[k]).normalize()) if numeric and k in NUMERIC
                 and number(row[k]) is not None else row[k] for k in fields)


def sequence_signature(rows, fields=SCIENTIFIC, numeric=False):
    # A multiset preserves repeated occurrences. Do not use a set of intervals.
    return tuple(sorted(cell_signature(row, fields, numeric) for row in rows))


def variants(reports):
    grouped = defaultdict(list)
    for well, rows in sorted(reports.items()):
        grouped[sequence_signature(rows)].append(well)
    return sorted(grouped.values(), key=lambda wells: wells[0])


def ordered(rows):
    return sorted(rows, key=lambda r: (number(r["start_depth"]) is None,
        number(r["start_depth"]) or Decimal(0), number(r["end_depth"]) is None,
        number(r["end_depth"]) or Decimal(0), r["strat_unit"], r["source_row"]))


def hierarchy_info(label, labels):
    """A label path expresses containment, not automatically formal rank."""
    leaf = label.split(".")[-1]
    rank, display, ref = "unresolved_label", label, ""
    if label == "Crbg":
        rank, display, ref = "group", "Columbia River Basalt Group", REFERENCES["group"]
    elif label in {"Crbg.Grb", "Crbg.Wb", "Crbg.Smb"}:
        rank = "formation"
        display = {"Crbg.Grb": "Grande Ronde Basalt", "Crbg.Wb": "Wanapum Basalt",
                   "Crbg.Smb": "Saddle Mountains Basalt"}[label]
        ref = REFERENCES["group"]
    elif label in {"AlkaliCanyonFm", "EllensburgFm"}:
        rank = "formation_from_label"
        display = {"AlkaliCanyonFm": "Alkali Canyon Formation", "EllensburgFm": "Ellensburg Formation"}[label]
    elif label == "Crbg.Grb.N2":
        rank, display, ref = "magnetostratigraphic_unit", "N2 normal-polarity interval", REFERENCES["polarity"]
    elif label in {"Crbg.Grb.N2.SentinelBluffs", "Crbg.Grb.N2.WinterWater"}:
        rank, display = "member", "Sentinel Bluffs Member" if leaf == "SentinelBluffs" else "Winter Water Member"
        ref = REFERENCES["sentinel_bluffs"] if leaf == "SentinelBluffs" else REFERENCES["winter_water"]
    elif label.startswith("Crbg.Smb.") or label in {"Crbg.Wb.FrenchmanSprings", "Crbg.Wb.PriestRapids"}:
        rank, ref = "member_draft", REFERENCES["regional_order"]
    elif label.startswith("Crbg.Wb.FrenchmanSprings."):
        rank, ref = "informal_flow_unit_or_flow_package", REFERENCES["frenchman"]
    elif label.startswith("Crbg.Wb.PriestRapids."):
        rank, ref = "flow_chemical_type_or_flow_package", REFERENCES["priest_rapids"]
    elif label.startswith("EllensburgFm."):
        rank, ref = "named_interbed_formal_rank_pending", REFERENCES["regional_order"]
    elif label == "Crbg.Undifferentiated":
        rank = "unresolved_group_level_basalt"
    elif label == "Crbg.Undifferentiated.WeatheredFlowTop":
        rank = "weathering_or_flow_top_description"
    elif label.startswith("Sediment.Interbed"):
        rank = "unresolved_interbed"
    elif label.startswith("Sediment.MissoulaFlood.") or label.startswith("Sediment.Quaternary.Alluvium."):
        rank = "sedimentary_facies"
    elif label.startswith("Sediment"):
        rank = "sedimentary_material_age_or_depositional_label"
    children = sorted(u for u in labels if u.startswith(label + "."))
    general = label + ".general" if label in labels and children and "Undifferentiated" not in label else ""
    return {"label_path": label, "parent_path": label.rsplit(".", 1)[0] if "." in label else "",
        "token_depth": len(label.split(".")), "recorded_label": label in labels,
        "rank_draft": rank, "display_name_draft": display, "reference": ref,
        "descendant_labels_json": packed(children), "general_candidate": general,
        "mapping_status": "draft_not_applied"}


def order_violations(a, b):
    """Partial regional order only; do not impose an order on sediment facies.

    Called only for distinct, positive, nonoverlapping intervals with a above b.
    Return review flags, not evidence that a named pick must be wrong.
    """
    x, y = a["strat_unit"], b["strat_unit"]
    rules = []
    family = lambda u: next((i for i, p in enumerate(("Crbg.Smb", "Crbg.Wb", "Crbg.Grb"))
                             if u == p or u.startswith(p + ".")), None)
    fx, fy = family(x), family(y)
    if fx is not None and fy is not None and fx > fy:
        rules.append("regional_basalt_formation_order")
    smb = {"Crbg.Smb.ElephantMtn": 0, "EllensburgFm.RattlesnakeRidge": 1,
           "Crbg.Smb.Pomona": 2, "EllensburgFm.Selah": 3,
           "Crbg.Smb.Umatilla": 4, "EllensburgFm.Mabton": 5}
    rx = smb.get(x, 6 if fx == 1 else 8 if x == "EllensburgFm.Vantage" else 9 if fx == 2 else None)
    ry = smb.get(y, 6 if fy == 1 else 8 if y == "EllensburgFm.Vantage" else 9 if fy == 2 else None)
    if rx is not None and ry is not None and rx > ry:
        rules.append("regional_members_and_major_interbeds")
    fs = {"Crbg.Wb.FrenchmanSprings.SentinelGap": 0,
          "Crbg.Wb.FrenchmanSprings.SandHollow": 1, "Crbg.Wb.FrenchmanSprings.Ginkgo": 2}
    if x in fs and y in fs and fs[x] > fs[y]:
        rules.append("partial_frenchman_flow_order")
    if x == "Crbg.Wb.PriestRapids.Rosalia" and y == "Crbg.Wb.PriestRapids.Lolo":
        rules.append("lolo_above_rosalia")
    if x.startswith("Crbg.") and y == "Sediment.PostCrb":
        rules.append("post_crbg_sediment_below_basalt")
    if x == "Sediment.PreCrb" and y.startswith("Crbg."):
        rules.append("pre_crbg_sediment_above_basalt")
    return rules


def literal_mentions(material):
    mentions = [u for u, pattern in NAME_PATTERNS.items() if re.search(pattern, material, re.IGNORECASE)]
    if "EllensburgFm.Quincy-SquawCreek" in mentions and "EllensburgFm.SquawCreek" in mentions:
        mentions.remove("EllensburgFm.SquawCreek")
    return mentions


def audit_sequence(rows):
    findings = []

    def flag(code, related, detail):
        findings.append({"issue_code": code, "classification": ISSUE_CLASS[code],
            "source_rows": [r["source_row"] for r in related], "detail": detail})

    valid = []
    surfaces = set()
    for r in rows:
        t, b = number(r["start_depth"]), number(r["end_depth"])
        if t is None or b is None:
            if any(not r[k].strip() for k in ("start_depth", "end_depth")):
                flag("missing_depth", [r], "Top or bottom depth is blank.")
            if any(r[k].strip() and number(r[k]) is None for k in ("start_depth", "end_depth")):
                flag("invalid_depth", [r], "Top or bottom depth is nonnumeric or nonfinite.")
        else:
            if min(t, b) < 0:
                flag("negative_depth", [r], "Depth is negative under the repository positive-down convention.")
            if b < t:
                flag("reversed_depth", [r], "Bottom depth is shallower than top depth.")
            if b == t:
                flag("zero_thickness", [r], "Top and bottom depths are equal.")
            if b > t:
                valid.append(r)
            thickness = number(r["depth_thickness"])
            if thickness is None:
                flag("missing_thickness" if not r["depth_thickness"].strip() else "invalid_thickness", [r], "Recorded thickness cannot be evaluated.")
            elif thickness != b - t:
                flag("thickness_mismatch", [r], "Reported thickness differs from bottom minus top.")
        zt, zb = number(r["start_depth_elev"]), number(r["end_depth_elev"])
        if zt is None or zb is None:
            if any(not r[k].strip() for k in ("start_depth_elev", "end_depth_elev")):
                flag("missing_elevation", [r], "One or both endpoint elevations are blank; no replacement inferred.")
            if any(r[k].strip() and number(r[k]) is None for k in ("start_depth_elev", "end_depth_elev")):
                flag("invalid_elevation", [r], "One or both endpoint elevations are nonnumeric or nonfinite.")
        if None not in (t, b, zt, zb):
            if zt - zb != b - t:
                flag("elevation_thickness_mismatch", [r], "Elevation drop differs from interval depth thickness.")
        if t is not None and zt is not None:
            surfaces.add(t + zt)
        if b is not None and zb is not None:
            surfaces.add(b + zb)
    if len(surfaces) > 1:
        flag("implied_surface_inconsistent", rows, "Depth plus elevation gives multiple offsets: " + packed(sorted(map(str, surfaces))))
    ordered_valid = ordered(valid)
    if ordered_valid and number(ordered_valid[0]["start_depth"]) > 0:
        flag("first_pick_below_zero", [ordered_valid[0]], "First recorded top is below zero; overlying sequence is unrecorded, not inferred absent.")
    # Coverage gaps use a running deepest bottom, so nesting creates no false gap.
    if ordered_valid:
        deepest = ordered_valid[0]
        for current in ordered_valid[1:]:
            gap = number(current["start_depth"]) - number(deepest["end_depth"])
            if gap > 0:
                flag("gap", [deepest, current], f"Uncovered depth range {deepest['end_depth']} to {current['start_depth']}; width {gap} ft.")
            if number(current["end_depth"]) > number(deepest["end_depth"]):
                deepest = current
    for a, b in combinations(ordered_valid, 2):
        overlap = min(number(a["end_depth"]), number(b["end_depth"])) - max(number(a["start_depth"]), number(b["start_depth"]))
        if overlap > 0:
            flag("overlap", [a, b], f"Intervals share {overlap} ft; no split applied.")
        if number(a["end_depth"]) <= number(b["start_depth"]):
            for rule in order_violations(a, b):
                flag("unexpected_order", [a, b], rule + "; regional expectation is a review hypothesis, not a correction.")
    bygeometry, byunit = defaultdict(list), defaultdict(list)
    for r in rows:
        bygeometry[cell_signature(r, GEOMETRY, True)].append(r)
        byunit[r["strat_unit"]].append(r)
    for rs in bygeometry.values():
        if len(rs) > 1:
            flag("duplicate_interval", rs, "Same label and numeric top/bottom within one report sequence; all occurrences retained.")
    for rs in byunit.values():
        if len(rs) > 1:
            flag("repeated_unit", rs, "Label occurs more than once; distinct flows, facies, or interpretations may explain the repetition.")
    for parent, child in combinations(sorted(byunit), 2):
        if child.startswith(parent + "."):
            flag("parent_child_mixed", byunit[parent] + byunit[child], "Recorded ancestor " + parent + " co-occurs with descendant " + child + "; this may be valid mixed resolution.")
    broad = [r for r in rows if r["strat_unit"].startswith("Crbg.Undifferentiated")]
    named = [r for r in rows if r["strat_unit"].startswith(("Crbg.Smb", "Crbg.Wb", "Crbg.Grb"))]
    if broad and named:
        flag("broad_named_basalt_mixed", broad + named, "Group-level undifferentiated basalt co-occurs with identified basalt subdivisions; these are siblings in the recorded code tree but differ in geological resolution.")
    return findings


def lithology_contact(depth, rows):
    valid = [r for r in rows if number(r["from_ft"]) is not None and
             number(r["to_ft"]) is not None and number(r["to_ft"]) > number(r["from_ft"])]
    if depth is None or not valid:
        return {"status": "unassessable", "nearest_distance_ft": "", "nearest_boundaries_json": "[]",
                "containing_rows_json": "[]", "adjacent_rows_json": "[]"}
    bounds = [(number(r[k]), r["source_row"], k) for r in valid for k in ("from_ft", "to_ft")]
    distance = min(abs(d - depth) for d, _, _ in bounds)
    containing = [r["source_row"] for r in valid if number(r["from_ft"]) < depth < number(r["to_ft"])]
    adjacent = [r["source_row"] for r in valid if depth in (number(r["from_ft"]), number(r["to_ft"]))]
    status = "exact_lithology_boundary" if distance == 0 else "inside_lithology_interval" if containing else "outside_lithology_extent" if depth < min(d for d, _, _ in bounds) or depth > max(d for d, _, _ in bounds) else "in_lithology_gap"
    return {"status": status, "nearest_distance_ft": decimal_text(distance),
        "nearest_boundaries_json": packed([{"depth_ft": decimal_text(d), "source_row": n, "endpoint": k} for d, n, k in bounds if abs(d - depth) == distance]),
        "containing_rows_json": packed(containing), "adjacent_rows_json": packed(adjacent)}


def run(input_dir=INPUT, output_dir=OUTPUT):
    input_dir, output_dir = Path(input_dir).resolve(), Path(output_dir).resolve()
    if output_dir == input_dir or input_dir in output_dir.parents:
        raise ValueError("Audit output must be outside the authoritative input directory.")
    names = ["boardman_wells_summary.csv", "boardman_wells_stratigraphy.csv", "boardman_wells_lithology.csv"]
    hashes = {name: digest(input_dir / name) for name in names + ["README.md"]}
    (summary, summary_fields), (strat, strat_fields), (lith, lith_fields) = [read(input_dir / name) for name in names]
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata = {r["well_id"]: r for r in summary}
    if len(metadata) != len(summary) or len({r["wl_id"] for r in summary}) != len(summary):
        raise ValueError("Summary report identifiers are not one-to-one.")
    for rows in (strat, lith):
        for r in rows:
            if r["well_id"] not in metadata or metadata[r["well_id"]]["wl_id"] != r["wl_id"]:
                raise ValueError(f"Unmatched report identifier at source row {r['source_row']}")
    bysite, bylith = defaultdict(lambda: defaultdict(list)), defaultdict(list)
    for r in strat:
        if not r["gw_site_id"] or metadata[r["well_id"]]["gw_site_id"] != r["gw_site_id"]:
            raise ValueError(f"Missing or mismatched site identifier at row {r['source_row']}")
        bysite[r["gw_site_id"]][r["well_id"]].append(r)
    for r in lith:
        bylith[r["well_id"]].append(r)
    scount, lcount = Counter(r["well_id"] for r in strat), Counter(r["well_id"] for r in lith)
    for r in summary:
        if int(r["strat_count"]) != scount[r["well_id"]] or int(r["lithology_count"]) != lcount[r["well_id"]]:
            raise ValueError(f"Interval counts disagree for {r['well_id']}")
        if (r["has_stratigraphy"] == "TRUE") != bool(scount[r["well_id"]]) or (r["has_lithology"] == "TRUE") != bool(lcount[r["well_id"]]):
            raise ValueError(f"Coverage flags disagree for {r['well_id']}")

    findings, site_rows, interval_rows, links, transitions = [], [], [], [], []
    row_flags, row_interval, interval_sources = defaultdict(set), {}, {}

    def finding(site, variant, issue, mapping):
        refs = sorted({n for representative in issue["source_rows"] for n in mapping.get(representative, [representative])})
        fid = f"F{len(findings) + 1:05d}"
        linked = [r for r in strat if r["source_row"] in refs]
        findings.append({"finding_id": fid, "gw_site_id": site, "sequence_variant_id": variant,
            "issue_code": issue["issue_code"], "classification": issue["classification"],
            "source_rows_json": packed(refs), "well_ids_json": packed(sorted({r['well_id'] for r in linked})),
            "wl_ids_json": packed(sorted({r['wl_id'] for r in linked})), "detail": issue["detail"],
            "correction_applied": False, "correction_source": "", "review_status": "unreviewed"})
        for n in refs:
            row_flags[n].add(issue["issue_code"])

    for site, reports in sorted(bysite.items(), key=lambda x: int(x[0])):
        vs = variants(reports)
        start = len(findings)
        if len(vs) > 1:
            finding(site, "", {"issue_code": "linked_report_conflict", "classification": ISSUE_CLASS["linked_report_conflict"],
                "source_rows": [r["source_row"] for rs in reports.values() for r in rs],
                "detail": "Scientific row multisets differ; separate variants retained without choosing a winner."}, {})
        for vnum, wells in enumerate(vs, 1):
            vid = f"{site}:v{vnum}"
            representative = wells[0]
            rs = ordered(reports[representative])
            mapping = {}
            occurrences = {}
            for well in wells:
                pool = defaultdict(list)
                for r in ordered(reports[well]):
                    pool[cell_signature(r, SCIENTIFIC)].append(r)
                occurrences[well] = pool
            occurrence_counts = Counter()
            for ordinal, r in enumerate(rs, 1):
                key = cell_signature(r, SCIENTIFIC)
                k = occurrence_counts[key]
                occurrence_counts[key] += 1
                matched = [occurrences[well][key][k] for well in wells]
                iid = f"{vid}:i{ordinal:03d}"
                refs = sorted(row["source_row"] for row in matched)
                mapping[r["source_row"]] = refs
                interval_sources[iid] = refs
                for n in refs:
                    row_interval[n] = iid
                interval_rows.append({**r, "sequence_variant_id": vid, "site_interval_id": iid,
                    "sequence_order": ordinal, "source_rows_json": packed(refs),
                    "linked_well_ids_json": packed(wells), "linked_wl_ids_json": packed([metadata[w]["wl_id"] for w in wells]),
                    "top_ft_parsed": decimal_text(number(r["start_depth"])), "bottom_ft_parsed": decimal_text(number(r["end_depth"])),
                    "unit_standardized": "", "top_ft_corrected": "", "bottom_ft_corrected": "",
                    "review_status": "candidate_unmodified"})
            for issue in audit_sequence(rs):
                finding(site, vid, issue, mapping)
            for a, b in zip(rs, rs[1:]):
                ta, ba, tb, bb = [number(v) for v in (a["start_depth"], a["end_depth"], b["start_depth"], b["end_depth"])]
                delta = tb - ba if None not in (ba, tb) else None
                transitions.append({"gw_site_id": site, "sequence_variant_id": vid,
                    "shallower_label": a["strat_unit"], "deeper_label": b["strat_unit"],
                    "shallower_interval_id": row_interval[a["source_row"]], "deeper_interval_id": row_interval[b["source_row"]],
                    "signed_separation_ft": decimal_text(delta),
                    "relation": "unassessable" if delta is None else "gap" if delta > 0 else "overlap" if delta < 0 else "touching",
                    "linked_report_count": len(wells)})
            for well in wells:
                m = metadata[well]
                links.append({**m, "sequence_variant_id": vid, "representative_report": well == representative,
                    "scientific_sequence_sha256": hashlib.sha256(packed(sequence_signature(reports[well])).encode()).hexdigest(),
                    "stratigraphy_source_rows_json": packed([r["source_row"] for r in reports[well]])})
        for well, rs in sorted(reports.items()):
            completed = number(metadata[well]["completed_depth_ft"])
            if completed is not None and completed <= 0:
                finding(site, row_interval[rs[0]["source_row"]].split(":i")[0],
                    {"issue_code": "nonpositive_report_depth", "classification": ISSUE_CLASS["nonpositive_report_depth"],
                     "source_rows": [r["source_row"] for r in rs], "detail": f"Report {well} completed_depth_ft={completed}; no missing-value convention inferred."}, {})
            for r in rs:
                if completed is not None and number(r["end_depth"]) is not None and number(r["end_depth"]) > completed:
                    finding(site, row_interval[r["source_row"]].split(":i")[0],
                        {"issue_code": "beyond_report_depth", "classification": ISSUE_CLASS["beyond_report_depth"],
                         "source_rows": [r["source_row"]], "detail": f"Site interval bottom {r['end_depth']} ft exceeds linked report {well} depth {completed} ft; site and report may cover different drilling histories."}, {})
        attributes = {k: sorted({metadata[w][k] for w in reports}) for k in ("completed_depth_ft", "complete_date", "latitude", "longitude", "location_class")}
        different = [k for k, values in attributes.items() if len(values) > 1]
        if len(reports) > 1 and different:
            finding(site, "", {"issue_code": "linked_report_metadata_difference", "classification": ISSUE_CLASS["linked_report_metadata_difference"],
                "source_rows": [r["source_row"] for rs in reports.values() for r in rs],
                "detail": "Report metadata differ: " + ", ".join(different) + "; preserve all links; no representative coordinate chosen."}, {})
        codes = Counter(f["issue_code"] for f in findings[start:])
        site_rows.append({"gw_site_id": site, "report_count": len(reports), "sequence_variant_count": len(vs),
            "numeric_scientific_variant_count": len({sequence_signature(rs, numeric=True) for rs in reports.values()}),
            "geometry_variant_count": len({sequence_signature(rs, GEOMETRY, True) for rs in reports.values()}),
            "report_order_variant_count": len({tuple(cell_signature(r, SCIENTIFIC) for r in rs) for rs in reports.values()}),
            "original_interval_rows": sum(map(len, reports.values())),
            "candidate_interval_count": sum(len(reports[ws[0]]) for ws in vs),
            "linked_well_ids_json": packed(sorted(reports)), "linked_wl_ids_json": packed([metadata[w]["wl_id"] for w in sorted(reports)]),
            "report_metadata_json": packed(attributes), "issue_counts_json": packed(codes),
            "issue_codes_json": packed(sorted(codes))})

    labels = sorted({r["strat_unit"] for r in strat})
    hierarchy = [hierarchy_info(u, labels) for u in sorted({".".join(u.split(".")[:i]) for u in labels for i in range(1, len(u.split(".")) + 1)})]
    frequencies, interpreters = [], []
    for label in labels:
        rs = [r for r in strat if r["strat_unit"] == label]
        people = sorted({r["picked_by"] for r in rs if r["picked_by"]})
        frequencies.append({"strat_unit": label, "interval_rows": len(rs), "well_reports": len({r["well_id"] for r in rs}),
            "gwis_sites": len({r["gw_site_id"] for r in rs}),
            "site_interval_occurrences": sum(r["strat_unit"] == label for r in interval_rows),
            "distinct_interpreter_labels": len(people), "missing_interpreter_rows": sum(not r["picked_by"] for r in rs),
            "interpreter_labels_json": packed(people), **{k: v for k, v in hierarchy_info(label, labels).items() if k in ("rank_draft", "general_candidate")}})
        for person in sorted({r["picked_by"] for r in rs}):
            selected = [r for r in rs if r["picked_by"] == person]
            interpreters.append({"strat_unit": label, "picked_by": person, "interval_rows": len(selected),
                "well_reports": len({r["well_id"] for r in selected}), "gwis_sites": len({r["gw_site_id"] for r in selected}),
                "casefold_candidate": person.strip().casefold(), "identity_merge_applied": False})
    audit = [{**r, "source_file": names[1], "source_sha256": hashes[names[1]],
        "site_interval_id": row_interval[r["source_row"]], "issue_codes_json": packed(sorted(row_flags[r["source_row"]])),
        "top_ft_parsed": decimal_text(number(r["start_depth"])), "bottom_ft_parsed": decimal_text(number(r["end_depth"])),
        "unit_standardized": "", "top_ft_corrected": "", "bottom_ft_corrected": "", "correction_source": "",
        "correction_reason": "", "decision_ids_json": "[]", "review_status": "unreviewed"} for r in strat]

    contacts, overlaps, lith_audit, named_checks = [], [], [], []
    paired = {r["well_id"] for r in strat} & set(bylith)
    for well in sorted(paired):
        for r in bylith[well]:
            t, b = number(r["from_ft"]), number(r["to_ft"])
            codes = []
            residual = None
            if t is None or b is None:
                codes.append("unassessable_depth")
            else:
                if min(t, b) < 0:
                    codes.append("negative_depth")
                if b < t:
                    codes.append("reversed_depth")
                if b == t:
                    codes.append("zero_thickness")
                thick = number(r["thickness_ft"])
                residual = thick - (b - t) if thick is not None else None
                if thick is None or thick != b - t:
                    codes.append("thickness_unassessable_or_mismatch")
            lith_audit.append({**r, "gw_site_id": metadata[well]["gw_site_id"], "issue_codes_json": packed(codes),
                "thickness_residual_ft": decimal_text(residual), "source_sha256": hashes[names[2]]})
    for r in strat:
        if r["well_id"] not in paired:
            continue
        rs = bylith[r["well_id"]]
        for endpoint, field in (("top", "start_depth"), ("bottom", "end_depth")):
            contacts.append({"well_id": r["well_id"], "wl_id": r["wl_id"], "gw_site_id": r["gw_site_id"],
                "site_interval_id": row_interval[r["source_row"]], "stratigraphy_source_row": r["source_row"],
                "strat_unit": r["strat_unit"], "endpoint": endpoint, "candidate_depth_ft_raw": r[field],
                **lithology_contact(number(r[field]), rs), "contact_status": "candidate_not_validated"})
        for l in rs:
            t, b, lt, lb = map(number, (r["start_depth"], r["end_depth"], l["from_ft"], l["to_ft"]))
            if None in (t, b, lt, lb) or b <= t or lb <= lt:
                continue
            width = min(b, lb) - max(t, lt)
            if width > 0:
                overlaps.append({"well_id": r["well_id"], "wl_id": r["wl_id"], "gw_site_id": r["gw_site_id"],
                    "site_interval_id": row_interval[r["source_row"]], "stratigraphy_source_row": r["source_row"],
                    "strat_unit": r["strat_unit"], "lithology_source_row": l["source_row"],
                    "lithology_interval_no": l["interval_no"], "material_raw": l["material_raw"],
                    "overlap_top_ft": decimal_text(max(t, lt)), "overlap_bottom_ft": decimal_text(min(b, lb)),
                    "overlap_thickness_ft": decimal_text(width)})
                mentions = literal_mentions(l["material_raw"])
                for mentioned in mentions:
                    agrees = r["strat_unit"] == mentioned
                    named_checks.append({"well_id": r["well_id"], "wl_id": r["wl_id"], "gw_site_id": r["gw_site_id"],
                        "stratigraphy_source_row": r["source_row"], "lithology_source_row": l["source_row"],
                        "strat_unit": r["strat_unit"], "literal_unit_mention_candidate": mentioned,
                        "material_raw": l["material_raw"], "overlap_top_ft": decimal_text(max(t, lt)),
                        "overlap_bottom_ft": decimal_text(min(b, lb)), "same_recorded_unit": agrees,
                        "review_status": "literal_name_screen_not_formation_validation"})
                    if not agrees:
                        finding(r["gw_site_id"], row_interval[r["source_row"]].split(":i")[0],
                            {"issue_code": "lithology_named_unit_disagreement", "classification": "review_required",
                             "source_rows": [r["source_row"]], "detail": f"Lithology CSV record {l['source_row']} contains a literal name suggesting {mentioned}, overlapping recorded stratigraphy {r['strat_unit']}; no interpretation replaced."}, {})

    # Lithology findings are report-specific and arrive after the site pass.
    for r in audit:
        r["issue_codes_json"] = packed(sorted(row_flags[r["source_row"]]))
    for s in site_rows:
        codes = Counter(f["issue_code"] for f in findings if f["gw_site_id"] == s["gw_site_id"])
        s["issue_counts_json"], s["issue_codes_json"] = packed(codes), packed(sorted(codes))

    issue_stats = {}
    for code in ISSUE_CLASS:
        fs = [f for f in findings if f["issue_code"] == code]
        refs = {n for f in fs for n in json.loads(f["source_rows_json"])}
        issue_stats[code] = {"findings": len(fs), "gwis_sites": len({f["gw_site_id"] for f in fs}),
            "well_reports": len({r["well_id"] for r in strat if r["source_row"] in refs}),
            "source_interval_rows": len(refs), "classification": ISSUE_CLASS[code]}
    inventory = {"well_reports": len(summary), "township_keys": len({r["tr_key"] for r in summary}),
        "county_reports": dict(sorted(Counter(r["county"] for r in summary).items())),
        "stratigraphy_rows": len(strat), "stratigraphy_reports": len(scount), "stratigraphy_gwis_sites": len(bysite),
        "shared_site_reports": sum(len(rs) for rs in bysite.values() if len(rs) > 1),
        "shared_gwis_sites": sum(len(rs) > 1 for rs in bysite.values()),
        "single_site_reports": sum(len(rs) == 1 for rs in bysite.values()),
        "paired_reports": len(paired), "paired_gwis_sites": len({metadata[w]["gw_site_id"] for w in paired}),
        "stratigraphy_without_lithology_reports": len(set(scount) - paired),
        "lithology_rows": len(lith), "lithology_reports": len(lcount), "stratigraphic_labels": len(labels),
        "candidate_site_intervals": len(interval_rows), "repeated_linked_interval_copies": len(strat) - len(interval_rows)}
    expected = {"well_reports": 7402, "township_keys": 19, "county_reports": {"GILL": 1, "MORR": 2553, "UMAT": 4848},
        "stratigraphy_rows": 1854, "stratigraphy_reports": 423, "stratigraphy_gwis_sites": 328,
        "shared_site_reports": 166, "shared_gwis_sites": 71, "single_site_reports": 257,
        "paired_reports": 121, "paired_gwis_sites": 112, "stratigraphy_without_lithology_reports": 302}
    result = {"audit_version": VERSION, "audit_script_sha256": digest(Path(__file__)), "source_directory": str(input_dir), "source_sha256": hashes,
        "inventory": inventory, "requested_count_checks": {k: {"expected": v, "actual": inventory[k], "passed": inventory[k] == v} for k, v in expected.items()},
        "source_schemas": {name: {"fields": fields, "blank_counts": {k: sum(not r[k] for r in rows) for k in fields}} for name, fields, rows in zip(names, (summary_fields, strat_fields, lith_fields), (summary, strat, lith))},
        "township_reports": dict(sorted(Counter(r["tr_key"] for r in summary).items())),
        "issues": issue_stats, "contact_candidate_counts": dict(Counter(r["status"] for r in contacts)),
        "contact_candidate_rows": len(contacts), "paired_lithology_rows": len(lith_audit),
        "paired_lithology_rows_with_flags": sum(json.loads(r["issue_codes_json"]) != [] for r in lith_audit),
        "contact_distinct_report_depths": len({(r['well_id'], number(r['candidate_depth_ft_raw'])) for r in contacts}),
        "contact_exact_distinct_report_depths": len({(r['well_id'], number(r['candidate_depth_ft_raw'])) for r in contacts if r['status'] == 'exact_lithology_boundary'}),
        "strat_lithology_overlap_rows": len(overlaps),
        "literal_lithology_unit_mention_checks": len(named_checks),
        "contact_distinct_depth_counts_by_status": dict(Counter(status for _, _, status in {
            (r["well_id"], number(r["candidate_depth_ft_raw"]), r["status"]) for r in contacts})),
        "report_metadata_difference_site_counts": {k: sum(len(json.loads(r["report_metadata_json"])[k]) > 1 for r in site_rows)
            for k in ("completed_depth_ft", "complete_date", "latitude", "longitude", "location_class")},
        "naive_representative_report_collapse": {
            "rule": "Lexicographically first well_id per identical site sequence, used only as a reproducible loss example.",
            "paired_reports_retained": sum(r["representative_report"] and r["well_id"] in paired for r in links),
            "paired_reports_lost": len(paired) - sum(r["representative_report"] and r["well_id"] in paired for r in links),
            "paired_sites_lost": len({metadata[w]["gw_site_id"] for w in paired}) - len({r["gw_site_id"] for r in links if r["representative_report"] and r["well_id"] in paired})},
        "missing_elevation_site_intervals": sum(not r["start_depth_elev"] or not r["end_depth_elev"] for r in interval_rows),
        "interpreter_labels": dict(sorted(Counter(r["picked_by"] for r in strat).items())),
        "interpreter_casefold_groups": {k: sorted(v) for k, v in _casefold_groups(strat).items() if len(v) > 1},
        "methods": {"source_row": "CSV record ordinal including header; first data record is 2. Not physical line number.",
            "depth_arithmetic": "Decimal, exact comparison, positive down; feet follows repository convention; elevation datum unverified.",
            "site_variants": "Scientific row multisets compared with original strings. Numeric-equivalent and geometry comparisons reported separately. Report fields and acquisition metadata excluded from scientific signature but preserved in source audit and report links.",
            "interval_matching": "Identical scientific interval signatures paired by occurrence number within each linked report; within-report duplicates never discarded.",
            "order_screen": "All nonoverlapping ordered interval pairs, partial published order only; unresolved labels and unverified within-facies orders untested; no forced rank for broad Ellensburg or undifferentiated CRBG.",
            "lithology": "All tops and bottoms retained as candidates. Exact endpoint match or interval containment is geometric evidence, not formation identification. Zero/reversed/missing lithology excluded only from geometric comparison and retained in lithology audit.",
            "coverage_gaps": "Running maximum bottom; no unit inserted. First pick below zero is a coverage note.",
            "geological_corrections": "None. Standardized names, corrected tops and bottoms, and reasons are blank."},
        "references": REFERENCES}
    schemas = {
        "row_audit": {"grain": "one authoritative stratigraphy source row", "fields": [*strat_fields, "source_row", "source_file", "source_sha256", "site_interval_id", "issue_codes_json", "top_ft_parsed", "bottom_ft_parsed", "unit_standardized", "top_ft_corrected", "bottom_ft_corrected", "correction_source", "correction_reason", "decision_ids_json", "review_status"]},
        "findings": {"grain": "one check result affecting one or more original rows", "fields": ["finding_id", "gw_site_id", "sequence_variant_id", "issue_code", "classification", "source_rows_json", "well_ids_json", "wl_ids_json", "detail", "correction_applied", "correction_source", "review_status"]},
        "proposed_cleaned_sequence": {"grain": "one interval occurrence per GWIS site and accepted interpretation variant; never merge repeated occurrences", "fields": {
            "sequence_id": "versioned site/interpretation key", "site_interval_id": "stable occurrence key plus sequence version", "sequence_order": "ordered position, original order retained in row links", "gw_site_id": "site interpretation identifier, not physical borehole", "well_ids_json": "all linked repository report IDs", "wl_ids_json": "all linked OWRD numeric IDs", "source_rows_json": "all CSV record references", "source_sha256": "source snapshot hash", "source_unit": "original label; in row links if variants differ", "unit_standardized": "reviewed controlled label, separate from source", "unit_rank": "formal/informal rank with evidence", "parent_unit_id": "approved containment; separate from polarity and age attributes", "resolution": "group/formation/member/flow/facies/unresolved", "top_ft_original": "original depth", "bottom_ft_original": "original depth", "top_ft_corrected": "nullable reviewed derived value", "bottom_ft_corrected": "nullable reviewed derived value", "top_elev_original": "original source elevation", "bottom_elev_original": "original source elevation", "top_elev_derived": "nullable, with explicit computation and datum", "bottom_elev_derived": "nullable, with explicit computation and datum", "depth_unit": "feet convention / verified unit status", "vertical_datum": "unknown until source verified", "top_contact_status": "candidate/reviewed/truncated/unresolved", "bottom_contact_status": "candidate/reviewed/truncated/unresolved", "issue_codes_json": "all applicable audit flags", "review_status": "unreviewed/accepted/rejected/deferred", "decision_ids_json": "links to correction register", "coordinate_source_links_json": "all report positions and quality, no automatic site centroid"}},
        "correction_register": {"grain": "one versioned decision for an interval endpoint or name", "fields": ["decision_id", "sequence_version", "site_interval_id", "field", "old_value", "derived_value", "method", "reason", "evidence_links_json", "reviewer", "reviewed_at", "approval_status", "algorithm_version"]},
    }
    tables = {
        "row_audit.csv": (audit, schemas["row_audit"]["fields"]),
        "findings.csv": (findings, schemas["findings"]["fields"]),
        "site_audit.csv": (site_rows, list(site_rows[0]) if site_rows else ["gw_site_id"]),
        "sequence_intervals.csv": (interval_rows, [*strat_fields, "source_row", "sequence_variant_id", "site_interval_id", "sequence_order", "source_rows_json", "linked_well_ids_json", "linked_wl_ids_json", "top_ft_parsed", "bottom_ft_parsed", "unit_standardized", "top_ft_corrected", "bottom_ft_corrected", "review_status"]),
        "site_report_links.csv": (links, [*summary_fields, "source_row", "sequence_variant_id", "representative_report", "scientific_sequence_sha256", "stratigraphy_source_rows_json"]),
        "unit_frequency.csv": (frequencies, list(frequencies[0]) if frequencies else ["strat_unit"]),
        "unit_interpreter_frequency.csv": (interpreters, ["strat_unit", "picked_by", "interval_rows", "well_reports", "gwis_sites", "casefold_candidate", "identity_merge_applied"]),
        "hierarchy_draft.csv": (hierarchy, list(hierarchy[0]) if hierarchy else ["label_path"]),
        "observed_transitions.csv": (transitions, ["gw_site_id", "sequence_variant_id", "shallower_label", "deeper_label", "shallower_interval_id", "deeper_interval_id", "signed_separation_ft", "relation", "linked_report_count"]),
        "contact_lithology_candidates.csv": (contacts, ["well_id", "wl_id", "gw_site_id", "site_interval_id", "stratigraphy_source_row", "strat_unit", "endpoint", "candidate_depth_ft_raw", "status", "nearest_distance_ft", "nearest_boundaries_json", "containing_rows_json", "adjacent_rows_json", "contact_status"]),
        "strat_lithology_overlaps.csv": (overlaps, ["well_id", "wl_id", "gw_site_id", "site_interval_id", "stratigraphy_source_row", "strat_unit", "lithology_source_row", "lithology_interval_no", "material_raw", "overlap_top_ft", "overlap_bottom_ft", "overlap_thickness_ft"]),
        "paired_lithology_audit.csv": (lith_audit, [*lith_fields, "source_row", "gw_site_id", "issue_codes_json", "thickness_residual_ft", "source_sha256"]),
        "lithology_named_unit_checks.csv": (named_checks, ["well_id", "wl_id", "gw_site_id", "stratigraphy_source_row", "lithology_source_row", "strat_unit", "literal_unit_mention_candidate", "material_raw", "overlap_top_ft", "overlap_bottom_ft", "same_recorded_unit", "review_status"]),
    }
    for name, (rows, fields) in tables.items():
        write(output_dir / name, rows, fields)
    result["output_tables"] = {name: {"rows": len(rows), "sha256": digest(output_dir / name)} for name, (rows, _) in tables.items()}
    result["literal_lithology_name_patterns"] = NAME_PATTERNS
    result["source_hashes_unchanged"] = all(digest(input_dir / name) == value for name, value in hashes.items())
    if not result["source_hashes_unchanged"]:
        raise RuntimeError("Source data changed during the audit.")
    (output_dir / "summary.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    (output_dir / "proposed_schemas.json").write_text(json.dumps(schemas, indent=2) + "\n")
    examples = {}
    lookup = {r["source_row"]: r for r in strat}
    for code in ISSUE_CLASS:
        examples[code] = [{**f, "original_rows": [lookup[n] for n in json.loads(f["source_rows_json"])]}
            for f in [f for f in findings if f["issue_code"] == code][:5]]
    (output_dir / "examples.json").write_text(json.dumps(examples, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"inventory": inventory, "issues": issue_stats, "contacts": result["contact_candidate_counts"],
        "count_checks_passed": all(v["passed"] for v in result["requested_count_checks"].values()),
        "source_hashes_unchanged": result["source_hashes_unchanged"]}, indent=2))
    return result


def _casefold_groups(rows):
    groups = defaultdict(set)
    for r in rows:
        if r["picked_by"]:
            groups[r["picked_by"].strip().casefold()].add(r["picked_by"])
    return groups


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=INPUT)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    run(args.input_dir, args.output_dir)
