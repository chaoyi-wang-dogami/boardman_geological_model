#!/usr/bin/env python3
"""Map saved Boardman reports and their lithology/stratigraphy subsets.

Run: uv run python scripts/plot_boardman_19_townships.py
The three 300-dpi maps use the same 19-township extent and only local files.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "03_processed/boardman_19_townships"
SUMMARY = DATA_DIR / "boardman_wells_summary.csv"
LITHOLOGY = DATA_DIR / "boardman_wells_lithology.csv"
STRATIGRAPHY = DATA_DIR / "boardman_wells_stratigraphy.csv"
BOUNDARY = ROOT / "02_gis/reference/plss_townships.geojson"
CRS = "EPSG:32611"
COUNTIES = [
    ("MORR", "Morrow", "#266486"),
    ("UMAT", "Umatilla", "#d37b32"),
    ("GILL", "Gilliam", "#617b52"),
]


def read_points() -> gpd.GeoDataFrame:
    reports = pd.read_csv(SUMMARY, dtype=str, keep_default_na=False)
    if reports.wl_id.duplicated().any():
        raise ValueError("Summary has duplicate wl_id values")
    for field, path in (("has_lithology", LITHOLOGY), ("has_stratigraphy", STRATIGRAPHY)):
        intervals = pd.read_csv(path, dtype=str, usecols=["wl_id"])
        ids = set(intervals.wl_id)
        if ids - set(reports.wl_id):
            raise ValueError(f"Interval IDs in {path} are missing from the summary")
        selected = set(reports.loc[reports[field] == "TRUE", "wl_id"])
        if ids != selected:
            raise ValueError(f"Summary {field} flags disagree with {path}")

    reports["longitude"] = pd.to_numeric(reports.longitude, errors="coerce")
    reports["latitude"] = pd.to_numeric(reports.latitude, errors="coerce")
    plausible = reports.longitude.between(-125, -116) & reports.latitude.between(42, 47)
    reports.loc[~plausible, ["longitude", "latitude"]] = float("nan")
    return gpd.GeoDataFrame(
        reports,
        geometry=gpd.points_from_xy(reports.longitude, reports.latitude),
        crs="EPSG:4326",
    ).to_crs(CRS)


def map_extent(townships: gpd.GeoDataFrame) -> tuple[float, float, float, float]:
    xmin, ymin, xmax, ymax = townships.total_bounds
    xpad = (xmax - xmin) * 0.06
    ypad = (ymax - ymin) * 0.06
    return xmin - xpad, xmax + xpad, ymin - ypad, ymax + ypad


def make_plot(
    points: gpd.GeoDataFrame,
    townships: gpd.GeoDataFrame,
    field: str | None,
    title: str,
    output: Path,
    extent: tuple[float, float, float, float],
    marker_size: float,
    opacity: float,
) -> tuple[tuple[float, float], tuple[float, float], int, int]:
    selected = points if field is None else points[points[field] == "TRUE"]
    xmin, xmax, ymin, ymax = extent
    visible = selected[
        selected.geometry.x.between(xmin, xmax)
        & selected.geometry.y.between(ymin, ymax)
    ]
    omitted = len(selected) - len(visible)
    if visible.empty:
        raise ValueError(f"No visible reports for {title}")

    fig, ax = plt.subplots(figsize=(12, 7.6))
    townships.plot(
        ax=ax, facecolor="#eee9d8", edgecolor="#a9a28e",
        linewidth=0.55, zorder=1,
    )
    gpd.GeoSeries([townships.union_all()], crs=townships.crs).boundary.plot(
        ax=ax, color="#3a433d", linewidth=1.7, zorder=2,
    )
    handles = []
    for code, label, color in COUNTIES:
        group = visible[visible.county == code]
        if group.empty:
            continue
        ax.scatter(
            group.geometry.x, group.geometry.y,
            s=marker_size, c=color, alpha=opacity,
            edgecolors="white", linewidths=0.15,
            rasterized=True, zorder=3,
        )
        handles.append(Line2D(
            [], [], marker="o", linestyle="", markerfacecolor=color,
            markeredgecolor="white", markersize=8,
            label=f"{label} ({len(group):,})",
        ))
    handles.append(Patch(
        facecolor="#eee9d8", edgecolor="#3a433d",
        label="19-township study area",
    ))
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect("equal", adjustable="box")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value / 1000:.0f}"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value / 1000:.0f}"))
    ax.set(
        xlabel="UTM zone 11N easting (km)",
        ylabel="UTM zone 11N northing (km)",
        title=title,
    )
    ax.grid(alpha=0.18, linewidth=0.6)
    ax.legend(handles=handles, loc="lower right", framealpha=0.96)
    note = (
        f"Saved OWRD report coordinates; {len(visible):,} of {len(selected):,} "
        "selected reports visible."
    )
    if omitted:
        note += f" {omitted} outside the common map extent."
    note += " Coordinates may be approximate; markers can overlap."
    fig.text(0.5, 0.015, note, ha="center", fontsize=8, color="#444444")
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    limits = ax.get_xlim(), ax.get_ylim()
    fig.savefig(output, dpi=300)
    plt.close(fig)
    print(f"Saved {output.name}: {len(visible):,}/{len(selected):,} reports visible")
    return limits[0], limits[1], len(visible), omitted


def main() -> None:
    points = read_points()
    townships = gpd.read_file(BOUNDARY).to_crs(CRS)
    if len(townships) != 19:
        raise ValueError(f"Expected 19 township polygons, found {len(townships)}")
    extent = map_extent(townships)
    maps = [
        (None, "Boardman 19-township well-report locations", "boardman_19_townships_locs.png", 7, 0.38),
        ("has_lithology", "Boardman well reports with structured lithology", "boardman_19_townships_lithology_locs.png", 11, 0.55),
        ("has_stratigraphy", "Boardman well reports with GWIS stratigraphy", "boardman_19_townships_stratigraphy_locs.png", 20, 0.75),
    ]
    limits = []
    for field, title, filename, size, alpha in maps:
        limits.append(make_plot(
            points, townships, field, title, DATA_DIR / filename,
            extent, size, alpha,
        )[:2])
    if not (limits[0] == limits[1] == limits[2]):
        raise AssertionError("The maps do not have identical coordinate limits")


if __name__ == "__main__":
    main()
