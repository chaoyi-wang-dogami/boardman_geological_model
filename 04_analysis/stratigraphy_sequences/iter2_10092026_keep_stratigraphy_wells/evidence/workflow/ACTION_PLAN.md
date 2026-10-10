# Boardman well preparation action plan

This plan implements the user's October 8–9, 2026 decisions. It separates basic well preparation from geological judgments made during cross-section interpretation. Draft 3 retains the approved within-group 100-metre deduplication rule and adds the stratigraphy-availability filter. [Iteration 0](iter0_10082026_raw_data_copy/README.md) and [iteration 1](iter1_10082026_dedupe_strat_reports/README.md) are complete. Iteration 2 is in progress; other preparation tasks remain planned.

## Accepted scope decisions

1. **Keep layer names exactly as recorded.** Do not apply the draft hierarchy, aliases, `.general` substitutions, or name merges during this preparation scope. Naming can be revisited in a separately documented later cleaning iteration. :codex-annotation{index="1"}

2. **Review the few gap and overlap cases individually.** There are four gaps in three wells and two overlaps in a fourth well, listed below. Do not introduce a dataset-wide boundary adjustment rule for these cases. :codex-annotation{index="2"}

3. **Defer geological suitability judgments to cross sections.** Preparation records missing fields, arithmetic discrepancies, source information, and unresolved questions. It does not assign new confidence scores, declare wells geologically unreliable, or exclude wells from modeling. Those decisions require comparison with other evidence in the second stage. Existing source location classes remain metadata. :codex-annotation{index="3"}

4. **Use the well as the primary record.** The working well table uses `well_id` as its primary key. Preserve every original well and its metadata in the snapshot or archives. The user's later instruction authorizes removing matching nearby records from the working release and recording them under an existing surviving representative well. No new well IDs are created; original IDs remain linked and recoverable. :codex-annotation{index="4"}

5. **Start with the current CSV format and current data.** The user will supply additional published reference wells and add them to the working CSV package. This workflow will record those additions and their sources; it will not independently select or import external wells at this stage. :codex-annotation{index="5"}

6. **Keep wells with stratigraphy in the working subset.** On October 9, the user approved iteration 2 to retain every `well_id` with at least one stratigraphy row, whether or not lithology is present. This supersedes the earlier proposal to require both datasets. Archive excluded wells and their associated rows without changing values. This is a data-availability filter; it does not judge geological reliability or independently change the intended regional model boundary.

## Preparation tasks

| Order | Task | Deliverable | Completion check |
|---|---|---|---|
| 1 | Freeze a raw working copy — complete | [Iteration 0](iter0_10082026_raw_data_copy/README.md) containing the three current CSVs and a manifest | All 30 snapshot checks passed; copies match source bytes/hashes, counts, and original columns |
| 2 | Remove nearby duplicate stratigraphy reports — complete | [Iteration 1](iter1_10082026_dedupe_strat_reports/README.md): working CSVs, original-record archives, and survivor links | All 15 checks passed; 91 duplicate well records removed and archived; four farther records kept |
| 3 | Keep wells with stratigraphy — in progress | Iteration 2: three working CSVs, exclusion archives, reasons, and source-row links | Every working well has stratigraphy; associated lithology is optional; all input rows are preserved in outputs or archives |
| 4 | Organize well metadata | Well, interpretation, and drilling-history metadata linked by `well_id` | Interpreter strings and available years/dates are retained without invented values or identity merges |
| 5 | Verify ground heights and references | Ground-height source table and separately recorded derived elevations where justified | Each changed or added height has a source, unit, reference, and calculation; original values remain recoverable |
| 6 | Review the four affected wells individually | Case notes and any user-approved derived boundary changes | Every proposed change has a source-row link, evidence, reason, and explicit decision |
| 7 | Check basic consistency and assemble the prepared release | Versioned working CSVs, factual checks, and open issues | Keys/joins/counts are valid; names remain unchanged; unresolved items are listed without suitability classifications |

The order is provisional. Metadata and height work can proceed alongside individual case review. User-supplied reference wells can be added in their own iteration whenever available, then undergo the same basic checks.

## Individual boundary cases

Depths below are feet under the current repository convention. Source record numbers refer to `boardman_wells_stratigraphy.csv`, including its header as record 1.

| Well primary key | Reference site | Source records | Recorded issue |
|---|---|---|---|
| `UMAT_0005342` | 17692 | 688–689 | Gap between 110.00 and 111.00 ft |
| `UMAT_0005858` | 15900 | 748–749 | Gap between 154.00 and 154.50 ft |
| `UMAT_0005859` | 15899 | 752–754 | Gaps between 5.00 and 8.00 ft, and between 148.00 and 151.00 ft |
| `MORR_0001751` | 940 | 314–317 | Overlaps of 13.00 ft and 58.00 ft |

Start from the individual source records and available original logs. A midpoint, rounding adjustment, gap fill, or endpoint replacement is a proposal until the user approves it. If local evidence cannot resolve a case, carry it into cross-section review. Do not discard the well to make the preparation table appear complete.

## Ground heights

The current data allow recovery of the source-used ground height at 327 of 328 reference sites by adding depth to endpoint elevation. That calculation does not independently verify the height or its reference. Site 6676 has five depth intervals with no endpoint elevations.

The existing 35-site source-metadata audit under `07_commercial_eval/rockworks/input/35_paired_spread/` contains recorded ground heights and height references: 34 NAVD1988 and one NGVD1929. Use it as existing evidence with its saved source-page hashes; do not extrapolate its reference to all wells.

Verify sources and positions before filling heights or applying a reference conversion. Record derived endpoint elevations separately. Do not alter recorded drilling depth merely because the adopted ground height changes.

## Decisions before executing data changes

- **Duplicate handling — decided:** group only matching complete interpretations at the same site. Use the most common recorded location; when no location is more common, use the location of the alphabetically first `well_id`. Keep an existing representative at that location, remove other matching records within 100 m, archive them under their original IDs, and link them to the survivor. Removed lithology stays archived; surviving wells keep their own data. See [DATA_FORMAT.md](DATA_FORMAT.md).
- **Year meaning:** distinguish report/record year, drilling year, and interpretation year. Preserve available values and leave unknown years blank; scraping dates are acquisition metadata.
- **Individual boundary changes:** approve each proposed adjustment after inspecting its evidence. A shared interpretation correction must identify every linked working-well row affected.
- **External additions:** agree on unique IDs and source information for user-supplied wells before appending them. Missing OWRD/GWIS identifiers must remain blank rather than invented.

These questions govern later execution. They do not block creation of this documentation package.

## Handoff to the second stage

The prepared release contains consistent well keys, source-linked metadata and heights, documented duplicate handling, and individual case outcomes. It can include unresolved factual deficiencies. Decisions about geological reliability, interpretation conflicts, exclusions, and connections between wells belong to cross-section iterations, as described in [ROADMAP.md](ROADMAP.md).
