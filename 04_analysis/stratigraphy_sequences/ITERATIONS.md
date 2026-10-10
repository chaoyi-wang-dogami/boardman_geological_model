# Boardman iteration index

Workflow draft 5, October 9, 2026. Iterations 0, 1, 2, and 4 are complete. Iteration 4 is the current database release, retaining iteration 2's 332 working well IDs and unchanged values. Iteration 3's read-only elevation/depth audit and maps are complete; the overall iteration awaits action decisions. No geological corrections or external additions have started.

## Data iterations

| Number | Directory | Purpose | Local start date | Input version | Status | Outputs | Open decisions | Closed date |
|---|---|---|---|---|---|---|---|---|
| 0 | [iter0_10082026_raw_data_copy](iter0_10082026_raw_data_copy/README.md) | Freeze unchanged current CSVs | October 8, 2026 | Authoritative processed inputs; exact hashes in manifest | Complete | Three CSVs, manifest, checks, README, execution script | None for this iteration | October 8, 2026 |
| 1 | [iter1_10082026_dedupe_strat_reports](iter1_10082026_dedupe_strat_reports/README.md) | Remove matching nearby reports and link archived wells to surviving representatives | October 8, 2026 | Frozen iteration 0 | Complete | 7,311 working wells; 1,427 stratigraphy intervals; 15,459 lithology intervals; 91 removed wells archived and linked | None for this iteration | October 8, 2026 |
| 2 | [iter2_10092026_keep_stratigraphy_wells](iter2_10092026_keep_stratigraphy_wells/README.md) | Keep wells with stratigraphy, with associated lithology where present | October 9, 2026 | Frozen iteration 1 | Complete | 332 working well IDs; 1,427 stratigraphy rows; 1,215 lithology rows; 6,979 excluded wells and 14,244 lithology rows archived | None for this filter; geological preparation continues | October 9, 2026 |
| 3 | [iter3_10092026_audit_heights_and_depths](iter3_10092026_audit_heights_and_depths/README.md) | Audit heights/depths, then choose actions after review | October 9, 2026 | Frozen iteration 2 and existing cached site evidence | Awaiting review | Completed phase 1 audit of 332 wells; findings, candidates, static/interactive maps; no modified data release | Actions for missing depths/elevations, references, and discrepancies not yet selected | |
| 4 | [iter4_10092026_build_postgres_well_database](iter4_10092026_build_postgres_well_database/README.md) | Import history and audit into PostgreSQL/PostGIS; build an HTML snapshot | October 9, 2026 | Iteration 2 working data, iteration 3 audit, iterations 0–1 history | Complete | Local database, frozen backup, interactive map, source inventory; 34 live and 34 restored-data checks passed | Height/depth actions remain in iteration 3; ArcGIS export deferred | October 9, 2026 |

## Next work

Use iteration 4's database release as the input to later well-preparation tasks. Its `boardman.working_wells` and `boardman.working_intervals` views expose the accepted subset; its frozen backup reconstructs this release. Iteration 2's CSVs remain its unchanged source values. Retained wells cover 18 of the original 19 townships; T5N R25E has no stratigraphy in this dataset.

Reuse the tools in `database/versions/v001/`; do not copy Compose or scripts into each iteration. Freeze changed tooling in a new version. Each later iteration records exact input backup hashes, tool version, changes, final backup, map, and verification.

Review [iteration 3's findings](iter3_10092026_audit_heights_and_depths/audit/phase1_completeness/FINDINGS.md) before choosing its action phase. Phase 1 is retained as read-only evidence; iteration 3 remains open until the agreed action scope is completed or the user selects audit-only closure.

Iteration 0 began on October 8, 2026, so its directory is `iter0_10082026_raw_data_copy`. Later numbers are allocated when work begins, in execution order, rather than reserved for every proposed roadmap task. Use each iteration's actual local start date.

## Index fields for active work

For each iteration, record its number, exact directory link, purpose, local start date, parent/input version, status, principal outputs, open decisions, and closed date when applicable. Use these statuses:

| Status | Meaning |
|---|---|
| Planned | Proposed work; no claim that files or outputs exist |
| In progress | Work has begun against recorded inputs |
| Awaiting review | Results exist, but consequential decisions or acceptance remain pending |
| Complete | Required outputs and checks are complete; outstanding issues are explicitly carried forward |
| Superseded | Retained historical result replaced by a later completed iteration |
| Cancelled | Retained record explaining why the work stopped |

An iteration may be complete with an unresolved issue if its purpose was to document that issue rather than resolve it. Completion never implies geological approval of every well or boundary.

## Documentation history

| Date | Change | Data effect |
|---|---|---|
| October 8, 2026 | Added the action plan, iterative SOP, roadmap, data-format proposal, directory conventions, and reusable templates based on the user's comments | None; existing findings, audit artifacts, and authoritative inputs retained |
| October 8, 2026 | Completed iteration 0 and updated workflow status links | Three unchanged CSV copies created; all 30 snapshot checks passed; authoritative inputs retained |
| October 8, 2026 | Completed iteration 1 using existing representatives and the 100 m rule | 91 well records, 427 stratigraphy intervals, and 127 lithology intervals removed from working tables and preserved in archives with survivor links |
| October 9, 2026 | Added before-and-after plots, plotted coordinates, and reproduction method inside iteration 1 at the user's request | Plot PNG/PDF/CSV copied unchanged; previous manifest/README retained; deduplication data and rules unchanged |
| October 9, 2026 | Replaced the blocked OpenStreetMap background with USGS in both interactive map copies; added a Wells only option and tile failure messages | Display repair only; prior map and manifests retained in iteration 1; group locations, static plots, and deduplication data unchanged |
| October 9, 2026 | Completed iteration 2 using the approved stratigraphy-only availability filter; superseded the unexecuted proposal to require both datasets | 332 working well IDs retained; all 1,427 stratigraphy rows unchanged; 1,215 associated lithology rows retained; 6,979 wells and 14,244 lithology rows archived with source links |
| October 9, 2026 | Added static full-extent/closer before-and-after comparisons and a USGS interactive map inside iteration 2 | Display evidence only; original data outputs, archives, decisions, and closure time unchanged; previous manifest/README retained |
| October 9, 2026 | Completed iteration 3's read-only audit phase and category maps; left iteration open for action decisions | No data changes; 19 missing completion depths, one well missing elevations, and 66 wells with discrepancies identified; calculated heights remain candidates |
| October 9, 2026 | Completed iteration 4 with shared versioned database tools, relational history, offline HTML inspection, and a tested backup | 332 working wells and all interval values unchanged; all 7,402 original IDs and 163 open audit findings retained; no height candidates adopted |
| October 9, 2026 | Repaired iteration 4's opening basemap using map tools v002; retained previous map and manifests | Display only: existing embedded data and database backup unchanged; verified live USGS tiles, background switching, and offline controls |

Keep dated plan revisions here. Once data iterations begin, record material workflow changes in the affected iteration's decisions and retain the document version used to perform the work.
