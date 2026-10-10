# Database schema v001

All project tables are in schema `boardman`. `schema.sql` is the exact definition. `well_id` is the user-selected primary well key; original `wl_id` and `gw_site_id` remain separate source fields. IDs are not reassigned during this migration.

| Table | Key | Meaning |
|---|---|---|
| `iterations` | iteration number | Dataset parent, release/audit distinction, source status |
| `wells` | well_id | All 7,402 original well IDs |
| `source_files` | SHA-256 | Complete original bytes, compressed losslessly in the database |
| `source_locations` | historical path | Source-content associations and frozen workflow snapshots |
| `source_records` | UUID | Original CSV values as JSON, preserving strings and blanks; file hash and CSV record ordinal |
| `well_versions` | source-record UUID | Numeric coordinates/depth and original well-record reference |
| `intervals` | baseline source-record UUID | Each original stratigraphy/lithology occurrence, including repeated identical rows |
| `interval_versions` | source-record UUID | Numeric interval fields and stable original interval ID |
| `well_membership` | iteration + well_id | Working, deduplicated, or excluded_no_stratigraphy; selected well version |
| `interval_membership` | iteration + interval_id | Same membership states and selected interval version |
| `record_lineage` | child record UUID | Parent and baseline record links imported from existing provenance tables |
| `well_audits` | audit record UUID | Iteration 3 numeric and ground-height categories; full audit in source_records |
| `findings` | iteration-prefixed finding ID | Affected well, source record, optional interval, description; initial review status open |
| `finding_events` | event UUID | Future append-only review-status history |
| `ground_height_candidates` | source-record UUID | Unadopted endpoint depth-plus-elevation calculations |
| `ground_height_sources` | source-record UUID | Original linked-site height/reference and metadata/page content IDs |
| `well_height_links` | well + height source | Associations with saved site evidence, coordinate agreement, unadopted status |
| `duplicate_wells` | removed well_id | Existing representative, original removed well, measured distance |
| `duplicate_intervals` | removed interval UUID | Corresponding surviving original occurrence |
| `decisions` | iteration-prefixed decision ID | Complete decision metadata and evidence-file reference |
| `changes` | change UUID | Future field/value changes, reason and decision; empty after migration |

## Source and version identity

UUIDs are deterministic UUIDv5 over `source SHA-256:CSV record ordinal`, using the namespace in `common.py`. The header is CSV record 1; the first data row is record 2. Records are not physical text lines. Equal contents in distinct source occurrences remain distinct. Byte-identical files can share one content object, with multiple historical path associations.

Core interval revisions link to iteration 0 occurrences through the approved iteration 1/2 row-link tables. Membership covers all original wells/intervals in every recorded stage. Iteration 3 is an audit of iteration 2, not a modified data release. Iteration 4 inherits iteration 2's exact working selection and values. Deduplicated lithology stays under its original well ID.

## Numeric and reference handling

Original strings live in `source_records.raw_values`. SQL numeric fields use decimal `numeric`; blanks or nonnumeric/nonfinite values map to NULL only in the numeric representation. Zero remains zero. No source value is replaced. Named feet fields and repository convention govern interpretation; actual source measurement conventions remain unresolved where unverified.

Locations use SRID 4326 for the existing longitude/latitude display assumption. `horizontal_reference_status` explicitly states that the original datum is unverified. No coordinate or elevation transformation was performed. No vertical reference is assigned to interval elevations. Saved linked-site references are retained as source text and are not adopted for every linked interval.

Geometry and its index support later spatial queries under those assumptions. Model preparation must establish suitable horizontal/vertical references before treating these as verified 3D coordinates.

## Views and future edits

`working_wells` and `working_intervals` select working membership from the highest numbered data release, excluding audit-only iteration 3. `arcgis_wells` exposes simple point attributes for later export. Original well metadata and full interval fields are available by joining source_records.

Historical data tables reject UPDATE/DELETE via triggers. Future work inserts a new source/version, records a decision and change, and creates a new iteration's membership. A new finding status belongs in finding_events. The v001 map displays initial imported finding status; a later shared version should incorporate event history when review actions begin. Iteration completion and geological approval are separate concepts.

Source files, including prior maps, manifests, scripts, cached pages and documents, can be recovered by decompressing `source_files.content_gzip`. Existing relative links inside those historical documents are preserved as historical text; they do not need to resolve to read the database's stored values. Reconstructed source SHA-256 verifies the exact original bytes.
