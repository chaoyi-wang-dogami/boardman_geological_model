"""Keep wells with stratigraphy; preserve excluded rows and their source identities."""
import csv
import hashlib
import json
import platform
import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ITERATION = Path(__file__).resolve().parent.parent
BASE = ITERATION.parent
REPO = BASE.parents[1]
PARENT = BASE / "iter1_10082026_dedupe_strat_reports"
KINDS = ("summary", "stratigraphy", "lithology")
DECISION = "ITER2_KEEP_STRATIGRAPHY"


def now():
    return datetime.now(ZoneInfo("America/Los_Angeles")).isoformat(timespec="seconds")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames, list(reader)


def write_csv(path, fields, rows):
    with path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def inventory(path, role, file_id=None, table=False):
    entry = {"file_id": file_id or path.stem, "path_base": "repository_root",
             "path": str(path.relative_to(REPO)), "role": role,
             "sha256": sha(path), "size_bytes": path.stat().st_size}
    if table:
        fields, rows = read_csv(path)
        entry.update(row_count=len(rows), headers=fields, encoding="UTF-8", delimiter=",")
    return entry


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    if (ITERATION / "manifest.json").exists() or (ITERATION / "outputs").exists():
        raise SystemExit("Existing iteration detected. Refusing to overwrite its files.")
    started = now()
    parent_manifest = json.loads((PARENT / "manifest.json").read_text())
    require(parent_manifest["status"] == "Complete", "Parent iteration is not complete.")
    inputs, tables = [], {}
    for kind in KINDS:
        path = PARENT / "outputs" / f"boardman_wells_{kind}.csv"
        recorded = next(e for e in parent_manifest["outputs"] if e["path"] == str(path.relative_to(REPO)))
        require(sha(path) == recorded["sha256"], f"Parent input hash mismatch: {kind}")
        tables[kind] = read_csv(path)
        inputs.append({**inventory(path, "source", f"input_{kind}", True), "parent_iteration": PARENT.name})
    for relative in ("audit/source_row_links.csv", "outputs/representative_well_metadata.csv",
                     "audit/deduped_well_links.csv", "audit/stratigraphy_duplicate_links.csv"):
        path = PARENT / relative
        recorded = next(e for e in parent_manifest["outputs"] + parent_manifest["audit_files"]
                        if e["path"] in (relative, str(path.relative_to(REPO))))
        require(sha(path) == recorded["sha256"], f"Parent provenance hash mismatch: {relative}")
        inputs.append({**inventory(path, "provenance", "parent_" + path.stem, True), "parent_iteration": PARENT.name})
    inputs.append({**inventory(PARENT / "manifest.json", "provenance", "parent_manifest"), "parent_iteration": PARENT.name})

    summary = tables["summary"][1]
    wells = {row["well_id"]: row for row in summary}
    require(len(wells) == len(summary) and "" not in wells, "Summary well IDs must be nonblank and unique.")
    strat_counts = Counter(row["well_id"] for row in tables["stratigraphy"][1])
    lith_counts = Counter(row["well_id"] for row in tables["lithology"][1])
    require(set(strat_counts) | set(lith_counts) <= set(wells), "Interval well IDs must resolve to the summary.")
    for well, row in wells.items():
        require(row["has_stratigraphy"] == ("TRUE" if strat_counts[well] else "FALSE"), f"Stratigraphy flag disagrees: {well}")
        require(row["has_lithology"] == ("TRUE" if lith_counts[well] else "FALSE"), f"Lithology flag disagrees: {well}")
        require(int(row["strat_count"]) == strat_counts[well] and int(row["lithology_count"]) == lith_counts[well], f"Interval counts disagree: {well}")
    kept = set(strat_counts)
    excluded = set(wells) - kept
    require(len(kept) == 332 and len(excluded) == 6979, "Input counts differ from the reviewed iteration 1 dataset.")
    parent_links = read_csv(PARENT / "audit/source_row_links.csv")[1]
    lookup = {(row["output_file"], int(row["output_record"])): row for row in parent_links}
    require(len(lookup) == len(parent_links), "Parent source occurrence links are not unique.")

    for folder in ("inputs", "outputs/removed_records", "audit", "evidence/workflow"):
        (ITERATION / folder).mkdir(parents=True, exist_ok=True)
    shutil.copyfile(PARENT / "manifest.json", ITERATION / "inputs/parent_manifest_snapshot.json")
    manifest = json.loads((BASE / "templates/manifest.example.json").read_text())
    manifest.pop("template_only")
    manifest.update(iteration_number=2, directory_name=ITERATION.name,
                    purpose="Keep wells with stratigraphy, with associated lithology where present; archive all excluded original rows.",
                    status="In progress", started_local=started, parent_iterations=[PARENT.name], inputs=inputs,
                    coordinate_references=parent_manifest["coordinate_references"],
                    notes="Selection uses actual stratigraphy rows by well_id, checked against summary flags. Lithology is optional. Original columns, values, and occurrence order are preserved. No geological reliability judgment or boundary correction is applied.")
    write_json(ITERATION / "manifest.json", manifest)
    write_csv(ITERATION / "inputs/input_files.csv",
              ("file_id", "path_base", "path", "role", "sha256", "size_bytes", "row_count", "parent_iteration"),
              [{key: e.get(key, "") for key in ("file_id", "path_base", "path", "role", "sha256", "size_bytes", "row_count", "parent_iteration")} for e in inputs])

    counts, outputs, links = {}, [], []
    for kind in KINDS:
        fields, rows = tables[kind]
        name = f"boardman_wells_{kind}.csv"
        selected = [row for row in rows if row["well_id"] in kept]
        archived = [row for row in rows if row["well_id"] in excluded]
        target = ITERATION / "outputs" / name
        archive = ITERATION / "outputs/removed_records" / name
        if kind == "stratigraphy":
            shutil.copyfile(PARENT / "outputs" / name, target)
        else:
            write_csv(target, fields, selected)
        write_csv(archive, fields, archived)
        counts[kind] = {"input": len(rows), "working": len(selected), "archived": len(archived)}
        for path, expected in ((target, selected), (archive, archived)):
            actual_fields, actual_rows = read_csv(path)
            require(actual_fields == fields and actual_rows == expected, f"Read-back values/order mismatch: {path}")
            role = "complete_release" if path == target else "archive"
            outputs.append(inventory(path, role, f"{role}_{kind}", table=True))
        ordinals = {"complete_release": 1, "archive": 1}
        for ordinal, row in enumerate(rows, 2):
            role = "complete_release" if row["well_id"] in kept else "archive"
            ordinals[role] += 1
            path = target if role == "complete_release" else archive
            prior = lookup[(f"outputs/{name}", ordinal)]
            require(prior["output_well_id"] == row["well_id"] and prior["role"] == "complete_release", "Parent source row link disagrees.")
            links.append({"output_file": str(path.relative_to(ITERATION)), "output_record": ordinals[role],
                          "well_id": row["well_id"], "role": role, "decision_id": DECISION,
                          "source_file": inputs[KINDS.index(kind)]["path"],
                          "source_sha256": inputs[KINDS.index(kind)]["sha256"], "source_record": ordinal,
                          "baseline_source_file": prior["source_file"], "baseline_source_sha256": prior["source_sha256"],
                          "baseline_source_record": prior["source_record"]})
        require(len(selected) + len(archived) == len(rows), f"Missing input occurrence: {kind}")
    write_csv(ITERATION / "audit/source_row_links.csv", list(links[0]), links)
    excluded_rows = [{"well_id": row["well_id"], "reason": "no_stratigraphy", "has_lithology": row["has_lithology"],
                      "lithology_rows_archived": lith_counts[row["well_id"]], "stratigraphy_rows_archived": 0,
                      "summary_source_file": inputs[0]["path"], "summary_source_sha256": inputs[0]["sha256"],
                      "summary_source_record": ordinal, "decision_id": DECISION}
                     for ordinal, row in enumerate(summary, 2) if row["well_id"] in excluded]
    write_csv(ITERATION / "audit/excluded_wells.csv", list(excluded_rows[0]), excluded_rows)
    write_json(ITERATION / "audit/decisions.json", [{"decision_id": DECISION, "date": "2026-10-09", "status": "accepted",
               "decided_by": "User", "decision": "Keep wells with at least one stratigraphy row; lithology is optional. Archive wells without stratigraphy and all associated records. Preserve original values and well IDs.",
               "supersedes": "Earlier proposal to require both lithology and stratigraphy; that proposal was not executed.",
               "authorization": "User approved the revised plan and instructed: Sure, start iteration 2."}])

    # Verify every output occurrence against both the parent and the frozen baseline.
    cache = {}
    for link in links:
        for prefix in ("", "baseline_"):
            path = REPO / link[prefix + "source_file"]
            if str(path) not in cache:
                cache[str(path)] = (sha(path), read_csv(path)[1])
            digest, rows = cache[str(path)]
            require(digest == link[prefix + "source_sha256"], f"Source hash changed: {path}")
            source = rows[int(link[prefix + "source_record"]) - 2]
            destination = ITERATION / link["output_file"]
            if str(destination) not in cache:
                cache[str(destination)] = (sha(destination), read_csv(destination)[1])
            actual = cache[str(destination)][1][int(link["output_record"]) - 2]
            require(actual == source, "Output source occurrence changed.")
    require(len(links) == sum(len(tables[k][1]) for k in KINDS), "Not every input occurrence has a link.")
    require(len({(e["source_file"], e["source_record"]) for e in links}) == len(links), "An input occurrence appears more than once.")
    require(len({(e["output_file"], e["output_record"]) for e in links}) == len(links), "An output occurrence appears more than once.")
    require(all(sha(REPO / e["path"]) == e["sha256"] for e in inputs), "Parent inputs changed during execution.")
    require(sha(ITERATION / "outputs/boardman_wells_stratigraphy.csv") == inputs[1]["sha256"], "Stratigraphy bytes changed.")
    representatives = read_csv(PARENT / "outputs/representative_well_metadata.csv")[1]
    require(all(row["well_id"] in kept for row in representatives), "A parent representative was excluded.")
    require(all(row["representative_well_id"] in kept for row in read_csv(PARENT / "audit/deduped_well_links.csv")[1]), "Parent duplicate survivor no longer present.")

    townships = sorted({row["tr_key"] for row in summary})
    active_townships = sorted({row["tr_key"] for row in summary if row["well_id"] in kept})
    checks = {"result": "pass", "counts": counts, "working_wells": len(kept), "excluded_wells": len(excluded),
              "working_wells_with_lithology": len(kept & set(lith_counts)), "working_wells_without_lithology": len(kept - set(lith_counts)),
              "excluded_wells_with_lithology": len(excluded & set(lith_counts)), "excluded_wells_without_lithology": len(excluded - set(lith_counts)),
              "input_townships": townships, "working_townships": active_townships,
              "townships_without_retained_stratigraphy": sorted(set(townships) - set(active_townships)),
              "source_row_links": len(links), "checks": {name: "pass" for name in (
                  "parent_complete_and_input_hashes", "summary_well_ids_unique_nonblank", "input_interval_foreign_keys",
                  "summary_flags_and_counts_match_actual_intervals", "selection_matches_actual_stratigraphy_ids",
                  "working_and_archive_well_ids_partition_input", "all_headers_values_and_row_order_preserved",
                  "working_and_archive_intervals_follow_well_selection", "every_input_occurrence_preserved_once",
                  "every_output_occurrence_linked_once", "parent_and_baseline_source_hashes_verified",
                  "every_output_occurrence_matches_parent_and_baseline", "stratigraphy_byte_identical",
                  "exclusion_reasons_recorded", "deduplication_representatives_and_links_retained", "parent_inputs_unchanged")}}
    write_json(ITERATION / "audit/checks.json", checks)
    for name in ("SOP.md", "ACTION_PLAN.md", "DATA_FORMAT.md"):
        path = ITERATION / "evidence/workflow" / name
        shutil.copyfile(BASE / name, path)
        manifest["workflow_documents"].append({"path_base": "iteration_directory", "path": str(path.relative_to(ITERATION)), "sha256": sha(path)})
    manifest.update(status="Awaiting review", outputs=outputs,
                    software=[{"name": "Python", "version": platform.python_version(), "libraries": "Standard library"}],
                    method_files=[{"path_base": "iteration_directory", "path": "scripts/filter_wells.py", "sha256": sha(Path(__file__))}],
                    audit_files=[{"path_base": "iteration_directory", "path": str(p.relative_to(ITERATION)), "sha256": sha(p)} for p in sorted((ITERATION / "audit").iterdir())],
                    input_evidence=[{"path_base": "iteration_directory", "path": "inputs/parent_manifest_snapshot.json", "sha256": sha(ITERATION / "inputs/parent_manifest_snapshot.json")},
                                    {"path_base": "iteration_directory", "path": "inputs/input_files.csv", "sha256": sha(ITERATION / "inputs/input_files.csv")}],
                    decision_ids=[DECISION], verification_summary=checks)
    write_json(ITERATION / "manifest.json", manifest)
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()
