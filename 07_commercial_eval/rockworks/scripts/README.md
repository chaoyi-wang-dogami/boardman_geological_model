# RockWorks evaluation scripts

Store reproducible input-preparation, schema-validation, and round-trip comparison scripts here.

- `build_spread_sample.py`: creates the current paired-only 35-report `.xls`,
  selection audits, source hashes, and cached GWIS/NOAA datum evidence.
  It checks every workbook cell with an independent XLS reader.
- `plot_spread_sample.py`: plots the current selected reports and full paired
  pool against the 19-township AOI.
- `audit_35_well_sources.py`: retains the earlier provisional 19-township audit;
  it includes stratigraphy-only reports and does not generate the current sample.

Run scripts from the repository root with `.venv/bin/python`. See the
[import instructions](../input/35_paired_spread/IMPORT_INSTRUCTIONS.txt) for
scoped Excel dependencies and exact reproduction commands. All scripts write
only within the RockWorks evaluation directory and leave processed data intact.
