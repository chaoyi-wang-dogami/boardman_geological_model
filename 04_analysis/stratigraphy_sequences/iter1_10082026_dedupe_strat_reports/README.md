# Iteration 1: remove duplicate reports within 100 metres

Status: **Complete**. Started October 8, 2026, 18:00:41 PDT, America/Los_Angeles. Exact closure time is in [manifest.json](manifest.json). Input: the three frozen [iteration 0 CSVs](../iter0_10082026_raw_data_copy/outputs/).

## Result

91 duplicate well records were removed from the working release and recorded under their existing surviving representative wells. Their original records remain in separate archive CSVs. No new well IDs were created. All retained CSV row values and original headers are unchanged.

| Table | Iteration 0 rows | Working rows | Archived rows |
|---|---:|---:|---:|
| Well summary | 7,402 | 7,311 | 91 |
| Stratigraphy intervals | 1,854 | 1,427 | 427 |
| Lithology intervals | 15,586 | 15,459 | 127 |

All 71 groups were checked. 68 groups had records removed; three had no other matching record within 100 metres of the representative. The groups originally contained 166 well records and now retain 75: 71 representatives and four farther records. The complete working data have 332 well IDs with stratigraphy.

## Exact rule applied

1. Compare records only within the same `gw_site_id`, requiring identical complete scientific interval collections. The comparison includes original names, depths, endpoint elevations, thickness, sample source, interpreter, ages, and repeated occurrence counts. Different site groups are not combined based on proximity.
2. Choose the most frequently recorded coordinate pair in each group. In nine groups, no location was more common than another; the user's choice was to use the location of the alphabetically first `well_id` among the equally common locations.
3. Keep the alphabetically first existing well at the chosen location as the representative. Preserve its original summary, stratigraphy, coordinates, IDs, dates, and its own lithology.
4. Remove other matching well records within 100 metres of that representative, inclusive. Measure directly from the representative; do not extend the removal radius through nearby wells.
5. Archive every removed original summary, stratigraphy, and lithology row under its original well ID. Do not transfer archived lithology to the representative. 21 removed well records have lithology, totaling 127 archived intervals.
6. Link each removed well and each removed stratigraphy occurrence to the survivor. The user's latest instruction to keep a surviving representative supersedes the earlier proposal to create a new working well ID.

The copying explanation is the user's hypothesis. This operation does not establish how the original interpretations were produced.

## Where to find the working data and original records

```text
iter1_10082026_dedupe_strat_reports/
├── README.md
├── manifest.json
├── inputs/input_files.csv
├── outputs/
│   ├── boardman_wells_summary.csv
│   ├── boardman_wells_stratigraphy.csv
│   ├── boardman_wells_lithology.csv
│   ├── representative_well_metadata.csv
│   └── removed_records/
│       ├── boardman_wells_summary.csv
│       ├── boardman_wells_stratigraphy.csv
│       └── boardman_wells_lithology.csv
├── audit/
│   ├── groups.csv
│   ├── well_group_membership.csv
│   ├── deduped_well_links.csv
│   ├── stratigraphy_duplicate_links.csv
│   ├── source_row_links.csv
│   ├── decisions.json
│   ├── checks.json
│   ├── plot_addition.json
│   └── map_background_fix/            # Prior map, manifests, repair evidence
├── evidence/
│   ├── workflow/                      # Document versions used
│   └── plots/
│       ├── manifest_before_plot_addition.json
│       ├── README_before_plot_addition.md
│       ├── plot_manifest_before_addition.json
│       ├── duplicate_groups/          # Original map and overview
│       └── before_after/
│           ├── README.md
│           ├── manifest.json
│           ├── before_after_dedupe.png
│           ├── before_after_dedupe.pdf
│           └── comparison_locations.csv
└── scripts/
    ├── dedupe.py
    └── plot_before_after.py
```

[representative_well_metadata.csv](outputs/representative_well_metadata.csv) provides each representative's removed-well list. [deduped_well_links.csv](audit/deduped_well_links.csv) has one row per removed well, sorted under its surviving representative, including original coordinates, IDs, dates, drilling depth, location class, source row, and distance. The [archives](outputs/removed_records/) retain every original column, including interpreter information in the stratigraphy table.

For example, `MORR_0000596` is archived under surviving `MORR_0000592` at site 1, at the same recorded location. The survivor's original row remains unchanged.

## Farther matching records deliberately retained

| Site | Surviving representative | Farther original well kept | Separation |
|---|---|---|---:|
| 79 | `UMAT_0001202` | `UMAT_0001205` | 244 m |
| 9297 | `UMAT_0001581` | `UMAT_0058282` | 440 m |
| 9301 | `UMAT_0001580` | `UMAT_0056176` | 707 m |
| 14674 | `UMAT_0052043` | `UMAT_0057516` | 104 m |

Consequently, 19 interval copies remain beyond the 1,408-row complete site collapse described in the earlier audit. The final 1,427 rows follow the approved distance rule rather than discarding those farther records.

## Verification and closure

All 15 checks in [audit/checks.json](audit/checks.json) passed. The execution method reads back every output and archive CSV, compares every field with its source, and proves that the two partitions account for every original row. Checks also cover unique well IDs, valid joins, summary counts/flags, complete interpretation matching, representative preservation, removal distances, farther records, and occurrence-level links.

Input and output hashes, original record ordinals, accepted decisions, script hash, and retained workflow-document hashes are in the manifest and audit files. [source_row_links.csv](audit/source_row_links.csv) identifies every working/archive row using the frozen input hash and CSV record ordinal, with the header counted as record 1. [stratigraphy_duplicate_links.csv](audit/stratigraphy_duplicate_links.csv) links all 427 removed interval occurrences to their surviving equivalents.

The execution command, from the repository root, was:

```bash
python3 04_analysis/stratigraphy_sequences/iter1_10082026_dedupe_strat_reports/scripts/dedupe.py
```

The script refuses to overwrite an existing iteration. Completed outputs are frozen by workflow convention; future corrections belong in another iteration. CSVs are ignored by the current Git configuration, so retain the actual files with their manifest.

Use the three root files in `outputs/` as the accepted input to the next preparation iteration. Original processed sources and iteration 0 remain unchanged. Existing geological gaps, overlaps, missing heights, unknown years, and source-location accuracy questions remain for their planned stages. No scientific boundaries or names were corrected here.

## Before-and-after plots added October 9, 2026

The [PNG comparison](evidence/plots/before_after/before_after_dedupe.png), [PDF](evidence/plots/before_after/before_after_dedupe.pdf), and [plot documentation](evidence/plots/before_after/README.md) now live inside this iteration. They show the 166 original group records and 75 surviving records, using the same map limits and 5 km scales.

The [original overview](evidence/plots/duplicate_groups/duplicate_groups_overview.png) and [interactive map](evidence/plots/duplicate_groups/duplicate_groups_map.html) also live here, with their source group tables and recorded hashes.

The plots and plotted-coordinate CSV were copied without changing their bytes. The old manifest and README were saved before adding plot references. This is a documented addition to the completed iteration; the working data, archives, decisions, and original closure date are unchanged.

Later on October 9, the interactive map background was changed to USGS after OpenStreetMap displayed blocked tile images. The map now offers **Wells only** and a clear message when background tiles cannot load. Both interactive HTML copies and their generator were updated; the prior map and file records are preserved in [audit/map_background_fix](audit/map_background_fix/). Static plots, well locations, and deduplication data remain unchanged.
