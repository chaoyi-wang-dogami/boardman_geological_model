"""Audit a provisional township-balanced sample; do not alter processed data.

Run with the repository Python environment (requests and lxml required).
The output is a preflight audit, not a RockWorks import workbook.
"""

import csv
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import requests
from lxml import html

EVAL = Path(__file__).resolve().parents[1]
REPO = EVAL.parents[1]
SOURCE = REPO / "03_processed/boardman_19_townships"
OUT = EVAL / "input/35_well_preflight"


def read(name):
    with (SOURCE / f"boardman_wells_{name}.csv").open(newline="") as stream:
        return list(csv.DictReader(stream))


def candidates():
    summary = read("summary")
    lith = defaultdict(list)
    strat = defaultdict(list)
    for row in read("lithology"):
        lith[row["well_id"]].append(row)
    for row in read("stratigraphy"):
        strat[row["well_id"]].append(row)

    def rank(row):
        well = row["well_id"]
        labels = [x["strat_unit"] for x in strat[well]]
        max_depth = max(float(x["end_depth"]) for x in strat[well])
        td = float(row["completed_depth_ft"] or 0)
        # Prefer report lithology, no repeated labels, consistent TD, and A/B.
        return (not bool(lith[well]), len(labels) != len(set(labels)),
                td <= 0 or max_depth > td, row["location_class"] not in ("A", "B"),
                -len(strat[well]), -len(lith[well]), well)

    by_township = defaultdict(list)
    for row in summary:
        if strat[row["well_id"]]:
            by_township[row["tr_key"]].append(row)
    selected = []
    used_sites = set()
    # Scarce townships get first choice; distinct GWIS IDs across the sample.
    order = sorted(by_township, key=lambda tr: (
        len({r["gw_site_id"] for r in by_township[tr]}), tr))
    for township in order:
        target = min(2, len({r["gw_site_id"] for r in by_township[township]}))
        chosen = []
        for row in sorted(by_township[township], key=rank):
            if row["gw_site_id"] in used_sites:
                continue
            chosen.append(row)
            used_sites.add(row["gw_site_id"])
            if len(chosen) == target:
                break
        assert len(chosen) == target, f"Unresolved cross-township site collision: {township}"
        selected.extend(chosen)
    assert len(selected) == 35
    assert len({r["well_id"] for r in selected}) == 35
    assert len({r["gw_site_id"] for r in selected}) == 35
    assert len({r["tr_key"] for r in selected}) == 19
    return sorted(selected, key=lambda r: (r["tr_key"], r["well_id"])), lith, strat


def fetch(row):
    site = row["gw_site_id"]
    url = row["gw_info_url"]
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    root = html.fromstring(response.content)
    prefix = "ctl00_PageData_uc_gw_site_location_"

    def value(suffix):
        elements = root.xpath("//*[@id=$ident]", ident=prefix + suffix)
        return elements[0].text_content().strip() if elements else ""

    datum = value("lb_elevation_datum")
    elevation = value("lb_lsd_elevation")
    if not datum or not elevation:
        raise ValueError(f"Site {site}: elevation or datum not disclosed")
    table = root.xpath("//table[@id='ctl00_PageData_uc_gw_lithology_GridView1']")
    rows = []
    if table:
        for tr in table[0].xpath(".//tr"):
            cells = [" ".join(td.text_content().split()) for td in tr.xpath("./td")]
            if len(cells) >= 3:
                try:
                    float(cells[0]); float(cells[1])
                except ValueError:
                    continue
                rows.append(cells)
    # Retain full live-page evidence without modifying saved authoritative data.
    (OUT / "evidence" / f"gwis_{site}.html.gz").write_bytes(gzip.compress(response.content, mtime=0))
    metadata = {
        "gwis_lsd_elevation_ft": elevation,
        "gwis_vertical_datum": datum,
        "gwis_elevation_source": value("lb_lsd_elevation_source"),
        "gwis_elevation_accuracy_raw": value("lb_lsd_accuracy"),
        "gwis_horizontal_datum": value("lb_lat_long_datum"),
        "gwis_coordinate_source": value("lb_lat_long_source_desc"),
        "gwis_lithology_rows_visible": len(rows),
        "gwis_lithology_pager_present": bool(table and table[0].xpath(".//a[contains(@href, 'Page$')]")),
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "live_page_sha256": hashlib.sha256(response.content).hexdigest(),
    }
    (OUT / "evidence" / f"gwis_{site}_lithology_visible.json").write_text(
        json.dumps({"source_url": url, "metadata": metadata, "rows": rows}, indent=2) + "\n")
    return metadata


def main():
    selected, lith, strat = candidates()
    (OUT / "evidence").mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        metadata = list(pool.map(fetch, selected))
    records = []
    for row, live in zip(selected, metadata):
        well = row["well_id"]
        source_ground = sorted({round(float(x[depth]) + float(x[elev]), 6)
            for x in strat[well]
            for depth, elev in (("start_depth", "start_depth_elev"), ("end_depth", "end_depth_elev"))
            if x[elev]})
        records.append({"sample_status": "provisional_not_imported", **row,
            "processed_lithology_rows": len(lith[well]),
            "processed_stratigraphy_rows": len(strat[well]),
            "csv_implied_ground_elevations_ft": json.dumps(source_ground),
            "csv_ground_matches_live_elevation": bool(source_ground) and all(
                abs(z - float(live["gwis_lsd_elevation_ft"].replace(',', ''))) <= 0.011 for z in source_ground),
            **live})
    with (OUT / "candidate_source_audit.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
              for path in sorted(SOURCE.glob("boardman_wells_*.csv"))}
    (OUT / "source_hashes.json").write_text(json.dumps(hashes, indent=2) + "\n")
    print("Candidate wells:", len(records))
    print("Vertical datums:", dict(Counter(r["gwis_vertical_datum"] for r in records)))
    print("Processed lithology available:", sum(r["processed_lithology_rows"] > 0 for r in records))
    print("Missing processed lithology, online GWIS rows available:", sum(
        r["processed_lithology_rows"] == 0 and r["gwis_lithology_rows_visible"] > 0 for r in records))
    print("Neither processed nor visible GWIS lithology:", sum(
        r["processed_lithology_rows"] == 0 and r["gwis_lithology_rows_visible"] == 0 for r in records))
    print("CSV/live elevation mismatches:", sum(not r["csv_ground_matches_live_elevation"] for r in records))
    print("Audit:", OUT / "candidate_source_audit.csv")


if __name__ == "__main__":
    main()
