# Elevation and depth completeness — read-only audit

Audited October 9, 2026: iteration 2's **332 well IDs, 1,427 stratigraphy intervals, and 1,215 lithology intervals**. No data values were changed. [checks.json](checks.json) contains the counts; [well_completeness.csv](well_completeness.csv) and [interval_findings.csv](interval_findings.csv) identify the affected wells and source occurrences.

## What is complete and what is missing

All stratigraphy and available lithology interval top/bottom depths are present and numeric. There are **19 wells missing the separate drilling completion-depth field**. Their interval depths are still present; the longest interpreted interval must not automatically be substituted for the missing drilling depth.

**MORR_0000561**, site **6676**, has five stratigraphy intervals with all ten endpoint elevation fields blank. Its depths are present. It has no calculated ground-height candidate or matching saved ground-height evidence in the sources inspected here. Every other well has all endpoint elevations.

The primary numeric map contains 246 green wells, 19 red, one orange, and 66 purple. Green means that required numeric fields exist and this audit found no numeric/sequence discrepancy. It does not mean the well is ready for modeling.

## Discrepancies to review

| Finding | Interval occurrences | Well IDs | Meaning |
|---|---:|---:|---|
| Interval below recorded completion depth | 127 | 64 | 104 stratigraphy and 23 lithology intervals extend below the summary's reported completion depth |
| Internal stratigraphy gaps | 4 | 3 | Adjacent recorded intervals leave a depth range uncovered |
| Internal stratigraphy overlaps | 2 | 1 | Recorded interval depth ranges overlap |
| Zero-thickness lithology interval | 1 | 1 | `MORR_0052638`, lithology CSV record 1021, has identical top and bottom depths |

These well counts overlap; their union is **66 wells**. A depth beyond a report's completion can reflect a shared site interpretation, later drilling, or a report-specific deficiency. It is a discrepancy requiring source review, not proof that the interval is wrong. No depths were truncated and no gap or overlap was repaired.

No interval thickness arithmetic errors, elevation-versus-depth thickness differences, negative depths, nonnumeric/nonfinite depth values, or inconsistent implied ground heights were found. The single zero-thickness lithology interval is still flagged separately.

## Ground height and reference information

The core CSVs have **no explicit ground-height column** and **no interval elevation-reference field**. This is different from saying that their numeric interval elevations are missing.

Depth plus endpoint elevation supplies **331 consistent implied ground-height candidates**. All usable endpoints within each well agree within 0.01 ft. There are 2,844 endpoint calculations in [ground_height_candidates.csv](ground_height_candidates.csv). They recover the offset used by the source records under a ground-based-depth assumption; they do not establish an independently checked land-surface height.

Existing cached GWIS pages contain ground height and reference information for **35 sites linked to 36 retained well IDs**. The saved raw ground heights equal those 36 wells' implied heights. This is evidence from the same source system, so agreement is not an independent measurement. The linked site reference strings are NAVD1988 for 35 well IDs and NGVD1929 for one; these strings were not assigned to interval elevations or converted.

**30** linked well coordinates match the saved site coordinates exactly; **six differ**. The original and saved coordinates remain in the audit table for review. A location difference does not by itself establish that a height is wrong, and no location or height was replaced.

The ground-height map therefore shows **36 recorded at a linked site, 295 calculated only, and one missing**. The reference view shows available linked-site evidence for 36 wells and none in the inspected saved evidence for 296. **All 332 interval height references remain unrecorded in the core data.** No common reference system can be declared from completeness alone.

Units are feet under repository conventions and named `_ft` fields. The core interval records do not independently encode their measurement units or where depth zero begins. Calculations state those assumptions; this audit has not verified every original log's measurement convention. No new elevation source or ground survey was obtained.

## Actions to consider next — not executed

| Problem | Suggested next investigation | Do not substitute automatically |
|---|---|---|
| 19 missing completion depths | Check original drilling reports and construction histories; preserve any alternative depths with sources | Deepest interpreted interval for reported drilling depth |
| One well missing elevations/ground height | Obtain a sourced ground height and its units/reference, then evaluate calculating endpoint elevations from recorded depths | Neighboring-well heights or an unspecified height source |
| Height references absent in core data | Gather source-backed height/reference metadata for the retained wells and check the six saved-site location differences | One reference system for all wells based on the small cached sample |
| 66 wells with depth/sequence discrepancies | Review the report/site history and individual recorded intervals before proposing replacements | Truncating intervals, choosing midpoint boundaries, or filling gaps without evidence |

The audit phase is complete. Iteration 3 remains open, awaiting decisions about the action phase. Iteration 2 remains the accepted working data. Audit CSVs and maps are evidence, not a corrected release.
