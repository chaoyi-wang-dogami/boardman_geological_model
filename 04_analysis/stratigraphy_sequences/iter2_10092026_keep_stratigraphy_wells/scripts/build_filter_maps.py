"""Plot the completed stratigraphy filter without changing any well records."""
import argparse
import csv
import hashlib
import json
import math
import platform
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ITERATION = Path(__file__).resolve().parent.parent
BASE = ITERATION.parent
REPO = BASE.parents[1]
PARENT = BASE / "iter1_10082026_dedupe_strat_reports"
CANONICAL = ITERATION / "evidence/plots/well_filter"
BLUE, GREY = "#2463a6", "#88949b"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def position(row):
    lat, lon = float(row["latitude"]), float(row["longitude"])
    if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError(f"Invalid geographic position: {row['well_id']}")
    return lon, lat


def extent(rows, padding=.08):
    xs, ys = zip(*(position(row) for row in rows))
    dx, dy = max(xs)-min(xs), max(ys)-min(ys)
    return min(xs)-padding*dx, max(xs)+padding*dx, min(ys)-padding*dy, max(ys)+padding*dy


def inside(row, bounds):
    x, y = position(row)
    return bounds[0] <= x <= bounds[1] and bounds[2] <= y <= bounds[3]


def distance(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 6371008.8*2*math.asin(math.sqrt(min(1,max(0,h))))


def scale_bar(ax, bounds, length):
    xmin, xmax, ymin, ymax = bounds
    lat = ymin+.075*(ymax-ymin)
    start = xmin+.07*(xmax-xmin)
    width = math.degrees(2*math.asin(math.sin(length/(2*6371008.8))/math.cos(math.radians(lat))))
    assert abs(distance((lat,start),(lat,start+width))-length) < .001
    tick = .012*(ymax-ymin)
    ax.plot([start,start+width],[lat,lat],color="#253345",linewidth=2.3,zorder=8)
    for x in (start,start+width):
        ax.plot([x,x],[lat-tick,lat+tick],color="#253345",linewidth=1.5,zorder=8)
    ax.text(start+width/2,lat+tick*2.2,f"{length//1000} km",ha="center",va="bottom",fontsize=10,
            color="#253345",bbox={"facecolor":"white","edgecolor":"none","alpha":.9},zorder=9)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True, help="A new map-evidence directory or external preview directory")
    args = parser.parse_args()
    out = args.output_dir.resolve()
    if out.is_relative_to(BASE) and out != CANONICAL:
        raise SystemExit("Inside the analysis workflow, only the iteration 2 map-evidence directory is allowed.")
    if out.exists():
        raise SystemExit("Output directory already exists. Refusing to overwrite map evidence.")
    snapshot = ITERATION / "evidence/plots/manifest_before_map_addition.json"
    original_manifest = json.loads(snapshot.read_text())
    assert original_manifest["status"] == "Complete"
    parent_summary = PARENT / "outputs/boardman_wells_summary.csv"
    active_summary = ITERATION / "outputs/boardman_wells_summary.csv"
    archive_summary = ITERATION / "outputs/removed_records/boardman_wells_summary.csv"
    stratigraphy = ITERATION / "outputs/boardman_wells_stratigraphy.csv"
    sources = [snapshot,parent_summary,active_summary,archive_summary,stratigraphy]
    source_hashes = {path:sha(path) for path in sources}
    for path in sources[1:]:
        entry = next(e for e in original_manifest["inputs"]+original_manifest["outputs"] if e["path"] == str(path.relative_to(REPO)))
        assert source_hashes[path] == entry["sha256"], path
    before, after, archived = map(read_csv,(parent_summary,active_summary,archive_summary))
    before_by_id = {r["well_id"]:r for r in before}
    after_by_id = {r["well_id"]:r for r in after}
    excluded_ids = {r["well_id"] for r in archived}
    assert len(before_by_id)==len(before)==7311 and len(after_by_id)==len(after)==332
    assert len(excluded_ids)==len(archived)==6979
    assert set(after_by_id)|excluded_ids==set(before_by_id) and not(set(after_by_id)&excluded_ids)
    assert set(after_by_id)=={r["well_id"] for r in read_csv(stratigraphy)}
    assert all(before_by_id[r["well_id"]]==r for r in after+archived)
    for row in before:
        position(row)
    full, closer = extent(before), extent(after,.12)
    before_closer = sum(inside(row,closer) for row in before)
    excluded_closer = sum(inside(row,closer) for row in archived)
    stats = {"before_well_ids":len(before),"after_well_ids":len(after),"excluded_well_ids":len(archived),
             "before_recorded_locations":len({position(r) for r in before}),
             "after_recorded_locations":len({position(r) for r in after}),
             "missing_or_invalid_coordinates":0,"closer_before_well_ids":before_closer,
             "closer_excluded_well_ids":excluded_closer,"before_outside_closer_view":len(before)-before_closer,
             "after_with_lithology":sum(r["has_lithology"]=="TRUE" for r in after),
             "after_without_lithology":sum(r["has_lithology"]=="FALSE" for r in after)}
    out.mkdir(parents=True)

    plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False})
    fig, axes = plt.subplots(2,2,figsize=(15,13),facecolor="#fbfaf6")
    for row_index,bounds in enumerate((full,closer)):
        for col_index,records in enumerate((before,after)):
            ax = axes[row_index,col_index]
            ax.set_facecolor("#f1f4f3")
            if col_index==0:
                grey = [r for r in archived if inside(r,bounds)]
                ax.scatter([position(r)[0] for r in grey],[position(r)[1] for r in grey],
                           s=5 if row_index==0 else 9,color=GREY,alpha=.48,edgecolors="none",rasterized=True,zorder=2)
            ax.scatter([position(r)[0] for r in after],[position(r)[1] for r in after],
                       s=12 if row_index==0 else 24,color=BLUE,edgecolors="white",linewidths=.35,zorder=4)
            ax.set_xlim(bounds[:2]);ax.set_ylim(bounds[2:])
            ax.set_aspect(1/math.cos(math.radians((bounds[2]+bounds[3])/2)))
            ax.set_xlabel("Longitude (degrees)");ax.set_ylabel("Latitude (degrees)")
            ax.grid(alpha=.2)
            label = "Before · iteration 1" if col_index==0 else "After · iteration 2"
            n = len(records) if row_index==0 else sum(inside(r,bounds) for r in records)
            detail = "Full recorded extent" if row_index==0 else "Closer view of retained area"
            ax.set_title(f"{label} · {n:,} well IDs\n{detail}",loc="left",fontsize=12,pad=12)
            ax.text(.96,.94,"N ↑",transform=ax.transAxes,ha="right",fontsize=12)
            scale_bar(ax,bounds,20000 if row_index==0 else 5000)
    fig.suptitle("Boardman · keep wells with stratigraphy",fontsize=21,x=.07,ha="left",y=.98)
    fig.text(.07,.945,"7,311 → 332 well IDs · 6,979 excluded because stratigraphy is absent · lithology remains optional",fontsize=12,color="#536174")
    fig.legend(handles=[Line2D([],[],marker="o",linestyle="",color=BLUE,label="Retained: stratigraphy present"),
                        Line2D([],[],marker="o",linestyle="",color=GREY,label="Excluded: no stratigraphy")],
               loc="lower center",bbox_to_anchor=(.5,.062),ncol=2,frameon=False)
    fig.text(.07,.025,f"Matching axes within each row. The closer view omits {len(before)-before_closer:,} pre-filter well IDs; all appear in the full-extent panels.\n"
             "Coordinates are recorded values, not independently verified. Well IDs may overlap at the same location. Scale bars use distance at their plotted latitude.",fontsize=10,color="#536174")
    fig.subplots_adjust(left=.07,right=.97,top=.895,bottom=.13,hspace=.32,wspace=.20)
    fig.savefig(out/"before_after_filter.png",dpi=180,facecolor=fig.get_facecolor())
    fig.savefig(out/"before_after_filter.pdf",facecolor=fig.get_facecolor())
    plt.close(fig)

    after_records = {row["well_id"]:ordinal for ordinal,row in enumerate(after,2)}
    wells = []
    for ordinal,row in enumerate(before,2):
        wells.append({**row,"status":"retained" if row["well_id"] in after_by_id else "excluded",
                      "parent_summary_record":ordinal,"after_summary_record":after_records.get(row["well_id"],"")})
    data = {"statistics":stats,"wells":wells,"full_extent":full,"closer_extent":closer}
    write_json(out/"well_locations.json",data)
    with (out/"well_locations.csv").open("x",newline="",encoding="utf-8") as stream:
        fields=list(wells[0])+["source_file","source_sha256"]
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        writer.writerows({**w,"source_file":str(parent_summary.relative_to(REPO)),"source_sha256":source_hashes[parent_summary]} for w in wells)
    write_json(out/"well_locations.geojson",{"type":"FeatureCollection","features":[
        {"type":"Feature","geometry":{"type":"Point","coordinates":list(position(w))},
         "properties":{"well_id":w["well_id"],"status":w["status"],"has_lithology":w["has_lithology"],
                       "has_stratigraphy":w["has_stratigraphy"],"tr_key":w["tr_key"],"gw_site_id":w["gw_site_id"]}} for w in wells]})
    script_dir=Path(__file__).resolve().parent
    template=(script_dir/"filter_map_template.html").read_text()
    page=template.replace("__WELL_DATA__",json.dumps(data,ensure_ascii=False).replace("<","\\u003c")).replace("__MAP_JS__",(script_dir/"filter_map.js").read_text())
    (out/"well_filter_map.html").write_text(page,encoding="utf-8")
    (out/"README.md").write_text(f"""# Iteration 2 well-filter maps

Open the [interactive map](well_filter_map.html), [static PNG](before_after_filter.png), or [PDF](before_after_filter.pdf).

Before means iteration 1's 7,311 well IDs. After means iteration 2's 332 retained well IDs. The 6,979 excluded IDs lack stratigraphy. Lithology is optional: 100 retained IDs have lithology and 232 do not. Counts are well IDs, not distinct locations.

The static comparison includes full-extent panels and closer panels based on retained-well bounds. Each before/after pair uses identical axes. The closer view shows {before_closer:,} pre-filter IDs and omits {len(before)-before_closer:,}; all source IDs appear in the full-extent view. Both rows have distance scales (20 km full extent; 5 km closer view). Grey means excluded and blue means retained. Coincident points may overlap.

The interactive map starts with the retained wells. Switch to **Before**, **Excluded**, or **Before + after overlay**. Filter by lithology and search well ID, site ID, or township. Click a marker or listed well for details. The list shows up to 80 matches; all matching wells are plotted. Recorded coordinate pairs are grouped only for popups, without merging well IDs. **Fit visible wells** includes all matches; **Zoom to retained area** changes the viewport without filtering the data.

The background uses [USGS The National Map](https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer), with a **Wells only** option and clear tile-error messages. Leaflet 1.9.4 loads from a CDN, so an internet connection is needed to initially load the interactive library. If it cannot load, the local static PNG remains available. The data and map JavaScript are embedded in the HTML; no local server is needed.

[well_locations.csv](well_locations.csv) preserves parent summary values, status, and source occurrence identity. [well_locations.geojson](well_locations.geojson) contains one feature per parent well ID. [manifest.json](manifest.json) records the checked input versions, generation methods, output hashes, and plot settings. Source latitude/longitude are displayed as geographic degrees; their geodetic datum has not been independently established. Scale bars use the same mean-Earth-radius distance convention as earlier maps. Distant coordinates have not been removed or corrected.

The generator is `scripts/build_filter_maps.py` inside iteration 2. Reproduce into a **new** external directory, for example from the repository root:

```bash
python3 04_analysis/stratigraphy_sequences/iter2_10092026_keep_stratigraphy_wells/scripts/build_filter_maps.py --output-dir /tmp/boardman_iter2_map_preview
```

The output directory must not already exist. Working CSVs, archives, filter decisions, and the original completion date remain unchanged. The generation-time iteration manifest was saved before adding map evidence, so hash references do not form a cycle.
""",encoding="utf-8")
    assert all(sha(path)==value for path,value in source_hashes.items())
    output_names=("before_after_filter.png","before_after_filter.pdf","well_filter_map.html","well_locations.csv","well_locations.json","well_locations.geojson","README.md")
    metadata={"purpose":"Before-and-after visualization of the completed iteration 2 stratigraphy-availability filter; no data changes.",
              "created_local":datetime.now(ZoneInfo("America/Los_Angeles")).isoformat(timespec="seconds"),
              "inputs":[{"path_base":"repository_root","path":str(path.relative_to(REPO)),"sha256":value} for path,value in source_hashes.items()],
              "sources":[{"path_base":"repository_root","path":str(path.relative_to(REPO)),"sha256":sha(path)} for path in
                         (Path(__file__).resolve(),script_dir/"filter_map.js",script_dir/"filter_map_template.html")],
              "statistics":stats,"full_extent_lon_lat":full,"closer_extent_lon_lat":closer,
              "plot_coordinates":"Recorded longitude/latitude displayed as geographic degrees; source datum unverified.",
              "scale_bars_metres":{"full":20000,"closer":5000},"distance_method":"Spherical distance at the bar latitude; mean Earth radius 6371008.8 m.",
              "basemap":{"provider":"USGS The National Map","service":"USGSTopo","max_native_zoom":16,"alternative":"Wells only"},
              "software":{"python":platform.python_version(),"matplotlib":matplotlib.__version__,"leaflet":"1.9.4, browser CDN"},
              "outputs":[{"path":name,"sha256":sha(out/name),"size_bytes":(out/name).stat().st_size} for name in output_names],
              "checks":{key:"pass" for key in ("frozen_input_hashes","well_id_partitions","retained_and_archived_values_unchanged",
                        "retained_ids_equal_actual_stratigraphy_ids","all_wells_have_valid_geographic_coordinates",
                        "scale_lengths_verified","input_hashes_unchanged_after_plotting")}}
    write_json(out/"manifest.json",metadata)
    print(json.dumps(stats,indent=2))


if __name__=="__main__":
    main()
