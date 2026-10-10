# Data alignment, contacts, and target ontology

**Date:** 2026-10-05  
**Status:** Provisional; requires Phase 0 analysis and geological review

## Aligning lithology with stratigraphy

One lithology row cannot be assumed to correspond to one stratigraphy row. For each paired report, form atomic depth segments from the sorted union of lithology and stratigraphy boundaries:

\[
B=\operatorname{sort}\left(\{d^{L}_{from},d^{L}_{to},d^{S}_{start},d^{S}_{end}\}\right).
\]

Each consecutive interval \([B_i,B_{i+1})\) becomes an atomic segment. Record:

- Covering lithology interval and original description.
- Covering stratigraphy interval and original label.
- Overlap length and overlap fraction.
- Original row identifiers and source values.
- Gaps, overlaps, conflicting labels, and incomplete coverage.

A training target should initially require one unambiguous lithology description and one unambiguous stratigraphic label over the segment. Gaps and conflicts remain in an audit table. No missing interval is filled silently, and no contact is moved to a lithology boundary without an explicit rule and flag.

## Overlapping stratigraphy intervals

Preserve every original interval boundary. When two consecutive interpreted units overlap, create a separate derived boundary at the midpoint of the overlap:

\[
d_{boundary}=\frac{d_{shallower\ bottom}+d_{deeper\ top}}{2}.
\]

Use that depth as both the derived bottom of the shallower unit and the derived top of the deeper unit. Record `boundary_method=overlap_midpoint_assumption` and retain the original depths beside it. Nearby stratigraphy and geologist review can later confirm or replace the assumed boundary.

The two current Boardman cases are:

| GWIS site | Shallower unit | Deeper unit | Derived shared boundary |
|---|---|---|---:|
| 940 | `EllensburgFm.Selah`, original bottom 273 ft | `Crbg.Wb.PriestRapids.Lolo`, original top 260 ft | 266.5 ft |
| 940 | `Crbg.Wb.FrenchmanSprings.SentinelGap`, original bottom 519 ft | `Crbg.Wb.FrenchmanSprings.SandHollow`, original top 461 ft | 490.0 ft |

## Provisional label hierarchy

The standardized dot-separated stratigraphic names support hierarchical targets. The hierarchy must be generated from the data and reviewed before it becomes a fixed contract.

### Level 1: broad unit

- Surficial and other sediment
- Alkali Canyon Formation
- Ellensburg Formation
- Saddle Mountains Basalt
- Wanapum Basalt
- Grande Ronde Basalt
- Undifferentiated Columbia River Basalt Group
- Unknown or other

### Level 2: member or named subdivision

Examples include Pomona, Elephant Mountain, Umatilla, Frenchman Springs, Priest Rapids, Mabton, Selah, and Vantage.

### Level 3: flow or finer subdivision

Examples include Sentinel Gap, Sand Hollow, Ginkgo, Lolo, and Sentinel Bluffs subdivisions.

### General child convention

When the source confirms a parent unit but gives no supported child subdivision, normalize it to an explicit `.general` child. Examples:

- `EllensburgFm` becomes `EllensburgFm.general`.
- `Crbg.Wb` becomes `Crbg.Wb.general`.
- `Crbg.Wb.FrenchmanSprings` becomes `Crbg.Wb.FrenchmanSprings.general`.
- `Crbg.Grb` becomes `Crbg.Grb.general`.

`.general` means that the named parent is supported and its finer subdivision is unresolved. It is different from `unknown`, which does not establish the parent unit.

## Tops and bottoms

Every standardized interval produces two boundary candidates:

- The unit top at its derived or observed start depth.
- The unit bottom at its derived or observed end depth.

A shared boundary can therefore be both the bottom of the shallower unit and the top of the deeper unit. The contact table must retain both roles, the original interval IDs, boundary method, confidence, and human-review status.

## Required non-geological states

- `unknown`: the evidence does not identify a unit.
- `unsupported_detail`: a broad unit is possible but finer detail is not supported.
- `out_of_vocabulary`: the likely unit is absent from the current ontology.
- `abstain`: model confidence or data quality is inadequate.

These states must not be treated as ordinary formations.

## Identity and deduplication rules

- Use `gw_site_id` as the GWIS interpretation group where available; do not assume that it is a unique physical borehole.
- Keep all rows from one site in the same training or evaluation split.
- Preserve report IDs because several reports may describe one site differently.
- Do not treat duplicated intervals under linked reports as independent geological evidence.
- Do not automatically reconcile competing interpretations; retain both with provenance until an adjudication rule exists.

The current 19-township summary contains 1,357 nonblank GWIS site IDs. Of these, 1,144 link to one repository `well_id` and numeric OWRD `wl_id`, while 213 link to multiple distinct `well_id` and `wl_id` values. In the stratigraphy subset, 71 GWIS sites link to multiple reports. The reverse relation is one-to-one in the current data: no `well_id` or `wl_id` links to more than one GWIS site.

The duplicated stratigraphy tables for the 71 multi-report sites are identical across their linked reports. Count the table once as one GWIS interpretation unless report-specific stratigraphy is later recovered. Keep the site-to-report relation so report dates, work type, depth, construction details, and locations can be used to determine whether linked reports describe one borehole or several.

## Phase 0 questions

1. Which linked reports represent independent physical boreholes, alterations, deepenings, or other work on an existing borehole?
2. Which depths have unambiguous overlapping lithology and stratigraphy?
3. Which labels have enough sites for broad, member, or flow prediction?
4. Where are interval gaps, overlaps, and conflicting labels concentrated?
5. How do label distributions vary with location, depth, date, interpreter, and location class?
6. Which sites should be locked for final testing?
