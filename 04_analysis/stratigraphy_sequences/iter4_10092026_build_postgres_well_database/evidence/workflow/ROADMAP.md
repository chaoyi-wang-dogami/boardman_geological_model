# Roadmap to a reviewed Boardman 3D geological model

Workflow draft 1, October 8, 2026. The goal is a reproducible 3D model of the supported parts of the 19-township region, with reviewed geological connections and explicit limits. The data may support some layers and locations better than others. A complete project does not require pretending that every recorded subdivision is known everywhere.

This roadmap is a proposal. The first stage follows the user's decisions in [ACTION_PLAN.md](ACTION_PLAN.md). Later section routes, modeled layers, software, and numerical acceptance limits require decisions based on the prepared data and intended use.

## Milestones

| Stage | Main work | Deliverable | Ready to advance when |
|---|---|---|---|
| 0: baseline and workflow | Retain the existing exploratory audit; establish these documents and iteration templates | Existing findings plus the workflow package | Input locations, user scope, and recording rules are clear. [Iteration 0](iter0_10082026_raw_data_copy/README.md) has completed the unchanged starting snapshot. |
| 1: prepare current wells | Freeze copies; account for duplicate interpretations; organize metadata; verify heights; review individual gaps/overlaps; check basic consistency | Prepared CSV release, source links, metadata, and unresolved factual issues | Every change is traceable, IDs are consistent, and limitations are visible. No new geological suitability classifications are required. |
| 2: add user-supplied reference wells | Preserve submissions, agree on IDs, check fields and source information, and append reviewed working additions | Updated prepared release with source-backed reference records | Added records have explicit locations, depth/height conventions, and source links; duplicate evidence is identified. |
| 3: interpret cross sections | Begin near useful reference wells, expand through an intersecting network, and review conflicts | Versioned sections, reviewed contacts/connections, geological decisions, and uncertainty records | Important intersections agree, consequential conflicts are resolved or bounded, and coverage supports the chosen model extent and detail. |
| 4: construct an initial 3D model | Translate reviewed evidence and relationships into a reproducible model | Native/scripted model, exported geometry, settings, and comparison sections | The model computes, reproduces accepted constraints within agreed limits, and exposes unresolved areas for review. |
| 5: review, revise, and release | Check shapes, evidence agreement, and predictions; revisit earlier stages when necessary | Reviewed model release, validation record, uncertainty/coverage maps, and known limitations | The release checks below pass and the user accepts the model's intended use and limits. |

Stage 2 can begin whenever the user supplies reference wells. Preliminary sections can show prepared observations while local issues remain open. An initial 3D trial can also help test section interpretations before they are finalized. Keep each stage's accepted release distinct, and record any return to earlier work as a new iteration.

## A practical cross-section campaign

The amounts below are starting workload proposals, not proven sufficiency thresholds or routes already selected. Choose routes after mapping wells, their depth coverage, source heights, shared interpretations, and user-supplied references. Geological confidence assessment begins here.

### Pass 1: establish local connections

Start with roughly 3–4 short sections near the most useful reference wells, with around 6–10 well records per section where coverage permits. Include nearby wells that reach the same layers, a range of spacing/depths, and at least one intersecting route. A section need not contain exactly this many wells, and repeated interpretation copies do not provide independent confirmation.

Compare recorded sequences and heights before drawing connections. Investigate disagreements instead of shifting boundaries simply to make lines smooth. Record reference quality and alternative explanations. Keep a common vertical scale or explicitly record any exaggeration, which can make gentle slopes look steep.

### Pass 2: expand across the region

Extend the network outward from reviewed sections through intermediate wells. Use some sections across the main changes in layer height and others along them. The direction must follow mapped evidence, rather than assuming that north–south and east–west are always geologically best. A few routes crossing the existing network help test whether different views give compatible connections.

A provisional budget is about 10–15 principal sections in total across the study area, plus short local sections where needed. Do not draw one isolated section per township merely to satisfy the administrative boundary count. Sparse areas may need longer routes, less detailed modeling, additional evidence, or an explicitly unsupported area.

For projected sections, choose and document the allowed distance of wells from the route. Wide projection can create false disagreements when layer height varies sideways. For routes that bend through wells, record the bends; a change in line direction can change the apparent layer slope.

### Pass 3: challenge and reconcile

Add short sections across disagreements, abrupt thickness changes, suspected missing layers, and poorly tested intersections. Revisit shared wells and intersection points so one accepted interpretation is used consistently in all views.

Where there is enough independent coverage, set aside some wells or spatial groups before fitting the trial model, then compare predictions with them. This tests whether the interpretation predicts beyond its inputs. Do not count copies of a fitted interpretation as withheld evidence. Publish the withheld list and explain where sparse coverage prevents a useful independent test.

Three passes describe the work sequence; they are not a stopping rule. More passes are needed if consequential conflicts remain. Advance when:

- Each modeled area has relevant well or other source evidence, or is explicitly identified as an estimate with limited support.
- Major boundaries have compatible interpretations at shared wells and section intersections.
- Important disagreements have reviewed decisions, alternatives, or bounded unresolved areas.
- Missing observations are distinguished from an interpreted absence of a layer.
- Section geometry, well offsets, source links, and accepted contacts can be reproduced.
- The reviewer agrees that remaining uncertainty is acceptable for the selected model use and level of detail.

## Choose software through a small pilot

Use the same small prepared well package and two intersecting sections for any software comparison. Test preserving well IDs, original labels, source intervals, height references, proposed edits, and exported reviewed contacts before expanding.

GemPy provides a scripted modeling API using boundary points, orientations, and structural relationships. It is a candidate 3D engine; the workflow would also need a deliberate way to review and record manual section interpretations. [GemPy modeling documentation](https://docs.gempy.org/tutorials/b_fundamentals/a01_basics.html).

RockWorks provides well-log sections and projected stratigraphy sections, making it a candidate for the well-comparison stage. [RockWorks log-section tutorial](https://help.rockware.com/rockworks/WebHelp/tut_strat_logsec.htm), [projected-section documentation](https://help.rockware.com/rockworks/WebHelp/strat_projsec_linear.htm).

Leapfrog Energy supports geological model volumes/surfaces and mesh exports; evaluate its editing and export workflow on the same pilot rather than assuming its native project transfers directly into GemPy. [Leapfrog Energy geological models](https://help.seequent.com/Energy/2023.2/en-GB/Content/geo-models/geo-models.htm), [mesh export documentation](https://help.seequent.com/Energy/2026.1/en-GB/Content/meshes/meshes.htm).

These documented capabilities do not establish suitability for this dataset. The pilot should decide whether one tool suffices or manual interpretation and scripted modeling should be combined. Record installed versions and verify a round trip. New workflow documentation and iteration records stay here; reference existing commercial-evaluation evidence elsewhere without rewriting it.

## 3D review and reasons to revisit sections

For a stack of adjoining layers, use a shared boundary between neighboring layers rather than estimating each touching face independently. Make the intended order and relationships explicit. A single volume classification should assign each modeled location consistently; check exported geometry too. These are proposed construction rules to test, not proof that the resulting geology is correct.

| Review finding | Why it matters | Follow-up |
|---|---|---|
| Layers cross, reverse order, or have negative thickness without evidence | Accepted layer relationships are violated | Check contact assignments and model relationships; revisit sections if the interpretation itself conflicts. |
| Two rock volumes occupy the same space, or unexplained empty space appears inside the modeled rock domain | Adjacent boundaries or volume construction disagree | Check shared boundaries and export geometry; review section contacts when the disagreement comes from them. |
| A layer suddenly becomes extremely thick/thin, forms a spike, or creates an isolated blob | Sparse evidence or modeling settings may create unsupported shapes | Compare nearby wells and crossing sections; test settings before proposing geological edits. |
| A modeled boundary misses an accepted well contact or section connection beyond the agreed tolerance | The model does not reproduce its reviewed constraints | First check units, references, import mapping, and projection; revisit the connection if those are correct. |
| Abrupt breaks or cutoffs lack supporting evidence | A software artifact may resemble a real geological break | Check settings and input coverage; require evidence for a geological explanation. |
| Rock extends above the intended ground boundary, or is modeled as certain far outside control | Model extent or clipping is wrong, or confidence is overstated | Check ground surface, domain, and coverage; reduce extent/detail or label unsupported estimates. |
| A thin layer disappears only when model resolution changes | The numerical representation may be too coarse | Compare resolutions and geometry before changing the geological interpretation. |
| Held-out wells consistently disagree in one area | Local connections, adopted heights, or assumed relationships may be wrong | Investigate the area using additional crossing sections and source records. |

Some layers really thin to zero, are removed by erosion, or are displaced by breaks in the rock. Such relationships need evidence and explicit modeling rules; do not remove them merely to enforce smoothness. Unknown/unmodeled regions are not geometric holes to fill with invented layers.

Before release, retain maps and tables comparing modeled and accepted boundaries, checks for overlap/unexplained voids, thickness review, section intersections, and sensitivity to settings. Set height mismatch limits from source quality and model purpose during review; this draft does not impose an arbitrary universal tolerance.

The final package includes frozen input/contact tables, every accepted decision, software/scripts/settings, coordinate and height references, the model and portable exports, review evidence, coverage/uncertainty maps, and open limitations. Completing the model means delivering this reviewable package with agreed scope, rather than only producing a visually smooth 3D view.
