"""Create and verify iteration 0 once; refuse to overwrite an existing snapshot."""

import csv
import hashlib
import io
import json
import platform
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def local_time():
    return datetime.now(ZoneInfo("America/Los_Angeles")).isoformat(timespec="seconds")


def inventory(data):
    reader = csv.reader(io.StringIO(data.decode("utf-8-sig"), newline=""))
    headers = next(reader)
    rows = list(reader)
    return headers, rows


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


iteration = Path(__file__).resolve().parent.parent
base = iteration.parent
repo = iteration.parents[2]
source_dir = repo / "03_processed/boardman_19_townships"
filenames = (
    "boardman_wells_summary.csv",
    "boardman_wells_stratigraphy.csv",
    "boardman_wells_lithology.csv",
)
expected_counts = (7402, 1854, 15586)
manifest_path = iteration / "manifest.json"
if manifest_path.exists() or (iteration / "outputs").exists():
    raise SystemExit("Existing snapshot detected; use a new iteration instead of overwriting it.")

started = local_time()
manifest = json.loads((base / "templates/manifest.example.json").read_text())
manifest.pop("template_only")
manifest.update({
    "iteration_number": 0,
    "directory_name": iteration.name,
    "purpose": "Freeze unchanged copies of the three authoritative processed CSVs.",
    "status": "In progress",
    "started_local": started,
    "inputs": [],
    "notes": "Raw means unchanged current processed inputs. No cleaning, interpretation, or coordinate/height conversion. References are preserved as recorded; null coordinate_references mean not evaluated by this snapshot iteration. Completed snapshot files are retained unchanged by workflow convention.",
})
write_json(manifest_path, manifest)
(iteration / "outputs").mkdir()
(iteration / "audit").mkdir()
baseline_path = base / "artifacts/summary.json"
baseline = json.loads(baseline_path.read_text())
checks = []


def check(check_id, expected, actual):
    checks.append({"check_id": check_id, "expected": expected, "actual": actual,
                   "status": "pass" if expected == actual else "fail"})


for index, (filename, expected_count) in enumerate(zip(filenames, expected_counts), 1):
    source = source_dir / filename
    data = source.read_bytes()
    digest = sha256(data)
    headers, rows = inventory(data)
    output = iteration / "outputs" / filename
    with output.open("xb") as stream:
        stream.write(data)
    copied_data = output.read_bytes()
    copied_headers, copied_rows = inventory(copied_data)
    metadata = {"file_id": f"input_{index:03d}", "path_base": "repository_root",
                "path": str(source.relative_to(repo)), "role": "source", "sha256": digest,
                "size_bytes": len(data), "row_count": len(rows), "headers": headers,
                "parent_iteration": None, "encoding": "UTF-8", "delimiter": ","}
    manifest["inputs"].append(metadata)
    manifest["outputs"].append({**metadata, "file_id": f"output_{index:03d}",
                                "path": str(output.relative_to(repo)), "role": "complete_release",
                                "source_file_id": metadata["file_id"]})
    check(f"{filename}:sha256_copy_matches_source", digest, sha256(copied_data))
    check(f"{filename}:bytes_copy_matches_source", True, data == copied_data)
    check(f"{filename}:source_unchanged_after_copy", digest, sha256(source.read_bytes()))
    check(f"{filename}:file_size", len(data), len(copied_data))
    check(f"{filename}:headers", headers, copied_headers)
    check(f"{filename}:row_count_preserved", len(rows), len(copied_rows))
    check(f"{filename}:baseline_row_count", expected_count, len(rows))
    check(f"{filename}:baseline_source_hash", baseline["source_sha256"][filename], digest)
    check(f"{filename}:consistent_csv_field_count", 0,
          sum(len(row) != len(headers) for row in rows))

check("input_file_count", 3, len(manifest["inputs"]))
check("output_file_count", 3, len(manifest["outputs"]))
check("directory_uses_actual_local_start_date",
      "iter0_" + datetime.fromisoformat(started).strftime("%m%d%Y") + "_raw_data_copy", iteration.name)
closed = local_time()
all_passed = all(item["status"] == "pass" for item in checks)
audit_path = iteration / "audit/checks.json"
write_json(audit_path, {"iteration_number": 0, "checked_local": closed,
                       "scope": "Snapshot integrity and baseline inventory only; not geological quality.",
                       "result": "pass" if all_passed else "fail", "checks": checks})
for filename in ("SOP.md", "DATA_FORMAT.md", "templates/ITERATION_README.md", "templates/manifest.example.json"):
    path = base / filename
    manifest["workflow_documents"].append({"path_base": "repository_root",
        "path": str(path.relative_to(repo)), "sha256": sha256(path.read_bytes()),
        "version": "Workflow draft 1, October 8, 2026"})
manifest["software"] = [{"name": "Python", "version": platform.python_version(),
                          "libraries": "Standard library only"}]
manifest["method_files"] = [{"path_base": "iteration_directory", "path": "scripts/create_snapshot.py",
                             "sha256": sha256(Path(__file__).read_bytes())}]
manifest["audit_files"] = [{"path_base": "iteration_directory", "path": "audit/checks.json",
                            "sha256": sha256(audit_path.read_bytes())}]
manifest["baseline_audit"] = {"path_base": "repository_root", "path": str(baseline_path.relative_to(repo)),
                              "sha256": sha256(baseline_path.read_bytes()), "role": "existing_evidence"}
manifest["verification_summary"] = {"result": "pass" if all_passed else "fail",
                                    "passed": sum(item["status"] == "pass" for item in checks),
                                    "total": len(checks)}
manifest["review"] = {"operator": "Codex", "reviewer": None, "reviewed_local": closed,
                      "outcome": "Automated snapshot checks passed; no geological review performed."
                      if all_passed else "Snapshot verification failed; inspect audit/checks.json."}
manifest["status"] = "Awaiting review"
write_json(manifest_path, manifest)
print(json.dumps({"directory": iteration.name, "started_local": started,
                  "checks_passed": manifest["verification_summary"]["passed"],
                  "checks_total": len(checks),
                  "row_counts": {item["path"].split("/")[-1]: item["row_count"] for item in manifest["inputs"]}}, indent=2))
if not all_passed:
    raise SystemExit("Snapshot checks failed; do not close iteration 0.")
