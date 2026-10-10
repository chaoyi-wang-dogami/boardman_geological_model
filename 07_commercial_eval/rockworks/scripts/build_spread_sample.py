"""Build a genuine BIFF8 .xls from paired reports, without altering sources.

Run with the repository .venv/bin/python. Install xlwt==1.3.0 and
xlrd==2.0.2 into scripts/.deps (see the input import instructions).
Network access is needed for uncached GWIS and NOAA metadata only.
"""
import csv
import gzip
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

EVAL = Path(__file__).resolve().parents[1]
REPO = EVAL.parents[1]
SOURCE = REPO / "03_processed/boardman_19_townships"
OUT = EVAL / "input/35_paired_spread"
sys.path.insert(0, str(EVAL / "scripts/.deps"))
import requests
import xlrd
import xlwt
from lxml import html
from pyproj import Transformer

FT_TO_M = 0.3048
URL = "https://apps.wrd.state.or.us/apps/gw/gw_info/gw_info_report/gw_details.aspx?gw_site_id={}"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name):
    with (SOURCE / f"boardman_wells_{name}.csv").open(newline="") as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames, list(reader)


def write_csv(path, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def flags(summary, lith, strat):
    result = []
    for name, rows, a, b in (("lithology", lith, "from_ft", "to_ft"),
                             ("stratigraphy", strat, "start_depth", "end_depth")):
        end = -math.inf
        for row in sorted(rows, key=lambda r: (float(r[a]), float(r[b]))):
            top, base = float(row[a]), float(row[b])
            if top < 0 or base <= top:
                result.append(name + "_nonpositive_or_negative_interval")
            if top < end:
                result.append(name + "_overlap")
            if end != -math.inf and top > end:
                result.append(name + "_gap")
            end = max(end, base)
    labels = [r["strat_unit"] for r in strat]
    if len(labels) != len(set(labels)):
        result.append("repeated_stratigraphic_label")
    max_depth = max([float(r["to_ft"]) for r in lith] + [float(r["end_depth"]) for r in strat])
    td = summary["completed_depth_ft"]
    if not td or float(td) <= 0:
        result.append("missing_or_nonpositive_reported_total_depth")
    elif max_depth > float(td):
        result.append("interval_beyond_reported_total_depth")
    if summary["location_class"] in ("C", "D"):
        result.append("lower_coordinate_confidence_" + summary["location_class"])
    return sorted(set(result))


def select(summary, lith, strat):
    project = Transformer.from_crs(4326, 26911, always_xy=True)
    pool = []
    for r in summary:
        well = r["well_id"]
        if not lith[well] or not strat[well]:
            continue
        q = flags(r, lith[well], strat[well])
        x, y = project.transform(float(r["longitude"]), float(r["latitude"]))
        pool.append({**r, "easting_m": x, "northing_m": y,
                     "qc_flags": ";".join(q), "selected": False,
                     "sampling_eligible": bool(r["completed_depth_ft"] and float(r["completed_depth_ft"]) > 0),
                     "selection_reason": "", "selection_step": "", "nearest_selected_at_selection_m": ""})
    assert len(pool) == 121 and len({r["gw_site_id"] for r in pool}) == 112
    chosen = []
    sites = set()
    eligible = [r for r in pool if r["sampling_eligible"]]
    for r in pool:
        if not r["sampling_eligible"]:
            r["selection_reason"] = "not_sampled_missing_native_import_total_depth_retained_in_pool_audit"

    def quality(r):
        # Quality only breaks spatial ties; no geological rows are discarded.
        return (r["location_class"] not in ("A", "B"), len(r["qc_flags"].split(";")) if r["qc_flags"] else 0, r["well_id"])

    def distance(r):
        return min(math.hypot(r["easting_m"] - c["easting_m"], r["northing_m"] - c["northing_m"])
                   for c in chosen) if chosen else 0

    def add(r, reason):
        d = distance(r)
        r.update(selected=True, selection_reason=reason, selection_step=len(chosen) + 1,
                 nearest_selected_at_selection_m=d if chosen else "")
        chosen.append(r)
        sites.add(r["gw_site_id"])

    # Seed at the western edge, then ensure all townships with paired data.
    add(min(eligible, key=lambda r: (r["easting_m"], quality(r))), "western_extent_seed")
    townships = {r["tr_key"] for r in pool}
    while {r["tr_key"] for r in chosen} != townships:
        covered = {r["tr_key"] for r in chosen}
        options = [r for r in eligible if r["tr_key"] not in covered and r["gw_site_id"] not in sites]
        add(min(options, key=lambda r: (-distance(r), quality(r))), "cover_paired_data_township")
    while len(chosen) < 35:
        options = [r for r in eligible if r["gw_site_id"] not in sites]
        add(min(options, key=lambda r: (-distance(r), quality(r))), "maximize_distance_to_selected_sites")
    assert len({r["well_id"] for r in chosen}) == len(sites) == 35
    assert len({r["tr_key"] for r in chosen}) == 13
    return sorted(chosen, key=lambda r: r["well_id"]), pool


def site_metadata(row):
    site = row["gw_site_id"]
    cache = OUT / "evidence" / f"gwis_{site}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    old = EVAL / "input/35_well_preflight/evidence" / f"gwis_{site}.html.gz"
    if old.exists():
        content = gzip.decompress(old.read_bytes())
        retrieved = json.loads(old.with_name(f"gwis_{site}_lithology_visible.json").read_text())["metadata"]["retrieved_at_utc"]
    else:
        response = requests.get(URL.format(site), timeout=60)
        response.raise_for_status()
        content = response.content
        retrieved = datetime.now(timezone.utc).isoformat()
    (OUT / "evidence" / f"gwis_{site}.html.gz").write_bytes(gzip.compress(content, mtime=0))
    root = html.fromstring(content)
    prefix = "ctl00_PageData_uc_gw_site_location_"
    def get(suffix):
        nodes = root.xpath("//*[@id=$ident]", ident=prefix + suffix)
        if not nodes:
            raise ValueError(f"Site {site}: missing {suffix}")
        return nodes[0].text_content().strip()
    identity = set(root.xpath("//input[contains(@id, 'hf_gw_site_id')]/@value")) - {""}
    assert identity == {site}, (site, identity)
    record = {"gw_site_id": site, "source_url": URL.format(site), "retrieved_at_utc": retrieved,
              "page_sha256": hashlib.sha256(content).hexdigest(),
              "source_ground_elevation_ft": get("lb_lsd_elevation"),
              "source_vertical_datum": get("lb_elevation_datum"),
              "source_elevation_method": get("lb_lsd_elevation_source"),
              "source_elevation_accuracy_raw": get("lb_lsd_accuracy"),
              "site_horizontal_datum": get("lb_lat_long_datum")}
    cache.write_text(json.dumps(record, indent=2) + "\n")
    return record


def navd88(row, metadata, strat):
    source_ft = float(metadata["source_ground_elevation_ft"].replace(",", ""))
    implied = [float(r[a]) + float(r[b]) for r in strat
               for a, b in (("start_depth", "start_depth_elev"), ("end_depth", "end_depth_elev")) if r[b]]
    if not implied or any(abs(z - source_ft) > 0.011 for z in implied):
        raise ValueError(f"Source/live elevation mismatch for {row['well_id']}; datum cannot be assigned silently")
    datum = metadata["source_vertical_datum"]
    result = {**metadata, "well_id": row["well_id"], "wl_id": row["wl_id"],
              "source_ground_elevation_m": source_ft * FT_TO_M,
              "target_vertical_datum": "NAVD88", "vertical_shift_m": 0.0,
              "transformation_method": "datum_identity_and_ft_to_m", "transform_sigma_m": ""}
    if datum == "NAVD1988":
        result["ground_navd88_m"] = source_ft * FT_TO_M
    elif datum == "NGVD1929":
        # Grid location transformed using the repository's WGS84 coordinate convention.
        # This is not an assertion of a surveyed NAD83 realization.
        location = Transformer.from_crs(4326, 4269, always_xy=True)
        lon, lat = location.transform(float(row["longitude"]), float(row["latitude"]))
        parameters = {"lat": lat, "lon": lon, "inDatum": "NAD83(1986)",
                      "outDatum": "NAD83(1986)", "inVertDatum": "NGVD29",
                      "outVertDatum": "NAVD88", "orthoHt": source_ft * FT_TO_M}
        cache = OUT / "evidence" / f"ncat_{row['gw_site_id']}.json"
        if cache.exists():
            evidence = json.loads(cache.read_text())
            assert evidence["parameters"] == parameters
        else:
            response = requests.get("https://geodesy.noaa.gov/api/ncat/llh", params=parameters, timeout=60)
            response.raise_for_status()
            evidence = {"request_url": response.url, "parameters": parameters,
                        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(), "response": response.json()}
            cache.write_text(json.dumps(evidence, indent=2) + "\n")
        response = evidence["response"]
        assert response["srcVertDatum"] == "NGVD29" and response["destVertDatum"] == "NAVD88", response
        result["ground_navd88_m"] = float(response["destOrthoht"])
        result["vertical_shift_m"] = result["ground_navd88_m"] - result["source_ground_elevation_m"]
        result["transform_sigma_m"] = response["sigOrthoht"]
        result["transformation_method"] = "NOAA_NCAT_VERTCON_" + response["vertconVersion"]
        result["ncat_request_url"] = evidence["request_url"]
    else:
        raise ValueError(f"Unsupported source datum: {datum}")
    return result


def workbook(selected, pool, lith, strat, raw, datum, hashes):
    wb = xlwt.Workbook(encoding="utf-8")
    header = xlwt.easyxf("font: bold on; pattern: pattern solid, fore_colour gray25;")
    numeric = xlwt.easyxf(num_format_str="0.000000")
    tables = {}
    def sheet(name, headings, rows):
        tables[name] = (headings, rows)
        ws = wb.add_sheet(name)
        ws.set_panes_frozen(True); ws.set_horz_split_pos(1)
        for j, key in enumerate(headings):
            ws.write(0, j, key, header)
            ws.col(j).width = min(55, max(14, len(key) + 2)) * 256
        for i, row in enumerate(rows, 1):
            for j, value in enumerate(row):
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    if not math.isfinite(value):
                        raise ValueError(f"Nonfinite value in {name}")
                    ws.write(i, j, value, numeric)
                else:
                    ws.write(i, j, str(value) if value is not None else "")

    label_parents = {r["strat_unit"] for r in raw["stratigraphy"][1]
                     if any(s["strat_unit"].startswith(r["strat_unit"] + ".") for s in raw["stratigraphy"][1])}
    # Dataset hierarchy convention; leaves and unknown labels are not altered.
    label_map = {label: label + ".general" if label in label_parents else label
                 for label in {r["strat_unit"] for r in raw["stratigraphy"][1]}}
    for r in selected:
        well = r["well_id"]
        d = datum[well]
        td = r["completed_depth_ft"]
        if not td or float(td) <= 0:
            raise ValueError(f"No usable reported Total Depth for {well}; choose or clarify before import")
    locations = []
    provenance = []
    lrows = []
    srows = []
    descriptions = sorted({r["material_raw"] for c in selected for r in lith[c["well_id"]]})
    keywords = {text: f"LITH_{i:04d}" for i, text in enumerate(descriptions, 1)}
    for r in selected:
        well = r["well_id"]
        d = datum[well]
        metadata = {"well_id": well, "wl_id": r["wl_id"], "gw_site_id": r["gw_site_id"],
                    "identity_kind": "report_proxy", "contact_state": "source_interpretation",
                    "location_class": r["location_class"], "qc_flags": r["qc_flags"],
                    "source_vertical_datum": d["source_vertical_datum"], "source_elevation_ft": d["source_ground_elevation_ft"],
                    "target_vertical_datum": "NAVD88", "vertical_method": d["transformation_method"]}
        locations.append([well, r["easting_m"], r["northing_m"], d["ground_navd88_m"],
                          float(r["completed_depth_ft"]) * FT_TO_M, "", "", json.dumps(metadata),
                          well, r["wl_id"], r["gw_site_id"], r["tr_key"], r["location_class"],
                          r["longitude"], r["latitude"], r["completed_depth_ft"],
                          d["source_ground_elevation_ft"], d["source_vertical_datum"], "NAVD88",
                          d["ground_navd88_m"], r["detail_url"], r["gw_info_url"]])
        for source in sorted(lith[well], key=lambda x: (float(x["from_ft"]), float(x["to_ft"]), int(x["_source_row"]))):
            top, base = float(source["from_ft"]) * FT_TO_M, float(source["to_ft"]) * FT_TO_M
            lrows.append([well, top, base, keywords[source["material_raw"]], source["material_raw"]])
            evidence = {"source_file": "boardman_wells_lithology.csv", "source_row": source["_source_row"],
                        "source_sha256": hashes["boardman_wells_lithology.csv"], "original": source,
                        "contact_state": "source_observation", "boundary_method": "ft_to_m_only"}
            provenance.append([well, "Lithology_Provenance", top, base, json.dumps(evidence)])
        for source in sorted(strat[well], key=lambda x: (float(x["start_depth"]), float(x["end_depth"]), int(x["_source_row"]))):
            top, base = float(source["start_depth"]) * FT_TO_M, float(source["end_depth"]) * FT_TO_M
            evidence = {"source_file": "boardman_wells_stratigraphy.csv", "source_row": source["_source_row"],
                        "source_sha256": hashes["boardman_wells_stratigraphy.csv"], "original": source,
                        "contact_state": "source_interpretation", "boundary_method": "ft_to_m_only",
                        "normalized_label": label_map[source["strat_unit"]], "human_review_status": "unreviewed"}
            srows.append([well, top, base, label_map[source["strat_unit"]], json.dumps(evidence)])
            provenance.append([well, "Stratigraphy_Provenance", top, base, json.dumps(evidence)])
    sheet("Location", ["Bore", "Easting", "Northing", "Elevation", "TD", "Symbol", "Color", "Comments",
                       "well_id", "wl_id", "gw_site_id", "tr_key", "location_class", "source_longitude", "source_latitude",
                       "source_completed_depth_ft", "source_ground_elevation_ft", "source_vertical_datum", "target_vertical_datum",
                       "ground_navd88_m", "detail_url", "gw_info_url"], locations)
    sheet("Lithology", ["Bore", "Depth-1", "Depth-2", "Lithology", "Description"], lrows)
    sheet("Stratigraphy", ["Bore", "Depth-1", "Depth-2", "Stratigraphy", "Comment"], srows)
    type_headers = ["Name", "Pattern", "Size", "Background", "Foreground", "Thk", "Percent", "Density", "G-Value"]
    sheet("Lith Type", type_headers, [[keywords[x], "", "", "", "", "", "", "", i] for i, x in enumerate(descriptions, 1)])
    types = sorted({r[3] for r in srows})
    # Registry values are NOT an approved geological order. No surfaces are built.
    sheet("Strat Type", type_headers, [[x, "", "", "", "", "", "", "", i] for i, x in enumerate(types, 1)])
    sheet("IText Type", ["Name"], [["Lithology_Provenance"], ["Stratigraphy_Provenance"]])
    sheet("IText", ["Bore", "Type", "Depth1", "Depth2", "Value"], sorted(provenance, key=lambda r: (r[0], r[1], r[2], r[3])))
    wells = {r["well_id"] for r in selected}
    for name, title in (("summary", "Source Summary"), ("lithology", "Source Lithology"), ("stratigraphy", "Source Stratigraphy")):
        headings, rows = raw[name]
        sheet(title, ["source_csv_row"] + headings,
              [[r["_source_row"]] + [r[k] for k in headings] for r in rows if r["well_id"] in wells])
    selected_headers = list(selected[0])
    sheet("Selection", selected_headers, [[r[k] for k in selected_headers] for r in selected])
    sheet("Label Map", ["Original", "Normalized", "Method"],
          [[label, label_map[label], "known_parent_to_general" if label in label_parents else "unchanged"]
           for label in sorted({r["strat_unit"] for c in selected for r in strat[c["well_id"]]})])
    sheet("Lithology Dictionary", ["Keyword", "Original material_raw"], [[keywords[x], x] for x in descriptions])
    sheet("Datum Audit", ["well_id", "gw_site_id", "source_datum", "source_ground_ft", "NAVD88_ground_m", "shift_m", "method", "source_url"],
          [[r["well_id"], r["gw_site_id"], datum[r["well_id"]]["source_vertical_datum"],
            datum[r["well_id"]]["source_ground_elevation_ft"], datum[r["well_id"]]["ground_navd88_m"],
            datum[r["well_id"]]["vertical_shift_m"], datum[r["well_id"]]["transformation_method"], r["gw_info_url"]] for r in selected])
    sheet("Read Me", ["Setting", "Value"], [
        ["Purpose", "35 paired well reports, distinct GWIS sites; import and observed-log review trial"],
        ["Horizontal coordinates", "EPSG:26911 NAD83 / UTM zone 11N; metres"],
        ["Report XY source convention", "Longitude/latitude treated as WGS84 as in repository; site datum verified separately"],
        ["Elevation", "NAVD88 metres; original elevation/datum retained; NOAA transformations archived"],
        ["Vertical/depth units", "Metres; source feet multiplied by 0.3048; positive downward from ground"],
        ["Import menu", "Borehole Manager > File > Import > Excel > Row Based"],
        ["Native sheets", "Location, Lithology, Stratigraphy, Lith Type, Strat Type, IText Type, IText"],
        ["Other sheets", "Audit only; do not map these as database import blocks"],
        ["Strat Type G values", "Registry codes in lexical order ONLY. Geologist must approve ordering before modeling."],
        ["Lithology keywords", "Opaque reversible description codes, not classified rock types"],
        ["Interval anomalies", "Preserved unchanged; see Selection qc_flags and source sheets"],
        ["Automatic rules", "Disable Infer Partial Units, Infer Missing Contacts, Insert Missing Units and Create Pinchouts"],
        ["Review provenance", "Imported originals are unreviewed; edited exports require separate snapshots and event audit"],
        ["RockWorks validation", "Workbook verified by independent XLS reader; application import not yet executed"],
    ])
    path = OUT / "boardman_35_paired_spread_rockworks.xls"
    wb.save(str(path))
    # Independent BIFF reader verifies every written cell and its type.
    book = xlrd.open_workbook(path)
    assert path.read_bytes()[:8] == bytes.fromhex("d0cf11e0a1b11ae1")
    for name, (headings, rows) in tables.items():
        ws = book.sheet_by_name(name)
        assert ws.nrows == len(rows) + 1 and ws.ncols == len(headings), name
        assert ws.row_values(0) == headings, name
        for i, row in enumerate(rows, 1):
            for j, expected in enumerate(row):
                cell = ws.cell(i, j)
                if isinstance(expected, (int, float)) and not isinstance(expected, bool):
                    assert cell.ctype == xlrd.XL_CELL_NUMBER and abs(cell.value - expected) < 1e-8, (name, i, j)
                else:
                    assert cell.value == (str(expected) if expected is not None else ""), (name, i, j)
    for wsname in ("Location", "Lithology", "Stratigraphy", "IText"):
        ws = book.sheet_by_name(wsname)
        assert all(ws.cell(i, 0).ctype == xlrd.XL_CELL_TEXT for i in range(1, ws.nrows))
    return path, {name: len(rows) for name, (_, rows) in tables.items()}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "evidence").mkdir(exist_ok=True)
    hashes = {p.name: sha(p) for p in SOURCE.glob("boardman_wells_*.csv")}
    raw = {name: load(name) for name in ("summary", "lithology", "stratigraphy")}
    for _, rows in raw.values():
        for i, r in enumerate(rows, 2):
            r["_source_row"] = str(i)
    lith, strat = defaultdict(list), defaultdict(list)
    for r in raw["lithology"][1]:
        lith[r["well_id"]].append(r)
    for r in raw["stratigraphy"][1]:
        strat[r["well_id"]].append(r)
    selected, pool = select(raw["summary"][1], lith, strat)
    write_csv(OUT / "paired_pool_selection_audit.csv", pool)
    write_csv(OUT / "selected_wells.csv", selected)
    print("Selected 35 distinct GWIS sites across 13 townships", flush=True)
    with ThreadPoolExecutor(max_workers=4) as executor:
        metadata = list(executor.map(site_metadata, selected))
    datum = {r["well_id"]: navd88(r, m, strat[r["well_id"]]) for r, m in zip(selected, metadata)}
    (OUT / "datum_audit.json").write_text(json.dumps(list(datum.values()), indent=2) + "\n")
    print("Source datums:", dict(Counter(r["source_vertical_datum"] for r in datum.values())), flush=True)
    path, counts = workbook(selected, pool, lith, strat, raw, datum, hashes)
    assert hashes == {p.name: sha(p) for p in SOURCE.glob("boardman_wells_*.csv")}, "Authoritative files changed"
    result = {"workbook": path.name, "workbook_sha256": sha(path), "source_sha256": hashes,
              "selected_reports": 35, "unique_gwis_sites": 35, "covered_townships": 13,
              "township_counts": dict(Counter(r["tr_key"] for r in selected)),
              "source_datum_counts": dict(Counter(r["source_vertical_datum"] for r in datum.values())),
              "sheet_rows_excluding_header": counts, "validation": "every XLS cell read back with xlrd; source hashes unchanged",
              "rockworks_import_status": "not_executed", "selection_algorithm": "township_coverage_then_farthest_point_in_EPSG26911"}
    (OUT / "manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
