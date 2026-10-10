"""Compare frozen iteration 0 and iteration 1 without changing either."""
import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

parser = argparse.ArgumentParser(description="Reproduce the before/after plot in a new preview directory.")
parser.add_argument("--output-dir", type=Path, required=True, help="New directory outside completed iterations")
args = parser.parse_args()
AFTER = Path(__file__).resolve().parent.parent
HERE = args.output_dir.resolve()
BASE = AFTER.parent
REPO = BASE.parents[1]
BEFORE = BASE / "iter0_10082026_raw_data_copy"
if HERE.is_relative_to(AFTER) or HERE.is_relative_to(BEFORE):
    raise SystemExit("Choose a preview directory outside completed iterations; their recorded plots are retained unchanged.")
if HERE.exists():
    raise SystemExit("Output directory already exists; choose a new directory.")
HERE.mkdir(parents=True)
BLUE, ORANGE, GREEN = "#2463a6", "#cf7920", "#24866c"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


before_manifest = json.loads((BEFORE / "manifest.json").read_text())
after_manifest = json.loads((AFTER / "manifest.json").read_text())
assert before_manifest["status"] == after_manifest["status"] == "Complete"
input_paths = [BEFORE / "outputs/boardman_wells_summary.csv", AFTER / "outputs/boardman_wells_summary.csv",
               AFTER / "outputs/removed_records/boardman_wells_summary.csv", AFTER / "audit/well_group_membership.csv",
               AFTER / "audit/checks.json", AFTER / "manifest.json"]
for path in input_paths[:-1]:
    manifest_root = BEFORE if BEFORE in path.parents else AFTER
    manifest = before_manifest if manifest_root == BEFORE else after_manifest
    entries = manifest["outputs"] + manifest.get("audit_files", [])
    entry = next(item for item in entries if
                 (REPO if item["path_base"] == "repository_root" else manifest_root) / item["path"] == path)
    assert sha(path) == entry["sha256"], path
source_hashes = {path: sha(path) for path in input_paths}
before_rows = {row["well_id"]: row for row in read(input_paths[0])}
after_rows = {row["well_id"]: row for row in read(input_paths[1])}
archived_ids = {row["well_id"] for row in read(input_paths[2])}
members = read(input_paths[3])
checks = json.loads(input_paths[4].read_text())
assert checks["result"] == "pass"
assert len(members) == len({row["original_well_id"] for row in members}) == 166
assert Counter(row["action"] for row in members) == {
    "surviving_representative": 71, "removed_duplicate": 91, "retained_more_than_100m": 4}
assert {row["original_well_id"] for row in members if row["action"] == "removed_duplicate"} == archived_ids
assert len(before_rows) == 7402 and len(after_rows) == 7311
positions = {"before": defaultdict(list), "after": defaultdict(list)}
for member in members:
    well = member["original_well_id"]
    original = before_rows[well]
    point = (float(original["latitude"]), float(original["longitude"]))
    positions["before"][point].append(member)
    if member["action"] == "removed_duplicate":
        assert well not in after_rows
    else:
        assert after_rows[well] == original
        positions["after"][point].append(member)
assert len(positions["before"]) == 84 and len(positions["after"]) == 75
assert sum(map(len, positions["after"].values())) == 75
assert all(len(records) == 1 for records in positions["after"].values())
all_lats, all_lons = zip(*positions["before"])
xspan, yspan = max(all_lons)-min(all_lons), max(all_lats)-min(all_lats)
xlimits = min(all_lons)-.05*xspan, max(all_lons)+.05*xspan
ylimits = min(all_lats)-.05*yspan, max(all_lats)+.05*yspan

plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
fig, axes = plt.subplots(1, 2, figsize=(16, 8.5), facecolor="#fbfaf6")
scale_metadata = []
for ax, stage in zip(axes, ("before", "after")):
    ax.set_facecolor("#f1f4f3")
    ax.set_xlim(*xlimits); ax.set_ylim(*ylimits)
    ax.set_aspect(1 / math.cos(math.radians(sum(ylimits)/2)))
    ax.set_xlabel("Longitude (degrees)"); ax.set_ylabel("Latitude (degrees)")
    ax.grid(alpha=.18)
    for point, records in positions[stage].items():
        lat, lon = point
        far = all(row["action"] == "retained_more_than_100m" for row in records)
        ax.scatter(lon, lat, s=30*len(records), color=GREEN if far else BLUE,
                   edgecolors="white", linewidths=.6, zorder=3)
        if stage == "before" and any(row["action"] == "removed_duplicate" for row in records):
            ax.scatter(lon, lat, s=30*len(records)+70, facecolors="none", edgecolors=ORANGE,
                       linewidths=1.25, zorder=4)
        if stage == "after" and far:
            ax.scatter(lon, lat, s=120, facecolors="none", edgecolors=GREEN, linewidths=1.4, zorder=4)
    count = sum(map(len, positions[stage].values()))
    ax.set_title(f'{stage.capitalize()} deduplication\n{count} well records · {len(positions[stage])} recorded locations',
                 loc="left", fontsize=15, fontweight="bold", pad=14)
    ax.annotate("N ↑", (.94, .94), xycoords="axes fraction", fontsize=13, ha="center")
    scale_lat = ylimits[0]+.06*(ylimits[1]-ylimits[0])
    scale_lon = xlimits[0]+.79*(xlimits[1]-xlimits[0])
    scale_width = math.degrees(2*math.asin(math.sin(5000/(2*6371008.8))/math.cos(math.radians(scale_lat))))
    height = .006*(ylimits[1]-ylimits[0])
    for index, color in enumerate(("#253345", "white")):
        ax.add_patch(Rectangle((scale_lon+index*scale_width/2, scale_lat), scale_width/2, height,
                              facecolor=color, edgecolor="#253345", linewidth=1, zorder=6))
    ax.annotate("5 km (5,000 m)", (scale_lon+scale_width/2, scale_lat), xytext=(0, 10),
                textcoords="offset points", ha="center", fontsize=9, zorder=7)
    ax.set_xlim(*xlimits); ax.set_ylim(*ylimits)
    scale_metadata.append({"panel": stage, "length_m": 5000, "latitude": scale_lat,
                           "start_longitude": scale_lon, "end_longitude": scale_lon+scale_width})
axes[0].legend(handles=[Line2D([], [], marker="o", linestyle="", color=BLUE, label="Original well records"),
                       Line2D([], [], marker="o", linestyle="", markerfacecolor="none", markeredgecolor=ORANGE,
                              color=ORANGE, label="Location includes copies removed"),
                       Line2D([], [], marker="o", linestyle="", color=GREEN, label="Farther records kept")], loc="upper left", fontsize=9)
axes[1].legend(handles=[Line2D([], [], marker="o", linestyle="", color=BLUE, label="71 surviving representatives"),
                       Line2D([], [], marker="o", linestyle="", color=GREEN, label="4 farther records kept")],
               loc="upper left", fontsize=9)
for member in members:
    if member["action"] != "retained_more_than_100m":
        continue
    offsets = {"79": (12, 8), "9297": (-8, 18), "9301": (-8, -28), "14674": (12, -16)}
    offset = offsets[member["gw_site_id"]]
    axes[1].annotate(f'Site {member["gw_site_id"]}',
        (float(member["longitude"]), float(member["latitude"])), xytext=offset,
        textcoords="offset points", fontsize=8, color=GREEN, ha="right" if offset[0]<0 else "left",
        arrowprops={"arrowstyle": "-", "color": GREEN, "linewidth": .7})
fig.suptitle("Boardman · before and after deduplication", x=.07, ha="left", fontsize=23, fontweight="bold")
fig.text(.07, .115, "91 well records removed from the working tables and archived · 427 stratigraphy intervals · 127 lithology intervals", fontsize=12, fontweight="bold")
fig.text(.07, .073, "Only the 71 duplicate groups are mapped; other wells are unchanged. Filled marker area reflects the number of records at a location.\n"
         "Most removed copies share coordinates with a survivor, so markers become smaller. Only 9 recorded locations disappear.", fontsize=10)
fig.text(.07, .025, "Whole dataset: 7,402 → 7,311 well records | 1,854 → 1,427 stratigraphy intervals | 15,586 → 15,459 lithology intervals", fontsize=10, color="#536174")
fig.subplots_adjust(left=.07, right=.96, top=.82, bottom=.22, wspace=.23)
for extension in ("png", "pdf"):
    fig.savefig(HERE / f"before_after_dedupe.{extension}", dpi=180, facecolor=fig.get_facecolor())
plt.close(fig)
with (HERE / "comparison_locations.csv").open("w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["stage", "latitude", "longitude", "well_record_count", "well_ids_json", "removed_well_count"])
    for stage, points in positions.items():
        for point, records in sorted(points.items()):
            writer.writerow([stage, *point, len(records), json.dumps([r["original_well_id"] for r in records]),
                             sum(r["action"] == "removed_duplicate" for r in records)])
for path, original_hash in source_hashes.items():
    assert sha(path) == original_hash
metadata = {"purpose": "Before/after visualization of the 71 duplicate groups; frozen iterations are unchanged.",
    "created_local": datetime.now(ZoneInfo("America/Los_Angeles")).isoformat(timespec="seconds"),
    "scope": {"groups": 71, "before_records": 166, "after_records": 75, "before_locations": 84,
              "after_locations": 75, "removed_records": 91, "representatives": 71, "farther_records": 4},
    "scales": scale_metadata, "marker_encoding": "Filled area proportional to record count; outlines encode removal/retention status.",
    "inputs": [{"path": str(path.relative_to(REPO)), "sha256": value} for path, value in source_hashes.items()],
    "sources": [{"path_base": "repository_root", "path": str(Path(__file__).resolve().relative_to(REPO)), "sha256": sha(Path(__file__))}],
    "outputs": [{"path": name, "sha256": sha(HERE/name)} for name in
                ("before_after_dedupe.png", "before_after_dedupe.pdf", "comparison_locations.csv")],
    "software": {"matplotlib": matplotlib.__version__},
    "checks": {"frozen_input_hashes_match": "pass", "record_actions_match_archive_and_survivors": "pass",
               "surviving_row_values_unchanged": "pass", "group_and_location_counts": "pass", "input_hashes_unchanged_after_plotting": "pass"}}
(HERE / "manifest.json").write_text(json.dumps(metadata, indent=2)+"\n")
print(json.dumps(metadata["scope"], indent=2))
