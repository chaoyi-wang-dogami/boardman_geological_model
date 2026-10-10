"""Keep existing representative wells; archive matching copies within 100 m."""
import csv
import hashlib
import itertools
import json
import math
import platform
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ITERATION = Path(__file__).resolve().parent.parent
BASE = ITERATION.parent
REPO = BASE.parents[1]
PARENT = BASE / "iter0_10082026_raw_data_copy"
SCIENTIFIC = ("start_depth", "end_depth", "start_depth_elev", "end_depth_elev", "depth_thickness",
              "strat_unit", "sample_source", "picked_by", "est_age", "est_age_error")
KINDS = ("summary", "stratigraphy", "lithology")


def now():
    return datetime.now(ZoneInfo("America/Los_Angeles")).isoformat(timespec="seconds")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path, rows, fields):
    with path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        rows = [{**row, "_source_record": number} for number, row in enumerate(reader, 2)]
        return reader.fieldnames, rows


def position(row):
    point = float(row["latitude"]), float(row["longitude"])
    assert all(map(math.isfinite, point)) and -90 <= point[0] <= 90 and -180 <= point[1] <= 180
    return point


def distance(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 6371008.8*2*math.asin(math.sqrt(min(1, max(0, h))))


def interval_signature(row):
    return tuple(row[field] for field in SCIENTIFIC)


def sequence_signature(rows):
    return tuple(sorted(interval_signature(row) for row in rows))


if (ITERATION / "manifest.json").exists() or (ITERATION / "outputs").exists():
    raise SystemExit("Existing iteration detected. Refusing to overwrite its files.")
started = now()
assert ITERATION.name == "iter1_" + datetime.fromisoformat(started).strftime("%m%d%Y") + "_dedupe_strat_reports"
for directory in ("inputs", "outputs/removed_records", "audit", "evidence/workflow"):
    (ITERATION / directory).mkdir(parents=True, exist_ok=True)
parent_manifest = json.loads((PARENT / "manifest.json").read_text())
tables, inputs = {}, []
for kind in KINDS:
    name = f"boardman_wells_{kind}.csv"
    path = PARENT / "outputs" / name
    recorded = next(row for row in parent_manifest["outputs"] if row["path"].endswith("/" + name))
    assert sha(path) == recorded["sha256"], name
    fields, rows = read_csv(path)
    tables[kind] = (fields, rows)
    inputs.append({**recorded, "file_id": f"input_{kind}", "role": "source", "parent_iteration": PARENT.name})
manifest = json.loads((BASE / "templates/manifest.example.json").read_text())
manifest.pop("template_only")
manifest.update({"iteration_number": 1, "directory_name": ITERATION.name, "status": "In progress",
    "purpose": "Remove identical nearby stratigraphy copies while keeping existing representative well IDs and all original removed records.",
    "started_local": started, "parent_iterations": [PARENT.name], "inputs": inputs,
    "notes": "No new well IDs. Group by site and identical complete scientific intervals. Choose the most frequent recorded coordinate pair; if frequencies tie, use the location of the alphabetically first well_id among those locations. Keep the alphabetically first well_id at the chosen location. Remove only other matching records within 100 m of that surviving well. Archive removed lithology without attaching it to survivors. Source depths, elevations, labels, IDs, and dates are not repaired or reinterpreted."})
write_json(ITERATION / "manifest.json", manifest)
input_index_fields = ("file_id", "path_base", "path", "role", "sha256", "size_bytes", "row_count", "parent_iteration")
write_csv(ITERATION / "inputs/input_files.csv", inputs, input_index_fields)
well_rows = tables["summary"][1]
wells = {row["well_id"]: row for row in well_rows}
assert len(wells) == len(well_rows) and "" not in wells
reports = defaultdict(lambda: defaultdict(list))
for row in tables["stratigraphy"][1]:
    assert row["well_id"] in wells
    reports[row["gw_site_id"]][row["well_id"]].append(row)
groups, membership, removed_links, representative_metadata = [], [], [], []
removed_to_representative = {}
for site, by_well in sorted(reports.items(), key=lambda pair: int(pair[0])):
    if len(by_well) < 2:
        continue
    # An entire sequence must match, preserving repeated interval occurrences.
    variants = defaultdict(list)
    for well, rows in by_well.items():
        variants[sequence_signature(rows)].append(well)
    assert len(variants) == 1, f"Conflicting interpretation at site {site}; stop for review."
    locations = defaultdict(list)
    for well in sorted(by_well):
        locations[position(wells[well])].append(well)
    largest_count = max(map(len, locations.values()))
    most_common_locations = [point for point, ids in locations.items() if len(ids) == largest_count]
    representative = min(well for point in most_common_locations for well in locations[point])
    reference = position(wells[representative])
    removed, outside = [], []
    distances = {}
    for well in sorted(by_well):
        metres = distance(reference, position(wells[well]))
        distances[well] = metres
        if well == representative:
            action = "surviving_representative"
        elif metres <= 100:
            action = "removed_duplicate"
            removed.append(well)
            removed_to_representative[well] = representative
        else:
            action = "retained_more_than_100m"
            outside.append(well)
        original = wells[well]
        membership.append({"gw_site_id": site, "representative_well_id": representative,
            "original_well_id": well, "action": action, "distance_to_representative_m": f"{metres:.6f}",
            "latitude": original["latitude"], "longitude": original["longitude"],
            "summary_source_record": original["_source_record"], "summary_source_sha256": inputs[0]["sha256"]})
        if action == "removed_duplicate":
            removed_links.append({"representative_well_id": representative, "removed_well_id": well,
                "gw_site_id": site, "distance_to_representative_m": f"{metres:.6f}",
                **{f"removed_{key}": original[key] for key in tables["summary"][0] if key != "well_id"},
                "summary_source_record": original["_source_record"], "summary_source_sha256": inputs[0]["sha256"]})
    group_id = "SITE_" + site
    groups.append({"group_id": group_id, "gw_site_id": site, "representative_well_id": representative,
        "reference_latitude": wells[representative]["latitude"], "reference_longitude": wells[representative]["longitude"],
        "original_well_count": len(by_well), "recorded_location_count": len(locations),
        "no_most_common_location": len(most_common_locations) > 1,
        "removed_well_count": len(removed), "removed_well_ids_json": json.dumps(removed),
        "retained_distant_well_ids_json": json.dumps(outside),
        "location_selection": "alphabetically_first_well_id_for_equally_common_locations" if len(most_common_locations) > 1 else "most_common_recorded_location",
        "scientific_signature_sha256": hashlib.sha256(json.dumps(sequence_signature(by_well[representative])).encode()).hexdigest()})
    representative_metadata.append({"well_id": representative, "gw_site_id": site, "group_id": group_id,
        "deduped_well_count": len(removed), "deduped_well_ids_json": json.dumps(removed),
        "retained_distant_well_ids_json": json.dumps(outside),
        "original_metadata_archive": "removed_records/boardman_wells_summary.csv",
        "removed_record_details": "../audit/deduped_well_links.csv"})
removed_ids = set(removed_to_representative)
assert len(groups) == 71 and len(membership) == 166 and len(removed_ids) == 91
assert sum(g["no_most_common_location"] for g in groups) == 9
assert sum(row["action"] == "retained_more_than_100m" for row in membership) == 4
source_links, output_files, counts = [], [], {}
retained_tables, removed_tables = {}, {}
for kind in KINDS:
    fields, rows = tables[kind]
    retained = [row for row in rows if row["well_id"] not in removed_ids]
    archived = [row for row in rows if row["well_id"] in removed_ids]
    retained_tables[kind], removed_tables[kind] = retained, archived
    counts[kind] = {"input": len(rows), "retained": len(retained), "archived": len(archived)}
    for relative, subset, role in ((f"outputs/boardman_wells_{kind}.csv", retained, "complete_release"),
                                  (f"outputs/removed_records/boardman_wells_{kind}.csv", archived, "archive")):
        path = ITERATION / relative
        write_csv(path, subset, fields)
        output_files.append({"file_id": f"{role}_{kind}", "path_base": "repository_root", "path": str(path.relative_to(REPO)),
            "role": role, "sha256": sha(path), "size_bytes": path.stat().st_size, "row_count": len(subset), "headers": fields})
        for output_record, original in enumerate(subset, 2):
            source_links.append({"output_file": relative, "output_record": output_record,
                "output_well_id": original["well_id"], "original_well_id": original["well_id"],
                "representative_well_id": removed_to_representative.get(original["well_id"], original["well_id"]),
                "source_file": inputs[KINDS.index(kind)]["path"], "source_sha256": inputs[KINDS.index(kind)]["sha256"],
                "source_record": original["_source_record"], "role": role})
        # Read the actual files back, checking original columns and all values.
        actual_fields, actual_rows = read_csv(path)
        assert actual_fields == fields
        assert [tuple(row[field] for field in fields) for row in actual_rows] == [tuple(row[field] for field in fields) for row in subset]
    original_counter = Counter(tuple(row[field] for field in fields) for row in rows)
    assert original_counter == Counter(tuple(row[field] for field in fields) for row in retained + archived)
active_well_ids = {row["well_id"] for row in retained_tables["summary"]}
assert len(active_well_ids) == len(retained_tables["summary"]) and not active_well_ids & removed_ids
assert active_well_ids | removed_ids == set(wells)
for kind in ("stratigraphy", "lithology"):
    assert {row["well_id"] for row in retained_tables[kind]} <= active_well_ids
    assert {row["well_id"] for row in removed_tables[kind]} <= removed_ids
active_strat_counts = Counter(row["well_id"] for row in retained_tables["stratigraphy"])
active_lith_counts = Counter(row["well_id"] for row in retained_tables["lithology"])
for row in retained_tables["summary"]:
    well = row["well_id"]
    assert int(row["strat_count"]) == active_strat_counts[well]
    assert int(row["lithology_count"]) == active_lith_counts[well]
    assert row["has_stratigraphy"] == ("TRUE" if active_strat_counts[well] else "FALSE")
    assert row["has_lithology"] == ("TRUE" if active_lith_counts[well] else "FALSE")
for group in groups:
    rep = group["representative_well_id"]
    assert rep in active_well_ids
    for well in json.loads(group["removed_well_ids_json"]):
        assert distance(position(wells[rep]), position(wells[well])) <= 100
        assert sequence_signature(reports[group["gw_site_id"]][rep]) == sequence_signature(reports[group["gw_site_id"]][well])
    for well in json.loads(group["retained_distant_well_ids_json"]):
        assert well in active_well_ids and distance(position(wells[rep]), position(wells[well])) > 100
# Match each archived stratigraphy occurrence to its surviving occurrence;
# occurrence counters ensure repeated identical intervals would not be collapsed.
duplicate_interval_links = []
strat_output_records = {row["_source_record"]: ordinal for ordinal, row in enumerate(retained_tables["stratigraphy"], 2)}
for removed, rep in sorted(removed_to_representative.items()):
    site = wells[removed]["gw_site_id"]
    rep_by_signature = defaultdict(list)
    for row in reports[site][rep]:
        rep_by_signature[interval_signature(row)].append(row)
    occurrences = Counter()
    for row in reports[site][removed]:
        key = interval_signature(row)
        survivor = rep_by_signature[key][occurrences[key]]
        occurrences[key] += 1
        duplicate_interval_links.append({"representative_well_id": rep, "removed_well_id": removed, "gw_site_id": site,
            "surviving_output_record": strat_output_records[survivor["_source_record"]],
            "representative_source_record": survivor["_source_record"], "removed_source_record": row["_source_record"],
            "source_sha256": inputs[1]["sha256"], "interval_occurrence_number": occurrences[key]})
assert len(duplicate_interval_links) == counts["stratigraphy"]["archived"]
for name, rows in (("groups.csv", groups), ("well_group_membership.csv", membership),
                   ("deduped_well_links.csv", removed_links), ("source_row_links.csv", source_links),
                   ("stratigraphy_duplicate_links.csv", duplicate_interval_links)):
    write_csv(ITERATION / "audit" / name, rows, list(rows[0]))
path = ITERATION / "outputs/representative_well_metadata.csv"
write_csv(path, representative_metadata, list(representative_metadata[0]))
output_files.append({"file_id": "representative_metadata", "path_base": "repository_root", "path": str(path.relative_to(REPO)),
    "role": "metadata", "sha256": sha(path), "size_bytes": path.stat().st_size, "row_count": len(representative_metadata), "headers": list(representative_metadata[0])})
decisions = [
    {"decision_id": "ITER1_WITHIN_GROUP", "decision": "Only compare copies within the same site and identical complete scientific interval collection.", "decided_by": "User", "status": "accepted"},
    {"decision_id": "ITER1_100_METRES", "decision": "Remove matching copies within 100 m of the selected representative; retain records more than 100 m away. No chaining through intermediate wells.", "decided_by": "User", "status": "accepted"},
    {"decision_id": "ITER1_LOCATION_CHOICE", "decision": "Use the most common recorded coordinate pair. When there is no single most common pair, use the location of the alphabetically first well_id among the equally common pairs.", "decided_by": "User", "status": "accepted"},
    {"decision_id": "ITER1_EXISTING_REPRESENTATIVE", "decision": "Latest instruction selects a surviving existing representative well. This supersedes the earlier proposal to create new well IDs. Select the alphabetically first well at the chosen location and preserve its row values.", "decided_by": "User; existing representative implemented from latest instruction", "status": "accepted"},
    {"decision_id": "ITER1_REMOVED_LITHOLOGY", "decision": "Archive removed wells' lithology under original IDs without transferring it to the representative. An existing surviving well retains its own original lithology.", "decided_by": "User", "status": "accepted"},
]
write_json(ITERATION / "audit/decisions.json", decisions)
checks = {"result": "pass", "counts": counts, "duplicate_groups": len(groups), "group_records": len(membership),
    "representatives": len(representative_metadata), "removed_wells": len(removed_ids),
    "groups_without_one_most_common_location": sum(g["no_most_common_location"] for g in groups),
    "distant_records_retained": [row["original_well_id"] for row in membership if row["action"] == "retained_more_than_100m"],
    "surviving_wells_with_stratigraphy": len({row["well_id"] for row in retained_tables["stratigraphy"]}),
    "checks": {name: "pass" for name in (
        "input_hashes", "complete_sequence_matching_with_occurrence_counts", "original_headers_preserved",
        "retained_and_archived_rows_read_back_unchanged", "all_original_rows_accounted_for", "primary_keys_unique",
        "active_and_archived_wells_partition_inputs", "active_foreign_keys", "archive_foreign_keys", "summary_counts_and_flags",
        "every_removal_within_100m", "distant_records_retained", "representatives_preserved",
        "every_removed_interval_linked_to_surviving_occurrence", "source_hashes_unchanged")}}
for item in inputs:
    assert sha(REPO / item["path"]) == item["sha256"]
write_json(ITERATION / "audit/checks.json", checks)
for name in ("SOP.md", "ACTION_PLAN.md", "DATA_FORMAT.md"):
    source = BASE / name
    frozen = ITERATION / "evidence/workflow" / name
    frozen.write_bytes(source.read_bytes())
    manifest["workflow_documents"].append({"path_base": "iteration_directory", "path": str(frozen.relative_to(ITERATION)), "sha256": sha(frozen)})
manifest.update({"status": "Awaiting review", "outputs": output_files,
    "software": [{"name": "Python", "version": platform.python_version(), "libraries": "Standard library"}],
    "method_files": [{"path_base": "iteration_directory", "path": "scripts/dedupe.py", "sha256": sha(Path(__file__))}],
    "audit_files": [{"path_base": "iteration_directory", "path": str(p.relative_to(ITERATION)), "sha256": sha(p)} for p in sorted((ITERATION / "audit").iterdir())],
    "decision_ids": [d["decision_id"] for d in decisions], "verification_summary": checks,
    "distance_method": "Haversine; mean Earth radius 6371008.8 m. Inclusive 100 m cutoff from representative coordinates."})
write_json(ITERATION / "manifest.json", manifest)
print(json.dumps(checks, indent=2))
