# Boardman iterative geological workflow

This directory records the preparation, cross-section interpretation, and 3D modeling of the Boardman 19-township well data. [Iteration 4](iter4_10092026_build_postgres_well_database/README.md) is the current working release: PostgreSQL/PostGIS and an interactive HTML map. Its 332 working well IDs, 1,427 stratigraphy intervals, and 1,215 lithology intervals retain iteration 2's values unchanged. The database also contains originals, archives, source links, and iteration 3's audit evidence. Geological interpretation and other preparation tasks remain ahead.

[Iteration 0](iter0_10082026_raw_data_copy/README.md) preserves the starting CSVs; [iteration 1](iter1_10082026_dedupe_strat_reports/README.md) records deduplication; [iteration 2](iter2_10092026_keep_stratigraphy_wells/README.md) records the stratigraphy availability filter. These frozen CSVs remain historical inputs.

Workflow draft 1 was prepared on October 8, 2026. The user's scope decisions in the action plan govern the work; iteration numbering, file details, section counts, and software choices remain adjustable.

## Start here

| Document | Purpose |
|---|---|
| [Action plan](ACTION_PLAN.md) | User decisions, immediate tasks, and questions to settle before changing data |
| [Standard operating procedure](SOP.md) | How to open, perform, review, and close each iteration |
| [Roadmap](ROADMAP.md) | Milestones from current data to a reviewed 3D model |
| [Data format](DATA_FORMAT.md) | Well keys, current CSV format, metadata, and duplicate-report handling |
| [Iteration index](ITERATIONS.md) | Planned, active, and completed data iterations |
| [Existing findings](FINDINGS.md) | Exploratory audit of the current authoritative processed inputs |

The earlier findings and `artifacts/` remain in place as the baseline audit. Some earlier recommendations, including early suitability classification and name standardization, are deferred by the user's later decisions in [ACTION_PLAN.md](ACTION_PLAN.md).

The [duplicate-group map](maps/duplicate_groups/README.md) shows the original iteration 0 groups and locations before deduplication. It includes an interactive map and static overview; use iteration 4 for the current working records. Its retained wells cover 18 townships because T5N R25E has no stratigraphy records; the original regional target remains 19 townships.

[Iteration 2's filter maps](iter2_10092026_keep_stratigraphy_wells/evidence/plots/well_filter/README.md) compare iteration 1's 7,311 well IDs with the 332 retained IDs. Static PNG/PDF and an interactive map are stored inside iteration 2.

[Iteration 3](iter3_10092026_audit_heights_and_depths/README.md) contains the completed read-only depth/elevation audit and colored completeness maps. It remains open for decisions about corrections. Iteration 4 imports that evidence without correcting or removing affected wells.

Open the [database map](iter4_10092026_build_postgres_well_database/evidence/maps/well_database_map.html) directly in a browser. Well information is embedded, so inspection works without a database connection. See [shared database instructions](database/versions/v001/README.md) to start the local server, regenerate a map, or restore the frozen backup. ArcGIS export is deferred.

## File layout

Numbered iteration directories sit directly inside this directory. Their names describe work actually done; the date is the local work date in `MMDDYYYY` format. Numbers increase across the whole workflow rather than restarting for sections or modeling.

```text
stratigraphy_sequences/
├── README.md
├── ACTION_PLAN.md
├── SOP.md
├── ROADMAP.md
├── DATA_FORMAT.md
├── ITERATIONS.md
├── FINDINGS.md
├── artifacts/                         # Existing exploratory audit
├── templates/
│   ├── ITERATION_README.md
│   └── manifest.example.json
│
├── iter0_10082026_raw_data_copy/       # Completed unchanged snapshot
├── iter1_10082026_dedupe_strat_reports/ # Completed removal and archives
├── database/                         # Shared versioned tools and private runtime settings
├── iter2_10092026_keep_stratigraphy_wells/ # Frozen stratigraphy-bearing CSV subset
├── iter3_10092026_audit_heights_and_depths/ # Audit complete; action decisions pending
├── iter4_10092026_build_postgres_well_database/ # Current database release and map
└── iterN_<MMDDYYYY>_<concise_action>/
    ├── README.md
    ├── manifest.json
    ├── inputs/
    ├── outputs/
    ├── audit/
    ├── evidence/
    └── scripts/
```

Iterations 0, 1, 2, and 4 are complete. Iteration 3's audit phase is complete and actions remain pending. The `iterN` directory above is a future example. Database tools live once under `database/versions/`; each iteration records the tool version and retains its own backup, map, checks, and manifest.

| Iteration location | Contents |
|---|---|
| `README.md` | Purpose, input version, method, results, checks, decisions, and remaining questions |
| `manifest.json` | Machine-readable iteration identity, dates, status, dependencies, and input/output hashes |
| `inputs/` | New submissions and/or `input_files.csv` pointing to prior frozen files |
| `outputs/` | Complete working tables or clearly identified additions, section geometry, interpretation tables, and software projects |
| `audit/` | Row links, changes, decisions, checks, and unresolved issues |
| `evidence/` | Source documents, figures, section drawings, and review evidence |
| `scripts/` | Scripts, settings, and a manual procedure when work is performed in a desktop application |

All new workflow documentation and iteration records belong here. Existing evidence elsewhere in the repository can be referenced by path and hash without moving or rewriting it.

## Current source and identity rules

The authoritative inputs remain under `03_processed/boardman_19_townships/`: `boardman_wells_summary.csv`, `boardman_wells_stratigraphy.csv`, and `boardman_wells_lithology.csv`. Working copies and changes belong in numbered iterations. Do not overwrite those authoritative inputs.

Use `well_id` as the unique primary key of the working well table. Keep `wl_id` and `gw_site_id` as reference metadata. The current source's `well_id` identifies a well-report record; this workflow does not silently redefine it as a physical borehole or merge different IDs. Keep layer labels unchanged during the current cleaning scope.

CSV files are currently ignored by the repository's Git configuration. Git history alone therefore does not preserve iteration data. Frozen output files, their manifests, and the project's chosen file storage must remain available. This setup does not change Git ignore rules or upload data.
