# Iteration 3: audit heights and depths before choosing corrections

**Status: Awaiting review. Phase 1 audit is complete; the action phase has not started.** Started October 9, 2026, America/Los_Angeles. Iteration 3 remains open. [Iteration 2](../iter2_10092026_keep_stratigraphy_wells/README.md) remains the current working data release.

The user authorized a read-only audit and maps for the filtered 332 well IDs. No working CSVs were copied into a replacement release, corrected, or excluded. Ground-height calculations remain audit candidates. The overall iteration will be closed only after the next actions are agreed and completed, or the user chooses to close it as audit-only.

## Results and maps

Read [the findings and proposed next actions](audit/phase1_completeness/FINDINGS.md).

| Numeric audit category | Well IDs |
|---|---:|
| Green: required numeric fields complete; no flagged discrepancy | 246 |
| Red: completion depth missing | 19 |
| Orange: interval elevations missing | 1 |
| Purple: discrepancy to review | 66 |
| Total | 332 |

The categories are exclusive in the order red, orange, purple, green. All individual findings remain available even when a higher-priority category determines the color. Green does not confirm geological reliability, a ground height, or an elevation reference.

Open the [static PNG](evidence/plots/completeness/audit_completeness.png), [PDF](evidence/plots/completeness/audit_completeness.pdf), or [interactive map](evidence/plots/completeness/audit_map.html). The static map has separate numeric-completeness and ground-height panels with matching bounds and 5 km scales. The interactive map also shows saved site height-reference information, category counts, search, and all source-record findings in popups. It uses USGS tiles, offers Wells only, and retains the static fallback when the map library cannot load. [Map documentation](evidence/plots/completeness/README.md) explains the colors and reproduction.

## Audit records and evidence

- [well_completeness.csv](audit/phase1_completeness/well_completeness.csv): one row per well ID, all completeness indicators, categories, source links, height candidates, and available cached site metadata.
- [interval_findings.csv](audit/phase1_completeness/interval_findings.csv): 163 findings, including summary completion-depth deficiencies and interval-specific discrepancies. Each finding identifies its input file hash and CSV record ordinal.
- [ground_height_candidates.csv](audit/phase1_completeness/ground_height_candidates.csv): 2,844 endpoint calculations, with their source identity and stated assumptions. None is an adopted height.
- [cached_ground_height_sources.csv](audit/phase1_completeness/cached_ground_height_sources.csv): 35 saved GWIS-site ground-height records, with metadata and source-page hashes.
- [classification_rules.json](audit/phase1_completeness/classification_rules.json): the map priorities, arithmetic threshold, missing-value treatment, and reference limitations.
- [checks.json](audit/phase1_completeness/checks.json): factual counts and successful consistency/provenance checks.

```text
iter3_10092026_audit_heights_and_depths/
├── README.md
├── manifest.json                     # Open audit → action iteration
├── inputs/
│   ├── input_files.csv
│   └── parent_manifest_snapshot.json
├── audit/phase1_completeness/
│   ├── FINDINGS.md
│   ├── well_completeness.csv
│   ├── interval_findings.csv
│   ├── ground_height_candidates.csv
│   ├── cached_ground_height_sources.csv
│   ├── classification_rules.json
│   ├── checks.json
│   ├── browser_checks.json
│   └── manifest.json
├── evidence/
│   ├── workflow/                     # Document versions used
│   └── plots/completeness/            # PNG, PDF, HTML, data, map manifest
└── scripts/
    ├── audit_heights_and_depths.py
    ├── build_audit_maps.py
    ├── map_geometry.py
    ├── audit_map.js
    └── audit_map_template.html
```

## Method, verification, and boundaries of this audit

The audit reads iteration 2's three CSVs and existing saved source evidence under `07_commercial_eval/rockworks/input/35_paired_spread/evidence/`. It verifies source hashes and the cached pages' recorded height/reference fields. No new source pages, elevation datasets, or reference wells were acquired. Source information is linked by its recorded `gw_site_id`; saved site coordinates and well coordinates are compared explicitly, without assuming the locations are identical.

Depths/elevations follow the repository feet convention. A 0.01 ft arithmetic threshold identifies discrepancies above the displayed precision; it is not a geological acceptance threshold. Blank, nonnumeric, and nonfinite values are unavailable. Zero remains a value, negative elevations remain valid numbers, and no undocumented finite sentinel value is silently converted to missing.

Implied ground height is depth plus endpoint elevation, assuming depth zero is ground surface and both values use the same units. Agreement among endpoints demonstrates arithmetic consistency. It does not independently verify the terrain height or reference system. The interval reference field is absent in all three core CSVs; cached site reference strings remain separate.

The phase manifest records the input versions, audit outputs, and review evidence. Browser checks confirmed real USGS tile loading, category counts, searches, source-record popups, and tile/library failure fallbacks. All source files and the parent manifest retain their original hashes. CSV record ordinals count the header as record 1 and can span quoted physical text lines.

To reproduce the audit, use a separate checkout or new iteration location: the audit script refuses an existing phase or iteration manifest. To reproduce maps from the accepted audit, use the map script with a new external `--output-dir`; it refuses existing outputs. Source SHA-256 hashes and scripts are recorded in the manifests.

Preserve phase 1 after review. Any agreed action phase must record the finding it addresses, old/new values, supporting source, calculation, and approval, and must retain the original observations. No actions are authorized by this audit's colors alone.
