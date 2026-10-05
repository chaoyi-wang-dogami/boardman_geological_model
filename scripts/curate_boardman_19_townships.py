#!/usr/bin/env python3
"""Curate the saved 19-township OWRD reports into three joinable CSV tables.

Run: uv run python scripts/curate_boardman_19_townships.py
Only local files are read; the original downloads are never changed.
"""

from __future__ import annotations

import csv
import os
from collections import Counter
from pathlib import Path

from download_owrd import build_where_clause, load_config


ROOT = Path(__file__).resolve().parents[1]
WELLS = ROOT / "01_raw/wells"
INVENTORY = ROOT / "01_raw/owrd/wells_raw.csv"
LINKS = ROOT / "01_raw/owrd/gwis_stratigraphy_links.csv"
OUTPUT = ROOT / "03_processed/boardman_19_townships"

SUMMARY_FIELDS = [
    "well_id", "county", "wl_nbr", "wl_id", "tr_key", "gw_site_id",
    "completed_depth_ft", "complete_date", "received_date",
    "has_lithology", "lithology_count", "has_stratigraphy", "strat_count",
    "detail_url", "gw_info_url", "longitude", "latitude", "location_class",
]
LITHOLOGY_FIELDS = [
    "well_id", "county", "wl_nbr", "wl_id", "interval_no", "from_ft",
    "to_ft", "thickness_ft", "material_raw", "static_water_level_raw",
    "completed_depth_ft", "complete_date", "latitude", "longitude", "detail_url",
]
STRATIGRAPHY_FIELDS = [
    "well_id", "wl_nbr", "wl_id", "gw_site_id", "start_depth", "end_depth",
    "start_depth_elev", "end_depth_elev", "depth_thickness", "strat_unit",
    "sample_source", "picked_by", "est_age", "est_age_error",
    "completed_depth_ft", "complete_date", "latitude", "longitude",
    "gw_info_url", "source_kind", "scraped_at",
]
RAW_LITHOLOGY_FIELDS = [
    "well_id", "well_log", "interval_no", "from_ft", "to_ft", "thickness_ft",
    "material_raw", "static_water_level_raw",
]
RAW_STRATIGRAPHY_FIELDS = [
    "well_folder", "wl_id", "gw_site_id", "start_depth", "end_depth",
    "start_depth_elev", "end_depth_elev", "depth_thickness", "strat_unit",
    "sample_source", "picked_by", "est_age", "est_age_error", "gw_info_url",
    "source_kind", "scraped_at",
]


def read_csv(path: Path, expected_fields: list[str] | None = None) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if expected_fields is not None and reader.fieldnames != expected_fields:
            raise ValueError(f"Unexpected columns in {path}: {reader.fieldnames}")
        return list(reader)


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def curate() -> Counter:
    reports = read_csv(INVENTORY)
    config = load_config(ROOT / "00_config/owrd_download.yml")
    _, township_keys = build_where_clause(config)
    if len(township_keys) != 19:
        raise ValueError(f"Expected 19 configured townships, found {len(township_keys)}")
    unexpected = {row["tr_key"] for row in reports} - set(township_keys)
    if unexpected:
        raise ValueError(f"Saved inventory contains reports outside the 19 townships: {sorted(unexpected)}")
    links = read_csv(LINKS)
    by_id = {row["wl_id"]: row for row in reports}
    if len(by_id) != len(reports):
        raise ValueError("Duplicate wl_id values in the saved report inventory")
    by_link = {row["wl_id"]: row for row in links}
    if len(by_link) != len(links):
        raise ValueError("Duplicate wl_id values in GWIS report links")
    if set(by_link) - set(by_id):
        raise ValueError("GWIS links include reports outside the saved 19-township inventory")

    summary_rows: list[dict[str, str]] = []
    lith_rows: list[dict[str, str]] = []
    strat_rows: list[dict[str, str]] = []

    for report in reports:
        wl_id = report["wl_id"]
        folder = report["well_folder"]
        county = report["wl_county_code"]
        number = report["wl_nbr"]
        well_dir = WELLS / folder
        lith_path = well_dir / "lithology.csv"
        if not lith_path.exists():
            raise FileNotFoundError(f"Missing well-report lithology file: {lith_path}")
        lithology = read_csv(lith_path, RAW_LITHOLOGY_FIELDS)
        for interval in lithology:
            if interval["well_id"] != wl_id or interval["well_log"] != folder:
                raise ValueError(f"Lithology report identifier mismatch: {lith_path}")
            lith_rows.append({
                "well_id": folder, "county": county, "wl_nbr": number, "wl_id": wl_id,
                "interval_no": interval["interval_no"],
                "from_ft": interval["from_ft"], "to_ft": interval["to_ft"],
                "thickness_ft": interval["thickness_ft"],
                "material_raw": interval["material_raw"],
                "static_water_level_raw": interval["static_water_level_raw"],
                "completed_depth_ft": report["completed_depth"],
                "complete_date": report["complete_date_iso"],
                "latitude": report["latitude_dec"], "longitude": report["longitude_dec"],
                "detail_url": report["detail_url"],
            })

        link = by_link.get(wl_id)
        strat_path = well_dir / "stratigraphy.csv"
        if link and link["well_folder"] != folder:
            raise ValueError(f"GWIS link folder mismatch for wl_id {wl_id}")
        if link and not strat_path.exists():
            raise FileNotFoundError(f"Missing linked GWIS stratigraphy file: {strat_path}")
        if not link and strat_path.exists():
            raise ValueError(f"Unlinked report has a GWIS stratigraphy file: {strat_path}")
        stratigraphy = read_csv(strat_path, RAW_STRATIGRAPHY_FIELDS) if link else []
        for interval in stratigraphy:
            if (
                interval["well_folder"] != folder
                or interval["wl_id"] != wl_id
                or interval["gw_site_id"] != link["gw_site_id"]
            ):
                raise ValueError(f"GWIS stratigraphy identifier mismatch: {strat_path}")
            strat_rows.append({
                "well_id": folder, "wl_nbr": number, "wl_id": wl_id,
                "gw_site_id": interval["gw_site_id"],
                **{field: interval[field] for field in RAW_STRATIGRAPHY_FIELDS[3:]},
                "completed_depth_ft": report["completed_depth"],
                "complete_date": report["complete_date_iso"],
                "latitude": report["latitude_dec"], "longitude": report["longitude_dec"],
            })

        summary_rows.append({
            "well_id": folder, "county": county, "wl_nbr": number, "wl_id": wl_id,
            "tr_key": report["tr_key"],
            "gw_site_id": link["gw_site_id"] if link else "",
            "completed_depth_ft": report["completed_depth"],
            "complete_date": report["complete_date_iso"],
            "received_date": report["received_date_iso"],
            "has_lithology": "TRUE" if lithology else "FALSE",
            "lithology_count": str(len(lithology)),
            "has_stratigraphy": "TRUE" if stratigraphy else "FALSE",
            "strat_count": str(len(stratigraphy)),
            "detail_url": report["detail_url"],
            "gw_info_url": (
                f"https://apps.wrd.state.or.us/apps/gw/gw_info/gw_info_report/"
                f"gw_details.aspx?gw_site_id={link['gw_site_id']}" if link else ""
            ),
            "longitude": report["longitude_dec"], "latitude": report["latitude_dec"],
            "location_class": report["location_class"],
        })

    if sum(int(row["lithology_count"]) for row in summary_rows) != len(lith_rows):
        raise ValueError("Summary lithology counts do not match interval rows")
    if sum(int(row["strat_count"]) for row in summary_rows) != len(strat_rows):
        raise ValueError("Summary stratigraphy counts do not match interval rows")

    write_csv(OUTPUT / "boardman_wells_summary.csv", SUMMARY_FIELDS, summary_rows)
    write_csv(OUTPUT / "boardman_wells_lithology.csv", LITHOLOGY_FIELDS, lith_rows)
    write_csv(OUTPUT / "boardman_wells_stratigraphy.csv", STRATIGRAPHY_FIELDS, strat_rows)
    return Counter({
        "reports": len(summary_rows),
        "reports_with_lithology": sum(row["has_lithology"] == "TRUE" for row in summary_rows),
        "lithology_rows": len(lith_rows),
        "reports_with_stratigraphy": sum(row["has_stratigraphy"] == "TRUE" for row in summary_rows),
        "stratigraphy_rows": len(strat_rows),
    })


if __name__ == "__main__":
    counts = curate()
    for name, count in counts.items():
        print(f"{name}: {count}")
    print(f"Output: {OUTPUT}")
