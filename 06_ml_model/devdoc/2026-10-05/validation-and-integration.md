# Validation and 3D-model integration

**Date:** 2026-10-05  
**Status:** Initial validation design

## Data splits

All rows belonging to one `gw_site_id` must stay in the same fold. Resolved reports from the same physical borehole must also stay together. Reports without a confirmed site link require a conservative group key. Correlated reports or intervals cannot cross from training into validation.

Use three evaluations:

1. **Grouped site cross-validation:** performance on another site from the current footprint.
2. **Spatial-block cross-validation:** transfer to contiguous areas not represented in training.
3. **Locked test sites:** a small set that is never used for tuning or human-feedback training.

Add interpreter-held-out and time-held-out sensitivity checks if sample support permits them. Grouped cross-validation is designed to keep correlated groups entirely within one fold. [scikit-learn grouped validation](https://scikit-learn.org/stable/modules/cross_validation.html#cross-validation-iterators-for-grouped-data).

## Metrics

| Level | Metrics |
|---|---|
| Segment | Macro F1, balanced accuracy, per-class precision and recall |
| Depth weighted | Correctly classified depth and thickness-weighted macro F1 |
| Contact | Missed and extra contacts; median and 90th-percentile depth error |
| Whole well | Exact broad-sequence match, edit distance, valid-order rate |
| Probability | Log loss, Brier score, reliability diagram, calibration error |
| Abstention | Accuracy versus retained coverage |
| 3D consequence | Withheld-contact residuals, surface change, crossing violations |

Overall accuracy alone is insufficient because common units could conceal complete failure on rare units.

## Probability and abstention

Every prediction should include:

- Calibrated class probabilities.
- Margin between the best alternatives.
- Model or fold disagreement.
- Distance from training examples in text/depth space.
- Geographic distance from paired or accepted sites.
- Location and interval QC flags.
- Rare or unsupported label flags.
- Sequence-constraint cost.

Possible statuses:

- `review_required`
- `high_confidence_candidate`
- `out_of_distribution`
- `insufficient_log_coverage`
- `ontology_gap`
- `accepted_by_human`

Confidence thresholds will be selected from held-out calibration and error-versus-coverage curves. Calibration itself must not use the evaluation labels. [scikit-learn calibration guide](https://scikit-learn.org/stable/modules/calibration.html).

## Promotion gates

A model can become the active interpreter only if it:

- Beats independent-interval and spatial-only baselines on spatially held-out sites.
- Improves macro metrics without collapsing rare classes.
- Provides usable calibrated probabilities.
- Passes sequence and provenance checks.
- Has reviewed successes, high-confidence errors, rare-unit cases, and geographic-edge cases.
- Does not degrade the locked test set after feedback updates.

Numeric thresholds will be selected after baseline experiments.

## Derived output tables

Predictions belong in new files:

- `predicted_intervals.csv`: intervals, hierarchy, probabilities, status, model version, and source snapshot.
- `predicted_contacts.csv`: top and bottom depths/elevations, boundary roles, uncertainty, acceptance, and provenance.
- `candidate_sequences.parquet`: top-K alternatives used for review.
- `feedback_events.parquet`: immutable human feedback.
- `data_manifest.json`: schemas and input hashes.
- `model_card.md`: training data, splits, metrics, limitations, and intended use.

Source GWIS intervals must remain unchanged.

## GemPy integration

GemPy should consume only contacts with an explicitly permitted status. Source contacts and ML-derived contacts need separate provenance and visualization.

Compare three model variants:

1. Source GWIS contacts only.
2. Source plus human-accepted ML contacts.
3. Source plus high-confidence unreviewed candidates, for research sensitivity only.

Evaluate withheld-contact residuals, surface stability, ordering, and regions where predictions strongly change geometry. A larger number of contacts does not automatically mean a better geological model.

### Vertical reference

Use NAVD88 as the target vertical datum after verifying or deriving each well's ground elevation in that datum:

\[
z_{contact,NAVD88}=z_{ground,NAVD88}-d_{contact}.
\]

Preserve GWIS source elevations, source depth, derived NAVD88 elevation, elevation source, transformation method, and QC difference in separate fields. Do not relabel an elevation as NAVD88 without a verified source datum or a documented transformation.

### Local subdivision domains

The iteration 2 GemPy model will include all subdivision tops and bottoms as candidate constraints. Interpolate detailed surfaces only inside evidence-supported domains. Use the parent `.general` unit outside those domains. Cross-section review, neighboring occurrences, meaningful absences in sufficiently deep wells, and regional references define and revise those domains.

## Reproducibility

- Version input hashes, preprocessing, ontology, splits, model, calibration, decoder rules, and feedback schema.
- Store train, validation, and test site IDs explicitly.
- Preserve original values beside derived values.
- Never silently repair depth, coordinates, or stratigraphic order.
- Record seeds and software versions.
- Keep locked test sites out of active learning.
- Version every ontology or geological-rule change.
- Support rollback to previous accepted models.
