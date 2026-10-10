# Data format and identity rules

Workflow draft 2, October 8, 2026. Retain the current CSV schemas and add supporting metadata/archive tables where needed. The user selected physical removal of matching nearby records while retaining an existing representative well and all original records in archives. All working files belong in numbered iterations under this directory.

## Core CSVs

| Working file | Record meaning | Key/link |
|---|---|---|
| `boardman_wells_summary.csv` | One record for each existing well ID | Unique primary key: `well_id` |
| `boardman_wells_stratigraphy.csv` | One recorded interval occurrence; many intervals per well | `well_id` links to the summary; retain all original fields |
| `boardman_wells_lithology.csv` | One rock-description interval occurrence; many intervals per well | `well_id` links to the summary; retain all original fields |

Keep header names, original label strings, identifiers, and units in the initial working copies. Use UTF-8 CSV and document the delimiter and missing-value convention from the source snapshot before generating new files. Treat identifiers as strings. A blank is missing information; zero is a value. An absent modeled member is not automatically a zero-thickness observation.

Keep `well_id`, `wl_id`, and `gw_site_id` separately. The user-approved iteration 1 operation retains an existing representative `well_id` and archives removed original IDs with explicit links to that survivor. Representative rows retain their own original metadata; archived report metadata are not silently substituted into the surviving row.

Keep rock descriptions and named geological intervals in their separate tables. A broadly named interval does not provide the boundaries of its finer subdivisions. Do not create missing contacts from names or apparent sequence alone.

## Source row identity

Freeze the original files before creating stable interval occurrence IDs. A source occurrence is identified by the file's SHA-256 hash and CSV record ordinal, including the header as record 1. These are CSV records, not necessarily physical text lines if a quoted value contains a newline.

Record an `interval_id` in a sidecar table linked to that source identity. Keep it stable through sorting and later revisions. New user-submitted intervals receive new IDs and source links. Identical repeated rows still have separate occurrence IDs. Multiple original occurrences can link to one shared interpretation without losing their provenance.

## Supporting metadata

These filenames and fields are proposals; create them when the relevant iteration begins. Their contents complement the existing CSVs instead of overloading the original fields.

| File | Record meaning and suggested contents |
|---|---|
| `well_metadata.csv` | One row per `well_id`: source system, original identifiers, location source/reference, source links, and relevant notes |
| `interpretation_metadata.csv` | One row per well/interpretation association: interpretation ID, original interpreter text, report/record year, interpretation year if known, and evidence for each |
| `drilling_history.csv` | One row per sourced event: event ID, `well_id`, event type/date, related report identifier, source, and notes |
| `ground_elevation_sources.csv` | One row per available height source: `well_id`, original height/unit/reference, location, source method/document, adoption decision, and any derived height/conversion |
| `stratigraphy_duplicate_links.csv` | Links among `well_id`, source interval occurrences, and duplicate interpretation group IDs, with matching method and evidence |

One well may have several source heights or drilling events. Retain the alternatives; an adoption decision identifies the height used in calculations. Metadata can repeat a source fact for linked well records while pointing to the same evidence.

Retain original interpreter strings before resolving identities. Keep drilling completion date, report/record year, interpretation year, and acquisition date distinct. `scraped_at` is acquisition metadata; `complete_date` is not automatically an interpretation year. Leave unknown years blank.

## Approved duplicate-removal format

The baseline audit found identical interval collections across reports at shared sites. Compare the complete collection, including repeated occurrence counts, original labels, depths, elevations, thicknesses, interpreter, sample source, and age fields. Different site groups are not merged based on proximity.

The selected procedure supersedes the earlier choices of retaining all duplicate rows or creating new replacement IDs:

1. Use the most common coordinate pair in a group. If several pairs are equally common, use the location of the alphabetically first `well_id` among those pairs. Keep the alphabetically first well at the chosen location as the representative.
2. Remove other matching well records within 100 metres of that representative, inclusive. Keep farther records and their data unchanged. Distances are measured from the representative, without chaining through neighbors.
3. Write complete working summary/stratigraphy/lithology tables with their current headers and surviving original values. No new well IDs or scientific boundary values are introduced.
4. Write removed original rows to three separate CSVs under `outputs/removed_records/`. Removed lithology is archived under original IDs and is not transferred to the representative. The existing representative retains its own original lithology.
5. Record each removed original well under its surviving representative in `audit/deduped_well_links.csv`. Include original metadata, source-record identity, and distance. Provide `outputs/representative_well_metadata.csv` with one row per representative and its removed-ID list.
6. Link every output/archive row to its original file hash and record ordinal. Link every removed stratigraphy occurrence to its equivalent surviving occurrence.

Matching interpretations more than 100 metres apart remain in the working data under the approved rule. Therefore the final stratigraphy table may contain more rows than a complete one-copy-per-site collapse. Original location differences, completion dates, depths, and IDs remain available in the archives and audit rather than being averaged or overwritten.

## Heights and derived boundaries

Preserve recorded depths and endpoint elevations. A separately adopted ground height can produce a derived endpoint elevation only after verifying depth units and the depth reference. If depth is vertical distance downward from ground surface, the calculation is:

`boundary elevation = ground elevation − depth below ground`

Use the same units and height reference for both operands. Check whether a drilling record instead measures from a raised collar or reports distance along a deviated hole; those cases need an explicit transformation. Do not change drilling depth simply to match a new ground height.

Store derived boundary heights in a linked table, such as `stratigraphy_derived_elevations.csv`, with `interval_id`, endpoint, adopted height source, units/reference, method, and decision ID. An original endpoint elevation and a recalculated one are different values with different provenance. Unverified height references remain unresolved; do not assume NAVD1988 for the whole dataset.

## User-supplied reference wells

Preserve each submitted file and citation. Before appending to a working release, agree on unique `well_id` values and map the supplied fields into the current schemas. A separate external ID namespace is possible but has not yet been selected. Do not invent OWRD or GWIS IDs; retain absent external-system IDs as blanks.

Record interpreter, publication/report year, location, height source/reference, interval observations, and the evidence supporting the interpretation where available. Check whether the addition duplicates an existing record. Calling a well a reference does not automatically establish its geological certainty; its role in section interpretation is reviewed in the second stage.

Changes to summary counts and indicators after appending intervals must be calculated and logged. Preserve original source summaries in the raw snapshot and retain every addition's source links.
