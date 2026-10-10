# Iteration 2: keep wells with stratigraphy

Status: **Complete**. Closed October 9, 2026. Started October 9, 2026, America/Los_Angeles. The exact start and closure times are recorded in [manifest.json](manifest.json). Operator: Codex, applying the user-approved filter.

This iteration uses [iteration 1](../iter1_10082026_dedupe_strat_reports/README.md) and retains every well ID with at least one stratigraphy row. Lithology is optional. It supersedes the earlier proposal to require both datasets; that proposal was not executed.

## Results

| Table | Input rows | Working rows | Archived rows |
|---|---:|---:|---:|
| Well summary | 7,311 | **332** | 6,979 |
| Stratigraphy | 1,427 | **1,427** | 0 |
| Lithology | 15,459 | **1,215** | 14,244 |

The 332 working well IDs comprise 100 with both datasets and 232 with stratigraphy only. The excluded well IDs comprise 2,946 with lithology only and 4,033 with neither dataset. Every excluded well has the reason `no_stratigraphy`; geological reliability was not assessed.

The working stratigraphy CSV is byte-for-byte identical to iteration 1's file. Existing columns, values, row order, repeated interval occurrences, and well IDs remain unchanged in the retained and archived records.

## Working files and archives

Use these three complete working tables as the input to future iterations:

- [boardman_wells_summary.csv](outputs/boardman_wells_summary.csv)
- [boardman_wells_stratigraphy.csv](outputs/boardman_wells_stratigraphy.csv)
- [boardman_wells_lithology.csv](outputs/boardman_wells_lithology.csv)

The [exclusion archive](outputs/removed_records/) contains the three corresponding CSVs under original well IDs. Its stratigraphy file has headers only because every stratigraphy row was retained. [excluded_wells.csv](audit/excluded_wells.csv) records each excluded well's reason, lithology availability/count, and parent summary occurrence.

```text
iter2_10092026_keep_stratigraphy_wells/
├── README.md
├── manifest.json
├── inputs/
│   ├── input_files.csv
│   └── parent_manifest_snapshot.json
├── outputs/
│   ├── boardman_wells_summary.csv
│   ├── boardman_wells_stratigraphy.csv
│   ├── boardman_wells_lithology.csv
│   └── removed_records/                # Three excluded-record CSVs
├── audit/
│   ├── excluded_wells.csv
│   ├── source_row_links.csv
│   ├── decisions.json
│   ├── checks.json
│   ├── map_addition.json
│   └── browser_map_checks.json
├── evidence/
│   ├── workflow/                       # Document versions used
│   └── plots/
│       ├── manifest_before_map_addition.json
│       ├── README_before_map_addition.md
│       └── well_filter/
│           ├── README.md
│           ├── manifest.json
│           ├── before_after_filter.png
│           ├── before_after_filter.pdf
│           ├── well_filter_map.html
│           ├── well_locations.csv
│           ├── well_locations.json
│           └── well_locations.geojson
└── scripts/
    ├── filter_wells.py
    ├── build_filter_maps.py
    ├── filter_map.js
    └── filter_map_template.html
```

## Method and source history

The [execution script](scripts/filter_wells.py) selects `well_id` values actually present in the stratigraphy table, checks summary flags and interval counts, and filters all three tables by that same set. It preserves excluded rows rather than dropping their history. It refuses to overwrite an existing iteration.

[input_files.csv](inputs/input_files.csv) records parent file paths and hashes. [source_row_links.csv](audit/source_row_links.csv) contains 24,197 occurrence links, covering every retained or archived input row. Each link identifies the iteration 1 file hash and CSV record ordinal, plus its frozen iteration 0 source identity. The header is record 1; ordinals refer to CSV records, which can contain quoted newlines.

Iteration 1's [representative metadata](../iter1_10082026_dedupe_strat_reports/outputs/representative_well_metadata.csv), [removed-well links](../iter1_10082026_dedupe_strat_reports/audit/deduped_well_links.csv), and [duplicate interval links](../iter1_10082026_dedupe_strat_reports/audit/stratigraphy_duplicate_links.csv) remain the deduplication evidence. Their paths and hashes are included as provenance inputs. All 71 representatives and all four farther matching records remain in the working subset. The 91 previously removed duplicate records remain archived in iteration 1; they were not reintroduced or counted among this iteration's 6,979 exclusions.

The execution command, from the repository root, was:

```bash
python3 04_analysis/stratigraphy_sequences/iter2_10092026_keep_stratigraphy_wells/scripts/filter_wells.py
```

## Verification

All 16 checks in [audit/checks.json](audit/checks.json) passed. Checks cover parent hashes, unique well IDs, valid joins, flags/counts, selection and exclusion accounting, original headers/values/order, complete occurrence links back to the parent and baseline, unchanged stratigraphy bytes, and preservation of deduplication representatives and links.

The user-approved rule is recorded in [decisions.json](audit/decisions.json). The manifest records source/output hashes, software, the script, audit files, and retained workflow documents. The copied action plan records the version used while this iteration was in progress; the living root documents subsequently record its closure.

## Coverage and handoff

The source region remains the original 19 townships. The retained wells occur in **18 townships**: T5N R25E (`WM5.00N25.00E`) has five parent wells and none has stratigraphy, so all five are archived by this filter. This is a coverage limitation, not a change to the intended regional model boundary.

Missing heights, uncertain height references, gaps, overlaps, and other existing preparation issues remain for later iterations. Retention establishes stratigraphy availability; it does not establish geological reliability. No layer names, depths, elevations, coordinates, or interpretations were corrected here.

Iterations 0 and 1 and the authoritative processed files remain unchanged. The completed iteration's outputs, archives, and evidence are frozen; subsequent data changes belong in a new iteration. CSVs are ignored by the current Git configuration, so retain the files themselves alongside their manifests.

## Maps added October 9, 2026

Open the [static before-and-after PNG](evidence/plots/well_filter/before_after_filter.png), [PDF](evidence/plots/well_filter/before_after_filter.pdf), or [interactive map](evidence/plots/well_filter/well_filter_map.html). All map artifacts and their [documentation](evidence/plots/well_filter/README.md) live inside this iteration.

Before means iteration 1's 7,311 well IDs; after means iteration 2's 332 retained IDs. The static plot has full-extent and closer-view comparisons with matching axes and 20 km / 5 km distance scales. Three excluded wells have recorded coordinates outside the closer view; all remain in the full-extent panels and interactive data.

The interactive map starts with the retained wells. Switch between before, after, excluded, and combined views; filter by lithology or search for a well/site/township. It uses USGS background tiles, offers **Wells only**, and falls back to the local static PNG if the interactive library cannot load. Coincident coordinates share a popup, without merging well IDs.

[browser_map_checks.json](audit/browser_map_checks.json) records successful browser checks with real USGS tile loads and simulated tile/library failures. [map_addition.json](audit/map_addition.json) records this later addition and preserved pre-addition metadata. Original data outputs, archives, filter decisions, verification results, and completion time remain unchanged.
