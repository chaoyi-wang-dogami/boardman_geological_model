# SOP: iterative well preparation and geological modeling

Workflow draft 1, October 8, 2026. This procedure covers basic well preparation, cross-section interpretation, and 3D modeling. The stages have different purposes, but they share the same record-keeping rules. Follow the current scope in [ACTION_PLAN.md](ACTION_PLAN.md).

## 1. Open an iteration

Give the iteration one clear purpose and a completion check. A purpose might be copying inputs, documenting duplicate interpretations, reviewing one boundary case, interpreting a group of sections, or checking a model revision. Do not create a new iteration for every small edit while the same review is underway.

Choose the next unused number from [ITERATIONS.md](ITERATIONS.md). Name the directory `iter<number>_<MMDDYYYY>_<concise_action>`, using the local date when work begins. Keep that name if work spans several days; record the finishing date separately. Do not reuse a cancelled iteration's number.

Copy the [README template](templates/ITERATION_README.md) and adapt the [manifest example](templates/manifest.example.json). Create only the subdirectories needed for the work. Add an `In progress` entry to the index, identify the input iteration, and state what remains undecided. Retain a copy or hash of the workflow documents used for material decisions.

## 2. Freeze and identify inputs

The first raw-copy iteration copies the three authoritative processed CSVs into `outputs/` without changing their contents. Record original paths, SHA-256 hashes, sizes, headers, and row counts. Compare source and copy hashes. The existing exploratory audit can be referenced as evidence; it is not a substitute for freezing the actual inputs.

Later iterations reference completed, frozen outputs rather than duplicating the entire history. List the exact files in the manifest and, when helpful, `inputs/input_files.csv`. Its columns are `file_id,path_base,path,role,sha256,size_bytes,row_count,parent_iteration`. Declare whether each path is relative to the repository root or iteration directory. Do not use an unspecified “latest” file as an input.

Copy new user submissions unchanged into `inputs/`, record their sources and hashes, and derive working additions in `outputs/`. If an input changes after work begins, record the replacement explicitly or restart the affected work against a new input version.

## 3. Perform the work and record the reasoning

Use complete output tables by default, so the next iteration has a definite working release. If an output is only an addition or a list of changes, label it as such and record the exact parent and reconstruction procedure. Retain the raw-copy snapshot throughout the project.

Use the following audit files when relevant; do not create empty paperwork just to fill folders:

| File | What to record |
|---|---|
| `audit/source_row_links.csv` | Each output interval's link to its original file hash and record ordinal; multiple links when copies share an interpretation |
| `audit/changes.csv` | A stable change ID, well/interval ID, field, old value, new value, reason, method, evidence, decision ID, and review status |
| `audit/decisions.csv` | A stable decision ID, question, options, outcome or pending status, person making the decision, date, and evidence |
| `audit/open_issues.csv` | Issue ID, affected wells/intervals/sections, factual description, required follow-up, and resolving iteration when available |
| `audit/checks.json` | Checks performed, expected result, actual result, pass/fail/unresolved status, and any explained differences |

Use `well_id` for well links. An original CSV record ordinal must always be paired with its input hash: sorting or rewriting a table changes its record positions. Preserve distinct occurrences of repeated identical intervals. See [DATA_FORMAT.md](DATA_FORMAT.md).

Keep proposed edits separate from accepted working values. A proposal awaiting a decision belongs in the audit or a clearly labeled candidate file. It must not silently become the next iteration's accepted input.

### During well preparation

Keep original layer names. Follow the user-approved duplicate-removal rule in the action plan: removed working records retain their original identities and metadata in archives and links under surviving representatives. Organize source-backed metadata, check units and heights, and review the four gap/overlap wells individually. Unknown values remain unknown unless a source or an explicitly documented calculation supports filling them.

Do not introduce geological reliability scores or modeling exclusions. Record factual deficiencies and carry unresolved boundary questions forward. Obtain the user's decision before applying consequential boundary replacements, name changes, or interpretation choices. Routine copying, factual checks, and documentation do not require a separate geological decision.

### During cross-section interpretation

Give each section a stable ID, such as `SEC_001`, reused when the same section is revised. Save its map trace, direction, well list, and plotting settings. For projected wells, record distance along the section and perpendicular offset from it. Show the observed well intervals separately from drawn connections and model predictions.

Store section-specific outputs together, for example:

```text
outputs/sections/SEC_001/
    trace.geojson
    wells.csv
    interpreted_contacts.csv
evidence/sections/SEC_001/
    observed_section.pdf
    interpreted_section.pdf
    review.md
```

`wells.csv` links `well_id`, duplicate interpretation group where applicable, section position, offset, and the input version. `interpreted_contacts.csv` records a contact ID, well/source links if observed, original label, coordinates and their references, observed/derived/interpreted/predicted status, decision ID, and review status. A contact drawn between wells is an interpretation, not a new well observation.

Record why a connection was changed, what alternative was considered, and which intersecting sections must be updated. This is the stage for geological suitability decisions, exclusions from a particular model, and uncertainty assessments. Retain the original observations even when a different interpretation is accepted.

### During 3D work or desktop-software editing

Save the native project or reproducible script, software version, settings, coordinate and height references, input mapping, and model extent. Put manual instructions in `scripts/manual_procedure.md`; include enough detail to repeat the import, edits, and export.

Export machine-readable reviewed contacts and geometry as well as images. Check an import/export round trip for well IDs, layer labels, depths, heights, and interval counts. Record any deliberate mapping in a crosswalk. A screenshot alone cannot recover an accepted boundary or prove that an import preserved values.

Use the same contact IDs across section and 3D outputs where possible. Save any new geological choices in `decisions.csv`; do not leave them only inside a proprietary project.

## 4. Verify against the iteration's purpose

Compare inputs and outputs. Explain every intentional change in counts, values, and links. At minimum, check:

- The working well table has a nonblank, unique `well_id`; interval and metadata well links resolve.
- Source hashes and record links are valid; well identities and original labels remain recoverable.
- Duplicate handling preserves every source occurrence and does not inflate independent evidence counts.
- Heights, depths, units, and height references are explicit. Any conversion has its source and calculation recorded.
- Unresolved gaps, overlaps, or missing information remain visible rather than silently filled.
- New interpretation outputs identify observations separately from drawings and model predictions.

Run checks suited to the actual change. A documentation iteration needs link and template checks, not a modeling test suite. A model iteration needs geometric checks and comparison with reviewed evidence, not merely a successful software run.

## 5. Review and close

Summarize what changed, what passed, and what remains open in the iteration README. Use `Awaiting review` if its intended outcome depends on an unresolved consequential decision. An iteration whose purpose is only to document an issue can finish with that issue explicitly handed forward.

Before marking the iteration `Complete`, record final output hashes, dates, decisions, checks, and links in the manifest and index. Completed inputs, outputs, evidence, and audit records are frozen. Correct a completed result in a new iteration; link the old result as superseded without removing it.

Maintain living root documents with dated revisions. Record changes to earlier administrative index entries openly. Data files are currently ignored by Git, so ensure frozen files themselves remain in the project's chosen storage; a hash without the file cannot reproduce the result.

## 6. Start the next iteration from an explicit handoff

Identify the accepted output version, open issues, and next purpose. A preparation issue discovered in a section leads to a new preparation correction iteration; a disputed geological connection leads to a new interpretation iteration. A purely numerical 3D problem may only require new modeling settings. Do not overwrite earlier stages to hide the feedback loop.

The broader milestone and review rules are in [ROADMAP.md](ROADMAP.md). Section counts and modeling acceptance thresholds must be agreed from the actual coverage and intended model use rather than treated as fixed requirements from this draft.
