# Development roadmap

**Date:** 2026-10-05  
**Status:** Proposed sequence of work

## Planned repository structure

```text
06_ml_model/
├── devdoc/
├── README.md
├── config/
│   ├── ontology.yml
│   ├── features.yml
│   └── experiment.yml
├── data/
│   ├── manifests/
│   ├── interim/
│   └── feedback/
├── src/
│   ├── audit_inputs.py
│   ├── align_intervals.py
│   ├── build_features.py
│   ├── split_sites.py
│   ├── train_baselines.py
│   ├── train_sequence_model.py
│   ├── decode_sequences.py
│   ├── calibrate.py
│   ├── select_for_review.py
│   └── export_contacts.py
├── tests/
├── models/
├── runs/
└── review_app/
```

Generated training data and model binaries should normally remain outside Git. Track code, small fixtures, manifests, schemas, configuration, and evaluation summaries.

## Phase 0 — data and ontology audit

- Verify report-to-site linkage and duplicate paired reports.
- Build atomic interval alignment with a row-level audit.
- Quantify coverage, conflicts, class support, and geography.
- Review label hierarchy and allowed transitions.
- Normalize unresolved parent labels to `.general` children.
- Derive and audit both unit tops and bottoms.
- Apply the documented midpoint assumption to overlapping intervals while preserving source depths.
- Verify or derive NAVD88 ground elevations and retain source and transformed values.
- Freeze grouped, spatial, and locked test splits.

**Deliverable:** audited aligned dataset and decision report. No model claim.

## Phase 1 — baselines

- Implement majority, spatial-only, text-only, single-tree, and gradient-boosted segment and boundary models.
- Add grouped and spatial validation.
- Add calibration and class-level metrics.
- Determine which feature groups add held-out value.

**Deliverable:** gradient-boosted baseline model card and error analysis.

## Phase 2 — sequence interpreter

- Add hierarchical outputs and contact prediction.
- Add constrained sequence decoding.
- Generate top-K interpretations and uncertainty.
- Compare linear decoding, CRF, GRU, and a small Transformer only when justified.

**Deliverable:** candidate generator that beats the baselines.

## Phase 3 — human review and active learning

- Build the review interface and feedback event schema.
- Run a small double-review pilot.
- Measure review time, agreement, and correction patterns.
- Test active-learning batches against random review batches.
- Retrain from adjudicated corrections.

**Deliverable:** audited supervised human-feedback loop.

## Phase 4 — preference learning and RLHF

- Collect whole-sequence preferences.
- Train and validate a preference ranker.
- Test candidate reranking first.
- Compare correction-based retraining, direct preference optimization, and conservative RL.

**Deliverable:** evidence showing whether preference optimization improves geological accuracy or review efficiency.

## Phase 5 — controlled 3D integration

- Export accepted contacts with uncertainty and provenance.
- Rebuild GemPy variants.
- Test withheld-contact residuals and surface stability.
- Define which prediction statuses may enter geological models.

**Deliverable:** auditable source-plus-reviewed-prediction 3D model.

## Immediate next task

Implement Phase 0 only. The first code should produce:

- A paired-site inventory.
- Atomic aligned intervals.
- Coverage and conflict flags.
- Label-support tables by hierarchy.
- Maps and depth summaries.
- A proposed ontology file.
- A standardized top-and-bottom contact table.
- A GWIS-site-to-report cardinality and physical-well review table.
- Reproducible grouped and spatial split manifests.

Review those artifacts before implementing a predictive model or RLHF component.
