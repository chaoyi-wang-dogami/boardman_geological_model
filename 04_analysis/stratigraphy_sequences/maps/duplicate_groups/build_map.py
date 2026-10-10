"""Map duplicate interpretation groups from frozen iteration 0; no data cleaning."""
import csv
import hashlib
import itertools
import json
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Rectangle

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
REPO = BASE.parents[1]
SNAPSHOT = BASE / "iter0_10082026_raw_data_copy"
FIELDS = ("start_depth", "end_depth", "start_depth_elev", "end_depth_elev",
          "depth_thickness", "strat_unit", "sample_source", "picked_by", "est_age", "est_age_error")
BLUE, ORANGE, RED = "#2463a6", "#c77716", "#bb3046"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name):
    with (SNAPSHOT / "outputs" / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def distance(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 6371008.8 * 2 * math.asin(math.sqrt(min(1, max(0, h))))


def signature(rows):
    return tuple(sorted(tuple(row[field] for field in FIELDS) for row in rows))


snapshot_manifest = json.loads((SNAPSHOT / "manifest.json").read_text())
input_files = []
for name in ("boardman_wells_summary.csv", "boardman_wells_stratigraphy.csv"):
    source = SNAPSHOT / "outputs" / name
    expected = next(item for item in snapshot_manifest["outputs"] if item["path"].endswith("/" + name))
    if digest(source) != expected["sha256"]:
        raise RuntimeError(f"Snapshot hash mismatch: {name}")
    input_files.append({"path": str(source.relative_to(REPO)), "sha256": digest(source)})
wells = {row["well_id"]: row for row in load("boardman_wells_summary.csv")}
site_reports = defaultdict(lambda: defaultdict(list))
for row in load("boardman_wells_stratigraphy.csv"):
    site_reports[row["gw_site_id"]][row["well_id"]].append(row)
groups = []
for site, reports in sorted(site_reports.items(), key=lambda item: int(item[0])):
    if len(reports) < 2:
        continue
    if len({signature(rows) for rows in reports.values()}) != 1:
        raise RuntimeError(f"Site {site} has conflicting interpretations; not a duplicate group.")
    positions = defaultdict(list)
    for well in sorted(reports):
        row = wells[well]
        lat, lon = float(row["latitude"]), float(row["longitude"])
        if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
            raise RuntimeError(f"Invalid location: {well}")
        positions[(lat, lon)].append({key: row[key] for key in
            ("well_id", "latitude", "longitude", "location_class", "completed_depth_ft", "complete_date")})
    locations = [{"latitude": lat, "longitude": lon, "wells": rows}
                 for (lat, lon), rows in sorted(positions.items())]
    spread = max((distance(a, b) for a, b in itertools.combinations(positions, 2)), default=0)
    groups.append({"site_id": site, "well_count": len(reports), "locations": locations,
                   "same_coordinates": len(locations) == 1, "spread_m": spread,
                   "interval_count": len(next(iter(reports.values())))})
nearby = []
for a, b in itertools.combinations(groups, 2):
    dist, pa, pb = min((distance((p["latitude"], p["longitude"]), (q["latitude"], q["longitude"])),
                        (p["latitude"], p["longitude"]), (q["latitude"], q["longitude"]))
                       for p in a["locations"] for q in b["locations"])
    if dist <= 100:
        nearby.append({"site_a": a["site_id"], "site_b": b["site_id"], "distance_m": dist,
                       "point_a": pa, "point_b": pb,
                       "identical_interpretations": signature(next(iter(site_reports[a["site_id"]].values())))
                       == signature(next(iter(site_reports[b["site_id"]].values())))})
nearby.sort(key=lambda pair: pair["distance_m"])
assert len(groups) == 71
assert sum(group["well_count"] for group in groups) == 166
assert sum(group["same_coordinates"] for group in groups) == 58
assert sum(len(group["locations"]) for group in groups) == 84
assert len(nearby) == 2
assert {(pair["site_a"], pair["site_b"]) for pair in nearby} == {("1077", "13353"), ("135", "680")}
assert all(not pair["identical_interpretations"] for pair in nearby)
data = {"groups": groups, "nearby_pairs": nearby, "threshold_m": 100,
        "statistics": {"groups": 71, "well_records": 166, "single_location_groups": 58,
                       "multiple_location_groups": 13, "recorded_positions": sum(len(g["locations"]) for g in groups)}}
(HERE / "groups.json").write_text(json.dumps(data, indent=2) + "\n")
features = []
with (HERE / "group_locations.csv").open("w", newline="") as stream:
    writer = csv.writer(stream)
    writer.writerow(["gw_site_id", "well_id", "latitude", "longitude", "location_class", "group_spread_m"])
    for group in groups:
        for location in group["locations"]:
            for well in location["wells"]:
                writer.writerow([group["site_id"], well["well_id"], well["latitude"], well["longitude"],
                                 well["location_class"], f'{group["spread_m"]:.3f}'])
            features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates":
                [location["longitude"], location["latitude"]]}, "properties": {
                "gw_site_id": group["site_id"], "well_ids": [w["well_id"] for w in location["wells"]],
                "group_well_count": group["well_count"], "group_spread_m": group["spread_m"]}})
(HERE / "group_locations.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": features}, indent=2) + "\n")

# Static geographic overview and detailed close-pair panels; no external tiles.
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
fig = plt.figure(figsize=(14, 8.5), facecolor="#fbfaf6")
layout = fig.add_gridspec(2, 2, width_ratios=[2.1, 1], hspace=.45, wspace=.28)
overview = fig.add_subplot(layout[:, 0])
overview.set_facecolor("#f1f4f3")
for group in groups:
    color = BLUE if group["same_coordinates"] else ORANGE
    xs = [p["longitude"] for p in group["locations"]]
    ys = [p["latitude"] for p in group["locations"]]
    overview.plot(xs, ys, color=color, linewidth=1, alpha=.65, linestyle="--")
    overview.scatter(xs, ys, color=color, s=24, edgecolors="white", linewidths=.5, zorder=3)
for pair in nearby:
    pa, pb = pair["point_a"], pair["point_b"]
    overview.plot([pa[1], pb[1]], [pa[0], pb[0]], color=RED, linewidth=2.5, zorder=4)
    overview.scatter([pa[1], pb[1]], [pa[0], pb[0]], facecolors="none", edgecolors=RED, s=150, linewidths=1.7, zorder=5)
    overview.annotate(f'{pair["site_a"]} / {pair["site_b"]}', (pa[1], pa[0]), xytext=(10, 10),
                      textcoords="offset points", color=RED, fontsize=9)
overview.set_aspect(1 / math.cos(math.radians(45.75)))
overview.set_xlabel("Longitude (degrees)")
overview.set_ylabel("Latitude (degrees)")
overview.grid(alpha=.2)
overview.set_title("All 71 groups · 166 well records", loc="left", pad=14)
overview.annotate("N ↑", (.95, .94), xycoords="axes fraction", fontsize=13, ha="center")
overview.legend(handles=[Line2D([], [], marker="o", linestyle="", color=BLUE, label="58 groups: one shared location"),
                         Line2D([], [], marker="o", linestyle="", color=ORANGE, label="13 groups: locations differ"),
                         Line2D([], [], color=RED, linewidth=2, label="Different groups within 100 m")],
                loc="upper left", fontsize=9)
# A 5 km east-west scale at its plotted latitude, using the same spherical
# distance convention as the group comparison. Keep the original plot limits.
xmin, xmax = overview.get_xlim()
ymin, ymax = overview.get_ylim()
scale_length_m = 5000
scale_latitude = ymin + .06 * (ymax-ymin)
scale_start_longitude = xmin + .74 * (xmax-xmin)
scale_width_degrees = math.degrees(2 * math.asin(
    math.sin(scale_length_m / (2 * 6371008.8)) / math.cos(math.radians(scale_latitude))))
bar_height = .006 * (ymax-ymin)
for segment, color in enumerate(("#253345", "white")):
    overview.add_patch(Rectangle((scale_start_longitude + segment * scale_width_degrees/2, scale_latitude),
        scale_width_degrees/2, bar_height, facecolor=color, edgecolor="#253345", linewidth=1, zorder=7))
overview.annotate("5 km (5,000 m)", (scale_start_longitude + scale_width_degrees/2, scale_latitude),
    xytext=(0, 12), textcoords="offset points", ha="center", fontsize=10, color="#253345", zorder=8)
overview.annotate("0", (scale_start_longitude, scale_latitude), xytext=(0, -5),
    textcoords="offset points", ha="center", va="top", fontsize=8, zorder=8)
overview.set_xlim(xmin, xmax); overview.set_ylim(ymin, ymax)
scale_end_longitude = scale_start_longitude + scale_width_degrees
assert abs(distance((scale_latitude, scale_start_longitude),
                    (scale_latitude, scale_end_longitude)) - scale_length_m) < .05
for index, pair in enumerate(nearby):
    ax = fig.add_subplot(layout[index, 1])
    ax.set_facecolor("#f1f4f3")
    anchor = pair["point_a"]
    lat0, lon0 = map(math.radians, anchor)
    def xy(point):
        lat, lon = map(math.radians, point)
        return ((lon-lon0)*6371008.8*math.cos(lat0), (lat-lat0)*6371008.8)
    for site in (pair["site_a"], pair["site_b"]):
        group = next(g for g in groups if g["site_id"] == site)
        offsets = []
        for location in group["locations"]:
            x, y = xy((location["latitude"], location["longitude"]))
            offsets.append((x, y))
            ax.scatter(x, y, s=70, color=BLUE if group["same_coordinates"] else ORANGE, zorder=3)
        label_position = (sum(p[0] for p in offsets)/len(offsets), sum(p[1] for p in offsets)/len(offsets))
        ax.annotate(site, label_position, xytext=(8, 7), textcoords="offset points", fontsize=10)
    a, b = xy(pair["point_a"]), xy(pair["point_b"])
    ax.plot([a[0], b[0]], [a[1], b[1]], color=RED, linewidth=2)
    ax.add_patch(Circle(a, 100, fill=False, linestyle="--", color="#929da6", linewidth=1))
    ax.set_aspect("equal")
    ax.set_xlim(-140, 140); ax.set_ylim(-140, 140)
    ax.set_title(f'{pair["site_a"]} ↔ {pair["site_b"]}: {pair["distance_m"]:.0f} m', loc="left")
    ax.set_xlabel("East–west separation (m)"); ax.set_ylabel("North–south (m)")
    ax.grid(alpha=.2)
fig.suptitle("Boardman · duplicate stratigraphy groups", x=.07, ha="left", fontsize=21, fontweight="bold")
fig.text(.07, .035, "Dots show recorded locations. Insets use local distances; dashed circles have a 100 m radius.\n"
         "The two nearby group pairs have different complete interpretations. Source: frozen iteration 0, before deduplication.", fontsize=10)
fig.subplots_adjust(left=.07, right=.96, bottom=.15, top=.9)
fig.savefig(HERE / "duplicate_groups_overview.png", dpi=160, facecolor=fig.get_facecolor())
plt.close(fig)

template = (HERE / "map_template.html").read_text()
safe_json = json.dumps(data).replace("<", "\\u003c")
page = template.replace("__GROUP_DATA__", safe_json).replace("__MAP_JS__", (HERE / "map.js").read_text())
(HERE / "duplicate_groups_map.html").write_text(page)
outputs = ("duplicate_groups_map.html", "duplicate_groups_overview.png", "groups.json",
           "group_locations.csv", "group_locations.geojson")
metadata = {"purpose": "Exploratory view of frozen iteration 0 before deduplication; this generator does not modify well records.",
    "created_local": datetime.now(ZoneInfo("America/Los_Angeles")).isoformat(timespec="seconds"),
    "inputs": input_files, "statistics": data["statistics"], "nearby_pairs": nearby,
    "distance_method": "Haversine, mean Earth radius 6371008.8 m; nearest stored coordinates between groups.",
    "overview_scale": {"length_m": scale_length_m, "reference_latitude": scale_latitude,
                       "start_longitude": scale_start_longitude, "end_longitude": scale_end_longitude},
    "software": {"matplotlib": matplotlib.__version__, "leaflet": "1.9.4, browser CDN"},
    "basemap": {"provider": "USGS The National Map", "service": "USGSTopo",
                "tile_url": "https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/tile/{z}/{y}/{x}",
                "max_native_zoom": 16, "alternative": "Wells only"},
    "sources": [{"path": name, "sha256": digest(HERE / name)} for name in ("build_map.py", "map.js", "map_template.html")],
    "outputs": [{"path": name, "sha256": digest(HERE / name)} for name in outputs],
    "checks": {"snapshot_input_hashes": "pass", "group_count_71": "pass", "well_count_166": "pass",
               "single_location_groups_58": "pass", "nearby_pairs_2": "pass", "nearby_interpretations_differ": "pass",
               "overview_scale_length_5000_m": "pass"}}
(HERE / "map_manifest.json").write_text(json.dumps(metadata, indent=2) + "\n")
print(json.dumps({"map": str((HERE / "duplicate_groups_map.html").relative_to(REPO)), **data["statistics"]}, indent=2))
