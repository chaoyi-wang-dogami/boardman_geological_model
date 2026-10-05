#!/usr/bin/env python3
"""Plot scraped Morrow and Umatilla wells and their interval-data subsets.

Run with: uv run python scripts/plot_scraped_waterwell_locations.py
Locations come from the live OWRD well-report FeatureServer, keyed by wl_id.
The processed summaries are used as a fallback when the service has no record.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter
import pandas as pd

from download_owrd import build_session, load_config


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "03_processed/waterwells_after2010_300ftplus_NM_04162026"
OUTPUT = DATA_DIR / "waterwells_after2010_300ftplus_MU_locs.png"
STRAT_OUTPUT = DATA_DIR / "waterwells_after2010_300ftplus_MU_stratigraphy_locs.png"
LITH_OUTPUT = DATA_DIR / "waterwells_after2010_300ftplus_MU_lithology_locs.png"
BOUNDARY = ROOT / "02_gis/reference/plss_townships.geojson"
SUMMARY_FILES = {
    "MORR": DATA_DIR / "Morrow County/morr_wells_summary_webscrape_NM.csv",
    "UMAT": DATA_DIR / "Umatilla County/umatpost2010_wells_summary_umatillacounty.csv",
}
STRAT_FILES = {
    "MORR": DATA_DIR / "Morrow County/morr_wells_stratigraphy_webscrape_NM.csv",
    "UMAT": DATA_DIR / "Umatilla County/umatpost2010_wells_stratigraphy_webscrape_NM.csv",
}
LITH_FILES = {
    "MORR": DATA_DIR / "Morrow County/morr_wells_lithology_webscrape_NM.csv",
    "UMAT": DATA_DIR / "Umatilla County/umatpost2010_wells_lithology_webscrape_NM.csv",
}
COLORS = {"MORR": "#266486", "UMAT": "#d37b32"}


def read_summaries() -> pd.DataFrame:
    frames = []
    for county, path in SUMMARY_FILES.items():
        frame = pd.read_csv(path, dtype=str, keep_default_na=False)
        if not frame.county.eq(county).all():
            raise ValueError(f"County mismatch in {path}")
        frames.append(frame[["well_id", "county", "wl_nbr", "wl_id", "longitude", "latitude"]])
    wells = pd.concat(frames, ignore_index=True)
    if wells.wl_id.duplicated().any():
        raise ValueError("Scraped summary contains duplicate wl_id values")
    return wells


def fetch_locations(wells: pd.DataFrame) -> pd.DataFrame:
    config = load_config(ROOT / "00_config/owrd_download.yml")
    url = config["owrd"]["layer_url"].rstrip("/") + "/query"
    session = build_session(config)
    records = []
    ids = wells.wl_id.tolist()
    for start in range(0, len(ids), 150):
        batch = ids[start:start + 150]
        response = session.get(url, params={
            "f": "json", "where": "wl_id IN (" + ",".join(batch) + ")",
            "outFields": "wl_id,wl_county_code,wl_nbr,longitude_dec,latitude_dec",
            "returnGeometry": "true", "outSR": 4326,
        }, timeout=45)
        response.raise_for_status()
        payload = response.json()
        if "error" in payload:
            raise RuntimeError(f"OWRD query error: {payload['error']}")
        for feature in payload.get("features", []):
            attrs = feature["attributes"]
            geometry = feature.get("geometry") or {}
            records.append({
                "wl_id": str(attrs["wl_id"]),
                "owrd_county": attrs["wl_county_code"],
                "owrd_wl_nbr": str(attrs["wl_nbr"]),
                "source_lon": attrs["longitude_dec"],
                "source_lat": attrs["latitude_dec"],
                "map_lon": geometry.get("x"),
                "map_lat": geometry.get("y"),
            })
    locations = pd.DataFrame(records)
    if locations.wl_id.duplicated().any():
        raise ValueError("OWRD returned duplicate wl_id values")
    result = wells.merge(locations, on="wl_id", how="left", validate="one_to_one")
    matched = result.owrd_county.notna()
    if (result.loc[matched, "county"] != result.loc[matched, "owrd_county"]).any():
        raise ValueError("OWRD county differs from a scraped summary")
    if (result.loc[matched, "wl_nbr"] != result.loc[matched, "owrd_wl_nbr"]).any():
        raise ValueError("OWRD well number differs from a scraped summary")

    # Prefer source coordinates, then OWRD's mapped feature, then scraped values.
    for column in ["source_lon", "source_lat", "map_lon", "map_lat", "longitude", "latitude"]:
        result[column] = pd.to_numeric(result[column], errors="coerce")
    result["lon"] = result.source_lon.fillna(result.map_lon).fillna(result.longitude)
    result["lat"] = result.source_lat.fillna(result.map_lat).fillna(result.latitude)
    plausible = result.lon.between(-125, -116) & result.lat.between(42, 47)
    result.loc[~plausible, ["lon", "lat"]] = float("nan")
    return result


def read_interval_ids(wells: pd.DataFrame, files: dict[str, Path]) -> set[str]:
    ids: set[str] = set()
    for county, path in files.items():
        frame = pd.read_csv(path, dtype=str, keep_default_na=False)
        if not frame.well_id.str.startswith(county + "_").all():
            raise ValueError(f"County mismatch in {path}")
        ids.update(frame.wl_id)
    unknown = ids - set(wells.wl_id)
    if unknown:
        raise ValueError(f"Interval reports missing from summaries: {sorted(unknown)}")
    return ids


def make_plot(points: gpd.GeoDataFrame, townships: gpd.GeoDataFrame,
              selected_ids: set[str], output: Path, title: str,
              extent: tuple[float, float, float, float],
              missing_ids: list[str]) -> tuple[tuple[float, float], tuple[float, float]]:
    selected = points[points.wl_id.isin(selected_ids)]
    if selected.empty:
        raise ValueError("No scraped wells have usable locations")

    fig, ax = plt.subplots(figsize=(12, 7.6))
    townships.plot(ax=ax, facecolor="#eee9d8", edgecolor="#a9a28e",
                   linewidth=0.55, zorder=1)
    gpd.GeoSeries([townships.union_all()], crs=townships.crs).boundary.plot(
        ax=ax, color="#3a433d", linewidth=1.7, zorder=2
    )
    for county, label in [("MORR", "Morrow"), ("UMAT", "Umatilla")]:
        group = selected[selected.county == county]
        ax.scatter(group.geometry.x, group.geometry.y, s=22, c=COLORS[county],
                   alpha=0.7, edgecolors="white", linewidths=0.25,
                   zorder=3, label=f"{label} ({len(group)})")

    xmin, xmax, ymin, ymax = extent
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect("equal", adjustable="box")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value / 1000:.0f}"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value / 1000:.0f}"))
    ax.set(xlabel="UTM zone 11N easting (km)", ylabel="UTM zone 11N northing (km)",
           title=title)
    ax.grid(alpha=0.18, linewidth=0.6)
    handles = [
        Line2D([], [], marker="o", linestyle="", markerfacecolor=COLORS[code],
               markeredgecolor="white", markersize=8,
               label=f"{label} ({(selected.county == code).sum()})")
        for code, label in [("MORR", "Morrow"), ("UMAT", "Umatilla")]
    ]
    handles.append(Patch(facecolor="#eee9d8", edgecolor="#3a433d",
                         label="19-township study area"))
    ax.legend(handles=handles, loc="lower right", framealpha=0.96)
    note = (f"OWRD report locations queried {date.today():%Y-%m-%d}; "
            f"{len(selected)} of {len(selected_ids)} selected reports located.")
    if missing_ids:
        note += " Unlocated: " + ", ".join(missing_ids) + "."
    fig.text(0.5, 0.015, note + " Coordinates may be approximate.",
             ha="center", fontsize=8, color="#444444")
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    limits = ax.get_xlim(), ax.get_ylim()
    fig.savefig(output, dpi=300)
    plt.close(fig)
    print(f"Saved {output} at 300 dpi; plotted {len(selected)} of {len(selected_ids)} reports")
    if missing_ids:
        print("Unlocated IDs:", ", ".join(missing_ids))
    return limits


if __name__ == "__main__":
    wells = fetch_locations(read_summaries())
    mapped = wells[wells.lon.notna() & wells.lat.notna()].copy()
    if mapped.empty:
        raise ValueError("No scraped wells have usable locations")
    points = gpd.GeoDataFrame(
        mapped, geometry=gpd.points_from_xy(mapped.lon, mapped.lat), crs="EPSG:4326"
    ).to_crs("EPSG:32611")
    townships = gpd.read_file(BOUNDARY).to_crs(points.crs)
    if len(townships) != 19:
        raise ValueError(f"Expected 19 township polygons, found {len(townships)}")
    bounds = points.total_bounds
    township_bounds = townships.total_bounds
    xmin = min(bounds[0], township_bounds[0])
    ymin = min(bounds[1], township_bounds[1])
    xmax = max(bounds[2], township_bounds[2])
    ymax = max(bounds[3], township_bounds[3])
    xpad = (xmax - xmin) * 0.06
    ypad = (ymax - ymin) * 0.06
    extent = (xmin - xpad, xmax + xpad, ymin - ypad, ymax + ypad)
    full_ids = set(wells.wl_id)
    strat_ids = read_interval_ids(wells, STRAT_FILES)
    lith_ids = read_interval_ids(wells, LITH_FILES)
    full_missing = wells.loc[~wells.wl_id.isin(points.wl_id), "well_id"].tolist()
    strat_missing = wells.loc[wells.wl_id.isin(strat_ids) &
                              ~wells.wl_id.isin(points.wl_id), "well_id"].tolist()
    lith_missing = wells.loc[wells.wl_id.isin(lith_ids) &
                             ~wells.wl_id.isin(points.wl_id), "well_id"].tolist()
    full_limits = make_plot(points, townships, full_ids, OUTPUT,
                            "Scraped Morrow and Umatilla well-report locations",
                            extent, full_missing)
    strat_limits = make_plot(points, townships, strat_ids, STRAT_OUTPUT,
                             "Scraped wells with stratigraphy", extent, strat_missing)
    lith_limits = make_plot(points, townships, lith_ids, LITH_OUTPUT,
                            "Scraped wells with lithology", extent, lith_missing)
    if not (full_limits == strat_limits == lith_limits):
        raise AssertionError("All maps must use exactly the same axis limits")
