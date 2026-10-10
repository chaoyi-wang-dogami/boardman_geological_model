# RockWorks 2026 evaluation scope and workflow

**Date:** 2026-10-06  
**Status:** Initial evaluation plan; test dataset has not yet been prepared

## Purpose

Evaluate whether RockWorks 2026 can provide the geological interpretation and cross-section capabilities needed for the Boardman project, and determine how much custom software remains necessary for the ML human-feedback workflow.

## Authoritative Boardman inputs

- `03_processed/boardman_19_townships/boardman_wells_summary.csv`
- `03_processed/boardman_19_townships/boardman_wells_lithology.csv`
- `03_processed/boardman_19_townships/boardman_wells_stratigraphy.csv`
- The standardized hierarchy and contact rules developed under `06_ml_model/devdoc/`

RockWorks-ready files belong in `input/`. Preparation code belongs in `scripts/`. Do not edit the authoritative processed files to satisfy a RockWorks import format.

## Initial evaluation dataset

Prepare a small, reproducible dataset of approximately 20 wells or resolved boreholes containing:

- Wells with both lithology and stratigraphy.
- Wells with lithology and no stratigraphy.
- Deep wells containing detailed CRBG subdivisions.
- Parent-level labels that will normalize to `.general`.
- GWIS sites linked to multiple well reports.
- GWIS site 940, which contains the two known overlapping interval pairs.
- Wells spanning several parts of the 19-township area.
- A range of coordinate-quality classes and log completeness.

The input manifest must state why every test well was selected.

## Identifier decision required before import

RockWorks expects a borehole identifier. Before creating the import package, decide whether each RockWorks borehole represents:

- A repository `well_id` report.
- An OWRD numeric `wl_id` report.
- A GWIS interpretation group.
- A resolved physical borehole.

Keep `well_id`, `wl_id`, and `gw_site_id` as separate imported fields regardless of the display identifier. Do not count identical site-level stratigraphy copied across linked reports as independent interpretations.

## Evaluation sequence

1. Create a disposable RockWorks project with explicit horizontal CRS, horizontal units, vertical units, and depth direction.
2. Import borehole locations and identifiers.
3. Define the ordered Stratigraphy Types table.
4. Import lithology and stratigraphy as separate interval datasets.
5. Configure a strip-log design that shows both datasets.
6. Create a selected-well, hole-to-hole linear correlation section.
7. Create a multi-panel projected section and test the projection swath.
8. Build selected stratigraphic surfaces or a stratigraphic solid model.
9. Edit tops and bottoms and test `.general` labels.
10. Export the edited records.
11. Compare the export with the source and derived inputs.
12. Record lost fields, changed identifiers, altered depths, rounding, reordered units, and other round-trip differences.

## Capabilities to test

### Data import and identity

- Preserve all identifiers.
- Preserve original interval depths.
- Import both tops and bottoms.
- Maintain lithology and stratigraphy as distinct observations.
- Represent missing stratigraphy without manufacturing intervals.
- Preserve parent-only `.general` labels.

### Geological review

- Select and order wells interactively.
- Display lithology beside stratigraphy.
- Create hole-to-hole and projected sections.
- Display ground elevation, total depth, and incomplete penetration.
- Edit interval labels, tops, and bottoms.
- Show units that disappear between wells.
- Compare source intervals with modeled surfaces.

### Modeling

- Model subdivisions without forcing unsupported units throughout the study area.
- Represent tops and bottoms of interbeds and basalt subdivisions.
- Control stratigraphic order.
- Inspect extrapolation beyond supporting wells.
- Export surfaces or model products in a format usable by the Boardman workflow.

### Audit and ML feedback

- Export reviewed intervals with source identifiers intact.
- Determine whether RockWorks records reviewer identity, time, reason, and previous value.
- Determine whether source, derived, predicted, and reviewed contacts can coexist without ambiguity.
- Determine whether edits can be converted into immutable feedback events.
- Determine whether repeated evaluation runs are reproducible.

## Success criteria

RockWorks is a strong candidate for the geological-review component if it can:

1. Import the Boardman test package without identifier or depth loss.
2. Display useful lithology and stratigraphy correlation sections.
3. Let a reviewer edit tops, bottoms, and labels efficiently.
4. Export reviewed intervals with enough identity and provenance for an auditable round trip.
5. Represent or clearly expose the limits of subdivision continuity.
6. Reduce the custom application scope materially.

If geological editing works but event-level feedback is insufficient, use RockWorks for interpretation and build a smaller companion feedback layer. If import, identity, hierarchy, or export behavior is inadequate, retain the custom review-application plan.

## Required records for every test

- RockWorks version and license level.
- Project settings and coordinate reference.
- Input file hashes.
- Exact import menu and field mappings.
- Relevant screenshots.
- Export settings and output hashes.
- Observed behavior.
- Pass, partial, or fail result.
- Workaround and its cost.
- Effect on the build-versus-buy decision.

## Safety and reproducibility

- Use a disposable RockWorks project for import experiments.
- Back up the project before replacement imports.
- Treat RockWorks project files and exports as derived artifacts.
- Never overwrite Boardman source or processed datasets.
- Prefer preparation scripts over manual spreadsheet edits.
