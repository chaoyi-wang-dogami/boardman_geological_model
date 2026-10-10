# Human feedback and RLHF

**Date:** 2026-10-05  
**Status:** Staged design

## Why RLHF begins later

Classic RLHF trains an initial policy, learns a reward model from preferences, and optimizes the policy against that reward. The current Boardman data contain only 112 paired GWIS interpretation sites, and the independent physical-borehole count still requires resolution. Starting with policy-gradient reinforcement learning would add instability before we have a reliable supervised interpreter or enough independent preferences.

The project will still include RLHF, in four stages:

1. Supervised corrections.
2. Active learning.
3. Preference learning and candidate reranking.
4. Conservative policy optimization.

Only Stage 4 is strict reinforcement learning. Direct preference optimization can be compared with an explicit reward model plus PPO when enough preference data exist. [DPO paper](https://arxiv.org/abs/2305.18290); [PPO paper](https://arxiv.org/abs/1707.06347).

## Reviewer interface

The primary reviewer workspace should combine five linked views:

1. **Well column:** original lithology descriptions and depths beside source, derived, and predicted stratigraphy; show tops and bottoms separately.
2. **Cross section:** the selected well and nearby wells, contact confidence, proposed surfaces, uncertainty bands, and vertical exaggeration. Allow several section directions.
3. **Map:** well location, coordinate quality, nearest interpreted wells, unit occurrences, and the current lateral support domain.
4. **Source evidence:** original report or PDF, interpreter, sample source, source interval, and any linked reports.
5. **Stratigraphic key:** canonical hierarchy, `.general` labels, regional order, aliases, and the evidence behind each candidate.

Cross sections are the main tool for correcting uncertain formation tops and bottoms. Lithology is needed beside them so the geologist can decide whether a boundary is supported by a sediment-basalt transition, weathered flow top, interbed, texture change, or only a regional trend. The map supplies the nearest-neighbor and lateral-continuity context that one cross section cannot show.

The interface should also show alternative complete interpretations, model probabilities, model version, and why the well was selected for review.

Existing stratigraphy should be revealed only when the review task permits it. The interface must visually distinguish source observations, model predictions, and human edits.

## Reviewer actions

- Accept the full interpretation.
- Accept or reject one interval.
- Change a broad or detailed unit.
- Change a unit to or from its parent `.general` label.
- Move, add, or delete a top or bottom contact.
- Accept or replace an overlap-midpoint boundary.
- Mark unknown, unsupported detail, out of vocabulary, or insufficient evidence.
- Prefer candidate A or B, or mark them indistinguishable.
- Add a structured reason and optional note.
- Request independent second review.

Every action creates an immutable event. It does not overwrite the source or original model output.

## Feedback record

Each event should record:

```text
feedback_id
well_id and gw_site_id
source_data_snapshot_id
model_version and candidate-generation configuration
candidate IDs
action type
original predictions and probabilities
corrected intervals or preferred candidate
reviewer pseudonymous ID and role
review timestamp and duration
reason codes and note
adjudication status
superseded_feedback_id
```

Reviewer identity supports audit and disagreement analysis. It is not a prediction feature. Conflicting reviews remain stored; adjudication determines which label enters training.

## Active-learning queue

Review selection should balance:

- Prediction uncertainty.
- Model or candidate disagreement.
- Novel lithology wording or interval structure.
- Geographic distance from labeled sites.
- Rare units and deep contacts.
- Diversity across the batch.
- Expected impact on the 3D model.
- Random control wells for measuring selection bias.

Uncertainty alone can overselect anomalies. Review batches should combine uncertainty, representativeness, and diversity. [Active-learning survey](https://arxiv.org/abs/2210.10109).

## Preference model

The supervised sequence model is the initial policy and produces `K` candidate sequences. Reviewers compare complete interpretations. “Both wrong” and “indistinguishable” are valid responses.

A pairwise ranker can use a Bradley–Terry-style objective:

\[
P(A \succ B)=\sigma(r_\phi(x,A)-r_\phi(x,B)).
\]

The ranker should expose separate components:

- Learned human preference.
- Agreement with corrected labels.
- Contact plausibility.
- Sequence-order penalties.
- Appropriate abstention.
- Out-of-distribution penalty.

Hard data-validity rules remain outside the learned reward.

## Policy updates

Update order:

1. Retrain on adjudicated corrections.
2. Use the preference model only to rerank unchanged candidates.
3. Test direct preference optimization.
4. Test conservative, KL-constrained RL only if earlier stages succeed.

Online self-modification after individual reviews is prohibited. Updates occur in versioned batches with a locked test set and rollback.

## Gate before true RL

Do not start policy-gradient RL until:

- Preferences cover the major units, geography, depths, and failure modes.
- A doubly reviewed subset measures human agreement.
- A preference test set is held out.
- The ranker predicts held-out preferences materially above chance.
- Reranking improves geological metrics or review efficiency.
- Updated policies continue to pass supervised and spatial validation gates.

Exact minimum feedback counts will be chosen from learning curves rather than assumed now.
