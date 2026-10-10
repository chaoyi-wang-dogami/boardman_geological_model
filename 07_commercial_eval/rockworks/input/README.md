# RockWorks test inputs

Store RockWorks-ready test workbooks, CSV files, schema notes, and an input manifest here. Generate them from the authoritative Boardman processed files whenever practical.

## Current paired-data sample

[35-well import workbook](35_paired_spread/boardman_35_paired_spread_rockworks.xls)
contains 35 distinct well reports and GWIS sites with both processed lithology
and stratigraphy, selected for township coverage and spatial spread.
It covers all 13 townships containing paired data; it does not cover all 19.

Read [the import instructions](35_paired_spread/IMPORT_INSTRUCTIONS.txt) before
importing. Coordinates are EPSG:26911 metres and elevations are NAVD88 metres.
Original values and provenance remain in the workbook and sidecars. Native
RockWorks import has not yet been executed. Stratigraphy Type order requires
geological review before modeling.

The [selection manifest](35_paired_spread/selected_wells.csv), full paired-pool
audit, datum evidence and validation manifest are alongside the workbook.
The [coverage map](../figures/35_paired_spread_coverage.png) shows the selected
reports, the full paired pool, and the six townships without paired data.

`35_well_preflight/` is the earlier provisional 19-township audit, superseded
for sample selection by the paired-only sample. It includes reports without
processed lithology and is not the current import package.
