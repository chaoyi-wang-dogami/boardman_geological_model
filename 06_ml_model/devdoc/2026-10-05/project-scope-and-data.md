# Project scope and current data

**Date:** 2026-10-05  
**Status:** Initial design

## Goal

Train a model on wells containing both lithology and interpreted stratigraphy, then propose stratigraphy for wells that contain lithology only. Human-reviewed predictions may later supply additional contacts to the Boardman 3D geological model.

The ML system is an interpretation assistant. It must preserve source lithology and GWIS stratigraphy, distinguish predictions from observations, report uncertainty, and retain every human decision.

## Starting files

- [Lithology intervals](../../../03_processed/boardman_19_townships/boardman_wells_lithology.csv)
- [Interpreted stratigraphy](../../../03_processed/boardman_19_townships/boardman_wells_stratigraphy.csv)
- [Well summary and site links](../../../03_processed/boardman_19_townships/boardman_wells_summary.csv)
- [Existing GemPy methods](../../../04_analysis/boardman_19_townships/METHODS_AND_ASSUMPTIONS.md)

## Current inventory

| Quantity | Count |
|---|---:|
| Reports with lithology | 3,067 |
| Reports with stratigraphy | 423 |
| Reports containing both | 121 |
| Distinct GWIS sites represented by paired reports | 112 |
| Lithology rows in paired reports | 1,342 |
| Stratigraphy rows in paired reports | 534 |
| Exact lithology descriptions in paired reports | 665 |
| Exact stratigraphic labels in paired reports | 39 |
| Stratigraphy rows fully covered by lithology depths | 468 |
| Stratigraphy rows partially covered by lithology depths | 19 |
| Stratigraphy rows with no lithology-depth overlap | 47 |
| Lithology-only reports | 2,946 |
| Lithology-only reports with more than 10 lithology rows | 282 |

The paired data contain **112 distinct GWIS interpretation sites**. This is not yet a confirmed count of independent physical boreholes. Rows from one report are correlated, and several reports can refer to the same GWIS site. Training and evaluation must respect those dependencies.

## Main data limitations

- The 39 exact stratigraphic labels are imbalanced; six occur only once in paired reports.
- Grande Ronde examples are much less common than sediment and Saddle Mountains examples.
- Lithology and stratigraphy interval boundaries do not necessarily coincide.
- Forty-seven stratigraphy intervals in paired reports have no lithology-depth overlap.
- Raw lithology descriptions contain detailed free text, spelling variation, and driller-specific wording.
- Some reports share a GWIS site, so report count is not independent-site count.
- Coordinate quality varies, and the GWIS vertical datum still needs verification before combining elevations with an external DEM.

## Intended outputs

The model should produce reviewable interval sequences, possible contact depths, calibrated probabilities, alternative interpretations, and explicit abstention states. It must not write predictions into the source stratigraphy CSV.

The first model is a gradient-boosted tree system that predicts hierarchical interval labels and formation top and bottom contacts. Parent-level source labels use an explicit `.general` child. Member- and flow-level predictions remain available where the evidence supports them, with parent `.general` fallback and human review elsewhere.
