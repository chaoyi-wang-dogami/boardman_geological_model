# Lithology-to-stratigraphy ML development notes

This directory contains design notes for the Boardman lithology-to-stratigraphy ML pipeline. Dates are directories; filenames describe topics without repeating the date.

## 2026-10-05 initial design

Read in this order:

1. [Project scope and current data](2026-10-05/project-scope-and-data.md)
2. [Data alignment, contacts, and target ontology](2026-10-05/data-alignment-and-ontology.md)
3. [Iteration 2 scope](2026-10-05/iteration-2-scope.md)
4. [Model architecture](2026-10-05/model-architecture.md)
5. [Human feedback and RLHF](2026-10-05/human-feedback-and-rlhf.md)
6. [Validation and 3D-model integration](2026-10-05/validation-and-integration.md)
7. [Development roadmap](2026-10-05/development-roadmap.md)

## Working rule

Add documents under the directory for the decision or experiment date. Update an existing document only to correct an error or clarify what was decided on that date. Later decisions should link back to the document they supersede.

Source data remain outside this directory. Generated training data and model artifacts will be stored separately from these design notes.
