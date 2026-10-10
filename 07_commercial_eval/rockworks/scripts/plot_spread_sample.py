"""Plot the paired pool and selected reports against the 19-township AOI."""
import csv
from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

EVAL = Path(__file__).resolve().parents[1]
REPO = EVAL.parents[1]
DATA = EVAL / "input/35_paired_spread"
FIGURE = EVAL / "figures/35_paired_spread_coverage.png"


def main():
    with (DATA / "paired_pool_selection_audit.csv").open() as stream:
        pool = list(csv.DictReader(stream))
    selected = [r for r in pool if r["selected"] == "True"]
    townships = gpd.read_file(REPO / "02_gis/reference/plss_townships.geojson").to_crs(26911)
    covered = {r["tr_key"] for r in selected}
    fig, ax = plt.subplots(figsize=(11, 8))
    for _, row in townships.iterrows():
        label = row["TWNSHPLAB"]
        township, rang = label.split()
        key = f"WM{int(township[1:-1])}.00N{int(rang[1:-1])}.00E"
        gpd.GeoSeries([row.geometry], crs=26911).plot(ax=ax,
            color="#edf3ef" if key in covered else "#f4e4d9",
            edgecolor="#a8aaa4", linewidth=0.8)
        point = row.geometry.representative_point()
        ax.text(point.x, point.y, label, ha="center", va="center", fontsize=8,
                color="#60645f", zorder=2)
    ax.scatter([float(r["easting_m"]) for r in pool], [float(r["northing_m"]) for r in pool],
               s=14, color="#969b9b", alpha=0.65, label="Paired reports (121; 112 GWIS sites)", zorder=3)
    for flagged, marker, label, color in ((False, "o", "Selected A/B coordinates", "#17697b"),
                                          (True, "^", "Selected C/D coordinates", "#b56927")):
        rows = [r for r in selected if (r["location_class"] in ("C", "D")) == flagged]
        ax.scatter([float(r["easting_m"]) for r in rows], [float(r["northing_m"]) for r in rows],
                   s=65, color=color, marker=marker, edgecolors="white", linewidths=0.7,
                   label=f"{label} ({len(rows)})", zorder=4)
    xmin, ymin, xmax, ymax = townships.total_bounds
    ax.set_xlim(xmin - 1500, xmax + 1500); ax.set_ylim(ymin - 1500, ymax + 1500)
    ax.set_aspect("equal")
    ax.set_title("Boardman RockWorks trial: 35 paired reports / 35 distinct GWIS sites", fontsize=13, loc="left", pad=16)
    ax.set_xlabel("Easting (km) — NAD83 / UTM zone 11N")
    ax.set_ylabel("Northing (km)")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: f"{x / 1000:.0f}"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, pos: f"{y / 1000:.0f}"))
    ax.legend(loc="lower left", fontsize=8, framealpha=0.95)
    fig.text(0.12, 0.04, "13 townships with paired data covered; peach townships have no processed paired reports.\n"
             "Township coverage uses report tr_key. Symbols retain reported locations and coordinate-quality classes.", fontsize=8)
    fig.subplots_adjust(bottom=0.14)
    FIGURE.parent.mkdir(exist_ok=True)
    fig.savefig(FIGURE, dpi=220, facecolor="white")
    plt.close(fig)
    print(FIGURE)


if __name__ == "__main__":
    main()
