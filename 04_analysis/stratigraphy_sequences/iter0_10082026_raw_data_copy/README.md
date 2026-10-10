# Iteration 0: unchanged starting snapshot

| Field | Value |
|---|---|
| Directory | `iter0_10082026_raw_data_copy` |
| Status | Complete |
| Local start | October 8, 2026, 17:18:28 PDT; America/Los_Angeles |
| Closed date | October 8, 2026; exact timestamp in [manifest.json](manifest.json) |
| Input version | Current authoritative processed CSVs; no parent data iteration |
| Workflow | Draft 1, October 8, 2026; document hashes in the manifest |
| Operator | Codex; automated snapshot verification |
| Geological review | Not part of this iteration |

## Purpose and completion check

Preserve an unchanged starting copy of the three current processed CSVs so later work can be compared with, and traced back to, the original records. Here, “raw” means unchanged processed inputs, rather than original drilling documents.

Completion requires matching source/copy bytes and SHA-256 hashes, matching headers and record counts, unchanged source files, and a recorded inventory. All 30 snapshot checks passed. This is a complete raw-copy iteration; it does not establish geological suitability.

## Inputs and outputs

Inputs came from [03_processed/boardman_19_townships](../../../03_processed/boardman_19_townships/). The manifest records exact repository-relative paths, file sizes, column names, data-row counts, and full SHA-256 hashes for both inputs and outputs. Row counts exclude the CSV header.

| Frozen working file | Data rows | SHA-256 of source and copy |
|---|---:|---|
| [boardman_wells_summary.csv](outputs/boardman_wells_summary.csv) | 7,402 | `0aa72d523e43e4d312cec67b480be6be179965a1b65428c2a69101e15695af17` |
| [boardman_wells_stratigraphy.csv](outputs/boardman_wells_stratigraphy.csv) | 1,854 | `4cd54db4ec0e21d6edaaa3f132f913bb62c2a8d66e90ae290113ac06c0d768d0` |
| [boardman_wells_lithology.csv](outputs/boardman_wells_lithology.csv) | 15,586 | `47680f75ad2c79a01acb397b4f2bfba3b5042c2bae1a6250cdf92acf27b29150` |

These are complete starting tables, not additions or change lists. Every source record retains its original values, sequence, identifiers, labels, missing fields, and existing issues. Because the files are identical, the source hash and CSV record ordinal also identify the same record in each copy; no rewritten row-link table is needed here.

## Method

[scripts/create_snapshot.py](scripts/create_snapshot.py) used Python's standard library to read source bytes, write each copy without reserializing the CSV, inspect headers/counts, and compare hashes and contents. Its hash and the Python version are recorded in the manifest. The script refuses to overwrite an existing snapshot.

The execution command, from the repository root, was:

```bash
python3 04_analysis/stratigraphy_sequences/iter0_10082026_raw_data_copy/scripts/create_snapshot.py
```

This command is retained as execution evidence, not an instruction to overwrite the completed iteration. Later corrections or new snapshots belong in new iterations.

## Verification

[audit/checks.json](audit/checks.json) records expected and actual results for all 30 checks:

- For each CSV: matching hashes, identical bytes, unchanged source after copying, matching file size, matching headers, preserved row count, expected baseline row count, matching existing audit hash, and consistent CSV field counts.
- For the package: three inputs, three outputs, and a directory date matching the actual local start date.

The existing [baseline audit](../artifacts/summary.json) was read as comparison evidence and remains unchanged. No cleaning or geological audit was rerun. Coordinate and height references were not reassessed or transformed; the original data were preserved. Null reference fields in the manifest mean this iteration did not evaluate them.

## Decisions, limitations, and handoff

No scientific values were changed, and no geological choices were made. Existing duplicates, gaps, overlaps, missing elevations, and other previously recorded limitations remain for later work. No wells were removed, renamed, or added.

Iteration 1 should reference these exact frozen files. Duplicate representation remains a decision before deduplication; see the [data-format proposal](../DATA_FORMAT.md). The broader sequence is in the [action plan](../ACTION_PLAN.md) and [iteration index](../ITERATIONS.md).

Retain this completed directory unchanged by workflow convention. CSV files are ignored by the current Git configuration, so the snapshot files themselves must remain available alongside their manifest; Git history alone does not preserve them.
