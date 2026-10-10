# RockWorks evaluation notes

Dates are directories; filenames describe topics without repeating the date.

## 2026-10-06 initial evaluation

1. [Evaluation scope and workflow](2026-10-06/evaluation-scope-and-workflow.md)
2. [35 paired-well import package and instructions](../input/35_paired_spread/IMPORT_INSTRUCTIONS.txt)
   — Revised sample: 35 distinct reports and GWIS sites with both processed
   datasets, covering all 13 townships with paired data. This supersedes the
   initial 20-case sample and the provisional 19-township selection for this
   import trial. The site-940 overlap case remains a future separate test.
   Workbook validation passed; native RockWorks import remains untested.

## Working rule

The [proposed stratigraphic order and styles](../input/35_paired_spread/proposed_stratigraphy_order_and_styles.csv)
now include provisional sediment codes, supported by a
[source-depth audit](../input/35_paired_spread/sediment_order_audit_summary.json).
Missoula Flood facies have unique codes in one family range; their mutual order
is arbitrary. This is a review proposal, not a complete import table or a
validated solid-model configuration. Resolved parent basalt labels now have
unique provisional codes within their family ranges, as requested by the user.
These codes do not establish additional layers or resolve interpolation behavior.
WeatheredFlowTop now has provisional code 92 in the undifferentiated CRBG family
90; its numeric placement does not establish a regional horizon. All 31 labels
have unique numeric codes; original CSVs and the import XLS are unchanged.

Record RockWorks-specific decisions, tests, screenshots, import mappings, export behavior, limitations, and findings here. Later decisions should link to the documents they refine or supersede.
