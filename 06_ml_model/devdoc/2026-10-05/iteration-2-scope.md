# Iteration 2 scope

**Date:** 2026-10-05  
**Status:** Agreed design; implementation has not started

## Objectives

Iteration 2 will:

1. Define a standardized stratigraphic hierarchy that retains all observed Boardman units and uses `.general` for a known parent with unresolved detail.
2. Construct auditable top and bottom candidates from every interpreted interval, including first occurrences and midpoint-adjusted overlaps.
3. Build a GemPy model containing detailed subdivisions within evidence-supported local domains, with parent `.general` units elsewhere.
4. Provide the cross sections, maps, lithology columns, source records, and hierarchy needed for geologist correction.
5. Establish gradient-boosted trees as the first lithology-to-stratigraphy model architecture.

## Data decisions

- Preserve all source intervals and boundaries.
- Treat every interval occurrence as a candidate top and bottom.
- Mark direct transitions, first occurrences, gaps, midpoint assumptions, regional priors, and human decisions separately.
- Split overlapping consecutive intervals at the midpoint of the overlap. Retain the original boundaries and update the derived boundary when nearby stratigraphy or geologist review supports a better value.
- Normalize a parent-only label to its `.general` child; for example, `EllensburgFm` becomes `EllensburgFm.general`.
- Use NAVD88 as the target modeling datum after verifying or deriving the well ground elevation. Preserve the original elevation and transformation provenance.

## Identifier decision

`gw_site_id` is the GWIS interpretation-group key. It is not one-to-one with repository `well_id` or numeric OWRD `wl_id`:

- The full 19-township summary has 1,357 GWIS sites: 1,144 link to one report and 213 link to multiple reports.
- The stratigraphy subset has 71 GWIS sites linked to multiple reports.
- Each current `well_id` and `wl_id` links to only one GWIS site.
- The site-level stratigraphy tables copied to linked reports are identical and count as one interpretation.

Iteration 2 will retain a many-to-one report-to-site table and audit report dates, work types, completion depths, construction information, and coordinates before assigning independent physical-borehole IDs.

## Geologist review package

For each uncertain site, provide:

- A depth-aligned lithology and stratigraphy column showing original, derived, and predicted intervals.
- Tops and bottoms with evidence class and uncertainty.
- Cross sections through nearby interpreted wells in selectable directions.
- A map of occurrences, meaningful absences, nearest neighbors, distances, and proposed local unit domain.
- Original well reports and GWIS provenance.
- The canonical hierarchy and regional stratigraphic order.
- Alternative model interpretations and their effects on the 3D model.

The reviewer can accept, move, add, delete, or relabel a top or bottom; choose `.general`; replace an overlap midpoint; and edit a unit's lateral support domain. Every action is versioned without overwriting source data.

## GemPy model

- Retain the broad CRBG framework as the regional parent model.
- Add all observed subdivision tops and bottoms to the candidate-contact inventory.
- Interpolate detailed subdivision surfaces inside evidence-supported local domains.
- Use the parent `.general` unit outside those domains.
- Use erosion, onlap, and fault relations only where supported by geological evidence.
- Generate alternate realizations for uncertain contacts, assignments, orientations, and lateral domains.
- Report contact-elevation percentiles, voxel unit probabilities, nearest-control distance, and prior-dominated areas.

A subdivision supported by too little local information remains visible as an observed constraint and may enter a clearly identified prior-dominated realization. It will not silently become a study-wide surface.

## First ML model

Use gradient-boosted decision trees with two fixed-length input tables:

1. Atomic lithology segments with text-derived, depth, thickness, QC, spatial, and fixed-window sequence features.
2. Candidate boundaries with features from the shallower and deeper intervals and nearby sequence context.

Predict:

- Hierarchical unit probabilities for each segment.
- `.general` when a parent is supported and a child is unresolved.
- Contact probability at each boundary.
- Shallower-unit bottom and deeper-unit top identities.
- Confidence and review-required status.

A constrained decoder assembles complete well sequences. Single decision trees, spatial-only models, and text-only models remain comparison baselines. Neural networks and Transformers remain later experiments after regional training-data expansion.

## Iteration 2 completion criteria

- Versioned ontology and alias mapping reviewed.
- Source and derived top-and-bottom contact tables produced.
- GWIS/report/physical-borehole relationship audit completed.
- NAVD88 transformation and QC fields documented.
- Cross-section review workflow demonstrated on known conflicts and uncertain labels.
- Detailed GemPy model and uncertainty ensemble generated without forcing subdivisions outside their support domains.
- Gradient-boosted baseline evaluated with grouped-site and spatial-block validation.
